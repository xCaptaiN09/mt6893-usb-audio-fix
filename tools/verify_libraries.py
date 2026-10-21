# SPDX-License-Identifier: MIT
# Copyright (c) 2026 xCaptaiN09
from pathlib import Path
import argparse
from hashlib import sha256
import io
import shlex
import shutil
import struct
import subprocess
import tempfile

from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R3, UC_ARM_REG_R6

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description="Verify the exact ARM32 patch and installer using your own local library copies.")
parser.add_argument("--audio", required=True, type=Path, help="Original audio.primary.mt6893.so")
parser.add_argument("--performance", required=True, type=Path, help="Original vendor.oplus.hardware.performance-V1-ndk_platform.so")
args = parser.parse_args()
MOD = ROOT / 'module'
AUDIO = args.audio
PERF = args.performance
if not __debug__:
    raise SystemExit("Do not run this verifier with Python -O; assertions are required.")
if shutil.which('sh') is None:
    raise SystemExit("A POSIX sh is required for installer fixtures. Use Linux or WSL.")
ORIGINAL = 'f080b9f3f607590b00aeca4a4a043eba4d594291bde287b20629ef35591db7fa'
PATCHED = 'b334b7ed5a4819eb1a922e958531ea964e985d0482456c42ab969d03c7cbf33e'
PERF_HASH = '7ae966ef80ef45f7dcda16f011d6454a635690af774dc3bfe84e5ff5caa7fca7'
report = ['LOCAL VERIFICATION', 'Installer permissions and SELinux helpers are mocked; this is not a device audio test.', '']

def passed(message):
    report.append('PASS: ' + message)

def digest(b):
    return sha256(b).hexdigest()

original = AUDIO.read_bytes()
performance = PERF.read_bytes()
assert digest(original) == ORIGINAL and digest(performance) == PERF_HASH
passed('Both uploaded inputs match the exact hashes embedded in the installer.')

ae = ELFFile(io.BytesIO(original))
pe = ELFFile(io.BytesIO(performance))
assert ae.elfclass == pe.elfclass == 32
assert ae['e_machine'] == pe['e_machine'] == 'EM_ARM'

