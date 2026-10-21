#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 xCaptaiN09
"""Package the audio-fix module without bundling proprietary libraries."""

import argparse
import hashlib
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "module"
FILES = (
    "action.sh",
    "config.sh",
    "customize.sh",
    "module.prop",
)
DIRECTORIES = (
    "system/",
    "system/vendor/",
    "system/vendor/lib/",
    "system/vendor/lib/hw/",
)


def build(destination: Path | None = None) -> Path:
    actual = {p.relative_to(MODULE).as_posix() for p in MODULE.rglob("*") if p.is_file()}
    if actual != set(FILES):
        raise ValueError(f"Unexpected module file set: {sorted(actual ^ set(FILES))}")
    for name in FILES:
        path = MODULE / name
        if path.is_symlink():
            raise ValueError(f"Module sources must be regular files: {name}")
        data = path.read_bytes()
        data.decode("utf-8")
        if b"\r" in data or not data.endswith(b"\n"):
            raise ValueError(f"Expected LF text with a final newline: {name}")

    prop = dict(
        line.split("=", 1)
        for line in (MODULE / "module.prop").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    if prop.get("id") != "mt6893-usb-audio-fix":
        raise ValueError("Unexpected module ID")
    version = prop.get("version", "")
    if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z._-]*", version):
        raise ValueError("Missing or invalid module version")
    archive = destination or ROOT / "dist" / f"mt6893-usb-audio-fix-v{version}.zip"
    archive = archive.expanduser().resolve()
    if archive.suffix.lower() != ".zip":
        raise ValueError("Output must have a .zip extension")
    if archive in {p.resolve() for p in MODULE.iterdir() if p.is_file()}:
        raise ValueError("Output cannot replace module source")
    archive.parent.mkdir(parents=True, exist_ok=True)

    # Use fixed metadata and a stable entry order.
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in DIRECTORIES:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o40755 << 16) | 0x10
            z.writestr(info, b"")
        for name in FILES:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o100755 if name.endswith(".sh") else 0o100644
            info.external_attr = mode << 16
            z.writestr(info, (MODULE / name).read_bytes())

    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
        if z.namelist() != list(DIRECTORIES) + list(FILES):
            raise ValueError("ZIP entry set/order differs from the source manifest")
        for name in z.namelist():
            if name.startswith("/") or ".." in name.split("/") or name.endswith(".so"):
                raise ValueError(f"Unexpected ZIP entry: {name}")
        for name in FILES:
            if z.read(name) != (MODULE / name).read_bytes():
                raise ValueError(f"Archive/source mismatch: {name}")

    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional destination .zip path")
    args = parser.parse_args()
    try:
        archive = build(args.output)
    except (OSError, UnicodeError, ValueError, zipfile.BadZipFile) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built: {archive}")
    print(f"Size: {archive.stat().st_size} bytes")
    print(f"SHA-256: {hashlib.sha256(archive.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
