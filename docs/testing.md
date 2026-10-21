# Testing and results

## Device result

Reported by xCaptaiN09 on **22 October 2026, India time** (21 October UTC).

| Check | Result and evidence |
| --- | --- |
| Installation through Magic Mount-rs | Confirmed by installer output: `Using mmrs metainstall` |
| Backend mounting | Backend reported one mounted file/symbol after reboot |
| Patch visibility | Action reported the complete expected patched checksum |
| Performance-library identity | Action reported a match to the inspected library |
| Physical USB music playback | User confirmed: song working with good sound |
| SystemUI lag resolved | Not yet reported after the successful installation |
| Speaker, calls, microphone, Bluetooth | Not yet reported after the successful installation |
| Long-term stability or other ROMs | Not tested |

The successful playback result was user-reported. The verifier cannot perform this physical test. No fresh post-fix crash capture was supplied to establish that every audio crash had stopped.

## Local checks

The optional `tools/verify_libraries.py` performs the same substantive checks used during development:

- Full original and performance-library SHA-256 checks.
- ELF class, architecture, virtual-address-to-file-offset mapping, and original instruction bytes.
- ARM instruction decoding and the exact two-byte output hash.
- Android APS2 packed relocation decoding and actual `BpPerformance` vtable resolution.
- ARM emulation of each original/patched load to verify method selection and destination register.
- Inspection for direct property-get calls in `setAudioHalSchedToUx`.
- POSIX shell syntax and LF line endings.
- Real installer script in temporary fixtures, with permission/SELinux helpers mocked.
- Accepted original input and accepted already-patched reinstall.
- Rejected wrong audio hash, wrong performance hash, recovery mode, and unsupported architecture.
- Input files remain untouched; the module-copy output has the expected bytes.
- Action distinguishes original and patched fixture files.



## Packaging checks

`tools/build.py` checks the expected source file set, LF text, required module ID, archive integrity, root-level installer files, safe entry names, and the absence of bundled `.so` files.

The library and installer verifier passed using the exact supplied library pair. Documentation and author metadata changes produce a new package checksum.

These results do not validate Android Binder behavior, kernel compatibility on another device, every SELinux configuration, or untested audio functions.