def read_va(elf, va, length):
    segment = next(s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD' and s['p_vaddr'] <= va < s['p_vaddr'] + s['p_filesz'])
    return segment['p_offset'] + va - segment['p_vaddr']

changes = [
    (0x2a3ca0, bytes.fromhex('cc3090e5'), bytes.fromhex('d03090e5'), 0xcc, 0xd0, UC_ARM_REG_R3, 'getHIUfsFeature', 'getKernelVersion'),
    (0x2a3d3c, bytes.fromhex('706290e5'), bytes.fromhex('746290e5'), 0x270, 0x274, UC_ARM_REG_R6, 'writeTidsSet', 'writeUxState'),
]
patched = bytearray(original)
cs = Cs(CS_ARCH_ARM, CS_MODE_ARM)
for va, before, after, old_slot, new_slot, reg, old_method, new_method in changes:
    off = read_va(ae, va, 4)
    assert original[off:off+4] == before
    patched[off:off+4] = after
    old_ins = list(cs.disasm(before, va))
    new_ins = list(cs.disasm(after, va))
    assert len(old_ins) == len(new_ins) == 1
    assert old_ins[0].mnemonic == new_ins[0].mnemonic == 'ldr'
    assert old_ins[0].op_str.endswith(f'#0x{old_slot:x}]')
    assert new_ins[0].op_str.endswith(f'#0x{new_slot:x}]')
    passed(f'ARM instruction at VA {va:#x}, file offset {off:#x}: {old_ins[0].op_str} -> {new_ins[0].op_str}.')
assert len(patched) == len(original) == 3107960
assert digest(patched) == PATCHED
assert [i for i, (a, b) in enumerate(zip(original, patched)) if a != b] == [2763936, 2764092]
passed('Exactly two bytes change; file size, ELF layout, and all other file bytes are unchanged.')

# Decode Android APS2 packed REL records to resolve the actual method table.
dyn = pe.get_section_by_name('.dynsym')
data = pe.get_section_by_name('.rel.dyn').data()
assert data[:4] == b'APS2'
position = 4

def sleb():
    global position
    value = shift = 0
    while True:
        byte = data[position]
        position += 1
        value |= (byte & 127) << shift
        shift += 7
        if not byte & 128:
            return value - (1 << shift) if byte & 64 else value

count, offset = sleb(), sleb()
done = 0
relocations = {}
while done < count:
    size, flags = sleb(), sleb()
    delta = sleb() if flags & 2 else None
    info = sleb() if flags & 1 else None
    assert not flags & 8
    for _ in range(size):
        offset += delta if flags & 2 else sleb()
        item = info if flags & 1 else sleb()
        symbol = dyn.get_symbol(item >> 8)
        relocations[offset] = (item & 255, symbol)
    done += size
assert done == count and position == len(data)
vtable = next(s for s in dyn.iter_symbols() if s.name.startswith('_ZTV') and s.name.endswith('13BpPerformanceE'))
address_point = vtable['st_value'] + 8
table = {}
for address, (kind, symbol) in relocations.items():
    slot = address - address_point
    if 0 <= slot < vtable['st_size'] - 8:
        assert kind == 2
        table[slot] = symbol

for va, before, after, old_slot, new_slot, reg, old_method, new_method in changes:
    assert old_method in table[old_slot].name and new_method in table[new_slot].name
    for instruction, slot, method in [(before, old_slot, old_method), (after, new_slot, new_method)]:
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(0x1000, 0x1000)
        uc.mem_map(0x600000, 0x1000)
        uc.mem_write(0x1000, instruction)
        for table_slot, symbol in table.items():
            uc.mem_write(0x600000 + table_slot, struct.pack('<I', symbol['st_value']))
        uc.reg_write(UC_ARM_REG_R0, 0x600000)
        uc.emu_start(0x1000, 0x1004, count=1)
        assert uc.reg_read(reg) == table[slot]['st_value']
    passed(f'Relocated vtable lookup and ARM emulation: {old_method} -> {new_method}, with the intended destination register preserved.')

# Confirm the observed stack pointer signature has no property-get calls.
plt = ae.get_section_by_name('.plt')
adyn = ae.get_section_by_name('.dynsym')
plt_names = {plt['sh_addr'] + 32 + 16*i: adyn.get_symbol(r.entry.r_info_sym).name for i, r in enumerate(ae.get_section_by_name('.rel.plt').iter_relocations())}
function = next(s for s in adyn.iter_symbols() if s.name == 'setAudioHalSchedToUx')
start = function['st_value']
off = read_va(ae, start, function['st_size'])
calls = []
for ins in cs.disasm(original[off:off+function['st_size']], start):
    if ins.mnemonic in ('bl', 'blx') and ins.op_str.startswith('#'):
        calls.append(plt_names.get(int(ins.op_str[1:], 0), ''))
assert not any('property_get' in x or 'system_property' in x for x in calls)
passed('The inspected function has no direct property-get calls offering a configuration bypass.')

for script in ['customize.sh', 'config.sh', 'action.sh']:
    subprocess.run(['sh', '-n', str(MOD / script)], check=True)
    assert b'\r' not in (MOD / script).read_bytes()
passed('All packaged shell scripts pass POSIX shell syntax checks and use LF line endings.')

# Run the real installer script with test-only input-path substitution and mocked
# root-manager permission helpers. This is not an Android/SELinux runtime test.
with tempfile.TemporaryDirectory(prefix='chu2-installer-test-') as temp:
    base = Path(temp)
    harness = base / 'harness.sh'
    harness.write_text('''ui_print() { printf '%s\\n' "$*"; }
abort() { printf '%s\\n' "$*" >&2; exit 42; }
set_perm_recursive() { :; }
set_perm() { chmod "$4" "$1"; }
ls() {
  if [ "$1" = -Zd ]; then
    printf '%s %s\\n' u:object_r:same_process_hal_file:s0 "$2"
  else
    command ls "$@"
  fi
}
BOOTMODE=$1
ARCH=$2
MODPATH=$3
. "$MODPATH/customize.sh"
''')
    cases = [
        ('exact inputs', original, performance, 'true', 'arm64', True),
        ('already patched reinstall', bytes(patched), performance, 'true', 'arm64', True),
        ('wrong audio hash', b'X' + original[1:], performance, 'true', 'arm64', False),
        ('wrong performance hash', original, b'X' + performance[1:], 'true', 'arm64', False),
        ('recovery install rejected', original, performance, 'false', 'arm64', False),
        ('unsupported CPU rejected', original, performance, 'true', 'x64', False),
    ]
    for number, (label, audio_input, perf_input, bootmode, arch, should_pass) in enumerate(cases):
        fixture = base / str(number)
        fixture.mkdir()
        a = fixture / 'live-audio.so'
        p = fixture / 'live-performance.so'
        a.write_bytes(audio_input)
        p.write_bytes(perf_input)
        m = fixture / 'module'
        shutil.copytree(MOD, m)
        config = (m / 'config.sh').read_text()
        config = config.replace('LIVE_AUDIO=/vendor/lib/hw/audio.primary.mt6893.so', 'LIVE_AUDIO=' + shlex.quote(str(a)))
        config = config.replace('LIVE_PERFORMANCE=/odm/lib/vendor.oplus.hardware.performance-V1-ndk_platform.so', 'LIVE_PERFORMANCE=' + shlex.quote(str(p)))
        (m / 'config.sh').write_text(config)
        result = subprocess.run(['sh', str(harness), bootmode, arch, str(m)], text=True, capture_output=True)
        assert (result.returncode == 0) == should_pass, (label, result.stdout, result.stderr)
        assert a.read_bytes() == audio_input and p.read_bytes() == perf_input
        output = m / 'system/vendor/lib/hw/audio.primary.mt6893.so'
        if should_pass:
            assert digest(output.read_bytes()) == PATCHED
            assert output.read_bytes() == patched
            assert (m / 'action.sh').stat().st_mode & 0o777 == 0o755
        else:
            assert not output.exists()
        passed(f'Installer fixture: {label}; original input files remain untouched.')
        if number == 0:
            action = subprocess.run(['sh', str(m / 'action.sh')], text=True, capture_output=True)
            assert 'NOT ACTIVE:' in action.stdout
            a.write_bytes(patched)
            action = subprocess.run(['sh', str(m / 'action.sh')], text=True, capture_output=True)
            assert 'ACTIVE:' in action.stdout and 'NOT ACTIVE:' not in action.stdout
            assert 'Performance: MATCH' in action.stdout
            passed('Status action correctly distinguishes original from patched live bytes in fixtures.')
            p.write_bytes(b'X' + performance[1:])
            action = subprocess.run(['sh', str(m / 'action.sh')], text=True, capture_output=True)
            assert 'BUILD MISMATCH:' in action.stdout and 'ACTIVE:' not in action.stdout
            assert p.read_bytes() == b'X' + performance[1:] and a.read_bytes() == patched
            p.write_bytes(performance)
            a.write_bytes(b'X' + original[1:])
            action = subprocess.run(['sh', str(m / 'action.sh')], text=True, capture_output=True)
            assert 'BUILD MISMATCH:' in action.stdout and 'ACTIVE:' not in action.stdout
            assert a.read_bytes() == b'X' + original[1:] and p.read_bytes() == performance
            a.write_bytes(patched)
            for marker, expected in [('disable', 'Disabled; reboot pending'), ('remove', 'Removal; reboot pending')]:
                (m / marker).touch()
                action = subprocess.run(['sh', str(m / 'action.sh')], text=True, capture_output=True)
                assert expected in action.stdout and 'Next: reboot to finish the change.' in action.stdout
                (m / marker).unlink()
            passed('Action reports mismatched libraries and pending disable/removal without modifying live inputs.')

report.extend(['', 'Not validated locally:', '- Android root-manager mount visibility and SELinux behavior.', '- Performance-service Binder replies on this ROM.', '- Physical USB audio, UI lag, microphones, calls, Bluetooth, and scheduling behavior.', '- Compatibility after any ROM/library update (uninstall before updating).'])
print('\n'.join(report))
