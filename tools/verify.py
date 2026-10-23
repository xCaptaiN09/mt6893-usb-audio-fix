#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 xCaptaiN09
"""Audit the v1.0.0 source and installable release without device libraries."""
import ast
import hashlib
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = {'action.sh': '6c33431a52b915c0eb6349ce03fe6c6fea80a5b64dcbd62b99030d552eace75f', 'config.sh': '9435d291ed966bd05b83287d21053fefab0e06e298ae8c9635918253fb0d0521', 'customize.sh': '303691516c0d075ef81180329a9edf22bb5ff3ee056c945c4d7c08ea1f25fddc', 'module.prop': '10192eefd0cc424f0e02b54dc2f606716977f73fe0c7ed89662f98e91caf5701'}
VERSION = "1.0.0"
ARCHIVE = "mt6893-usb-audio-fix-v1.0.0.zip"
DIRECTORIES = ["system/", "system/vendor/", "system/vendor/lib/", "system/vendor/lib/hw/"]

def require(condition, message):
    if not condition:
        raise ValueError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    module = ROOT / "module"
    actual = {p.relative_to(module).as_posix() for p in module.rglob("*") if p.is_file() or p.is_symlink()}
    require(actual == set(FILES), "Unexpected module file set")
    for name, expected in FILES.items():
        path = module / name
        require(not path.is_symlink(), f"Module symlink: {name}")
        data = path.read_bytes()
        require(digest(data) == expected, f"Reviewed module source changed: {name}")
        require(b"\r" not in data and data.endswith(b"\n"), f"Expected LF text: {name}")
        data.decode("utf-8")
    prop = dict(line.split("=", 1) for line in (module / "module.prop").read_text().splitlines() if "=" in line)
    for key, value in {"id": "mt6893-usb-audio-fix", "name": "MT6893 USB Audio Fix", "version": VERSION, "versionCode": "100", "author": "xCaptaiN09"}.items():
        require(prop.get(key) == value, f"Unexpected module {key}")
    shell = shutil.which("sh")
    require(shell is not None, "A POSIX shell is required; use Linux or WSL")
    for name in FILES:
        if name.endswith(".sh"):
            subprocess.run([shell, "-n", str(module / name)], check=True)
    for path in (ROOT / "tools").glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    print("PASS v1.0.0 metadata, reviewed module source and source syntax")

    archive = ROOT / "releases" / ARCHIVE
    require({p.name for p in archive.parent.iterdir() if p.suffix == ".zip"} == {ARCHIVE}, "Release folder contains another ZIP")
    checksum = digest(archive.read_bytes())
    require((archive.parent / "SHA256SUMS").read_text() == f"{checksum}  {ARCHIVE}\n", "SHA256SUMS mismatch")
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None, "ZIP CRC failure")
        require(z.namelist() == DIRECTORIES + list(FILES), "ZIP members/order differ from the module manifest")
        for entry in z.infolist():
            name = entry.filename
            require(not name.startswith("/") and ".." not in PurePosixPath(name).parts and "\\" not in name, f"Unsafe path: {name}")
            require(not entry.flag_bits & 1 and not stat.S_ISLNK(entry.external_attr >> 16), f"Unsupported ZIP entry: {name}")
            require(entry.date_time == (1980, 1, 1, 0, 0, 0), f"Unstable timestamp: {name}")
            mode = 0o755 if name.endswith(("/", ".sh")) else 0o644
            require((entry.external_attr >> 16) & 0o777 == mode, f"ZIP permissions: {name}")
            if not name.endswith("/"):
                require(z.read(name) == (module / name).read_bytes(), f"ZIP/source mismatch: {name}")
    print("PASS ZIP/source equality, CRC, metadata, paths, permissions and SHA-256")

    old_marker = "0.1" + "-test"
    texts = [ROOT / "README.md", ROOT / "CHANGELOG.md", *(ROOT / "docs").glob("*.md"), *(ROOT / "tools").glob("*.py"), *(module / name for name in FILES)]
    for path in texts:
        text = path.read_text(encoding="utf-8")
        require(old_marker not in text, f"Old release label in {path.relative_to(ROOT)}")
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", text):
                if "://" in target or target.startswith(("#", "mailto:")):
                    continue
                target = target.split("?", 1)[0].split("#", 1)[0]
                require((path.parent / target).exists(), f"Broken local link: {path.name}: {target}")
    print("PASS final release naming and local Markdown links")
    print(f"Release: {ARCHIVE}\nSHA-256: {checksum}")
    print("AUDIT PASSED. This is a PC release audit, not a new phone playback test.")

if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, SyntaxError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print(f"AUDIT FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
