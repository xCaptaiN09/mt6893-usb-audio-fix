# Technical analysis

## Observed failure

The device recognized `USB-Audio - Chu2 DSP` at ALSA `card=1;device=0`. Policy dumps selected the USB headset, but a playback-state sample during music playback reported `closed` and `Status: Stop`. The user also reported SystemUI lag.

Those early observations established detection and an unsuccessful playback path. They did not independently establish a missing audio-policy XML definition, an effects failure, or a USB power-management problem.

The subsequently collected crash buffer contained **29 complete MediaTek audio-service SIGSEGV reports** with the same relevant stack. It also began with a partial earlier report. The system log showed audio-service deaths and repeated USB-device reconnection during recovery.

Relevant stack frames, from the crashing operation toward its caller:

```text
vendor.oplus.hardware.performance-V1-ndk_platform.so
  AParcel_stdVectorExternalAllocator<ProcReqItemHal>
libbinder_ndk.so
  AParcel_readParcelableArray
vendor.oplus.hardware.performance-V1-ndk_platform.so
  ProcReqHal::readFromParcel
  BpPerformance::getHIUfsFeature
audio.primary.mt6893.so
  setAudioHalSchedToUx+504
  sw_mixer_mix_thread_hal+628
```

This is a crash in `/vendor/bin/hw/android.hardware.audio.service.mediatek`, in its `mix1:0` thread. The related `audioserver` and registered media services also disappeared/restarted; they are not interchangeable names for the crashing vendor executable.

## Exact library analysis

Both supplied libraries are 32-bit ARM ELF files. The inspected function uses ARM instructions rather than Thumb instructions. Android APS2 packed relocations were decoded to resolve the performance library's actual `BpPerformance` virtual-method table.

| Audio instruction VA | File offset | Original bytes | Patched bytes |
| --- | --- | --- | --- |
| `0x002a3ca0` | `0x002a2ca0` / 2763936 | `cc 30 90 e5` | `d0 30 90 e5` |
| `0x002a3d3c` | `0x002a2d3c` / 2764092 | `70 62 90 e5` | `74 62 90 e5` |

The first change is:

```text
ldr r3, [r0, #0xcc]  ->  ldr r3, [r0, #0xd0]
```

The caller supplies an integer-output pointer and later compares the result against `419`. In the supplied performance library, slot `0xcc` selects `getHIUfsFeature(ProcReqHal*)`; slot `0xd0` selects the signature-compatible `getKernelVersion(int*)`. Deserializing a larger `ProcReqHal` object through storage supplied for an integer is incompatible with the caller and matches the observed failing stack.

The second change is:

```text
ldr r6, [r0, #0x270]  ->  ldr r6, [r0, #0x274]
```

That caller supplies three strings and an integer-output pointer, matching `writeUxState`. The original slot instead selects `writeTidsSet(string)`. The original crash signature is at the first call; the second mismatch was identified during inspection of the same function.

Exactly two bytes differ in the completed audio file. File size remains **3,107,960 bytes**. The ELF layout and embedded Build ID remain unchanged, so use full SHA-256 hashes to distinguish the original and patched files.

| Library | Embedded Build ID |
| --- | --- |
| Audio HAL | `58e0eba3964dca0ffaaf9e86f33bdfc0` |
| OPlus performance client | `95e980e49993d3f762b69ab247de76c7` |

No direct property-get call was found in the inspected function that provided a verified configuration-based bypass. This repair adjusts the method targets and preserves the intended scheduling operations.

## Separate installation problem

The first installed module contained the expected patched file, but `/proc/1/root/vendor/lib/hw/audio.primary.mt6893.so` still had the original hash. Initially no mount metamodule was installed. After Magic Mount-rs was installed, the existing audio module still used this layout:

```text
module/system/vendor -> ../vendor
module/vendor/       contains the actual files
```

The inspected Magic Mount-rs v4.0.12 scanner classifies symlinks without traversing them as module directories. Its module installer overrides partition handling to keep actual files under `system/vendor`, with a top-level vendor symlink where required. Reinstalling the audio ZIP after the backend was present applied that layout.

The successful installation printed `Using mmrs metainstall` and `Handle partition /vendor`. After reboot, the backend reported one mounted file/symbol, Action reported the expected patched hash, and the user confirmed music playback with good sound.

References to the exact upstream implementation inspected:

- [Magic Mount-rs v4.0.12 module installer](https://github.com/Tools-cx-app/meta-magic_mount-rs/blob/v4.0.12/module/metainstall.sh)
- [Magic Mount-rs v4.0.12 module scanner/mounter](https://github.com/Tools-cx-app/meta-magic_mount-rs/blob/v4.0.12/src/magic_mount.rs)

## Evidence limits

The repeated stack, mismatched method signatures, exact two-byte change, and successful playback after activation support the repair on this library pair. The test does not establish compatibility with all MT6893 ROMs, every USB device, or later firmware.

The original logs also contained Trustonic/Soter crashes with a different signature (`Could not register Trustonic ISoter Service`). No causal connection to USB silence was established. This module does not address them.

Raw device logs, screenshots, complete ROM fingerprints, and vendor binaries are omitted from the public package. The findings above retain the details needed to understand and reproduce the exact-library verification.
