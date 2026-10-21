# MT6893 USB Audio Fix

Systemless repair for USB audio crashes on the tested Realme X7 Max ColorOS 17 port.

**Version:** `0.1-test` · **License:** [MIT](LICENSE) · **Maintainer:** [xCaptaiN09](https://github.com/xCaptaiN09)

[Download module](releases/mt6893-usb-audio-fix-v0.1-test.zip?raw=1) · [Technical details](docs/analysis.md) · [Troubleshooting](docs/troubleshooting.md)

## What it fixes

On the tested ROM, connecting a Moondrop Chu2 DSP caused silent playback and repeated MediaTek audio-service crashes. The audio HAL was calling incompatible methods in the OPlus performance library.

This module corrects two call targets by changing two bytes in a module-local copy of the audio library. The root manager mounts the repaired copy; the original partition file is preserved.

**USB music playback is confirmed working after activation.** Calls, microphones, Bluetooth, long-term stability, and the earlier UI lag have not yet been verified after the fix.

## Compatibility

| Component | Tested setup |
| --- | --- |
| Device | Realme X7 Max / MT6893 |
| ROM | ColorOS 17 custom port |
| Kernel | 4.19.325 |
| Root | KernelSU Next v3.4.1-legacy |
| Mount backend | Magic Mount-rs v4.0.12-941 |
| Earphones | Moondrop Chu2 DSP |

Compatibility depends on the **exact audio and performance libraries**. The installer checks both hashes and rejects other versions. Other USB-C earphones may benefit from the same repair, but have not been tested. Other phones, ROMs, and root setups are unverified.

## Installation

1. Install [Magic Mount-rs v4.0.12](https://github.com/Tools-cx-app/meta-magic_mount-rs/releases/tag/v4.0.12) in KernelSU Next and reboot. Skip this step if the tested backend is already installed and enabled.
2. Download the [audio-fix ZIP](releases/mt6893-usb-audio-fix-v0.1-test.zip?raw=1).
3. Open **KernelSU Next → Modules**, install the ZIP, and reboot.
4. Open the audio module and tap **Action**. It should show **ACTIVE** and a matching performance library.
5. Enable **OTG**, keep **Disable USB audio routing** switched **off**, connect the earphones, and play music.

No Python or Termux setup is needed to install the module. Flash it through the root manager, not recovery.

### If Action says NOT ACTIVE

If the audio module was installed before Magic Mount-rs, reinstall the same audio ZIP with the backend enabled, then reboot. The tested installer printed `Using mmrs metainstall` and `Handle partition /vendor`.

See [troubleshooting](docs/troubleshooting.md) if activation still fails.

## Uninstall and ROM updates

Disable or remove the audio module in KernelSU Next, then reboot.

**Remove it before updating the ROM or replacing either library.** The version checks run during installation, not at every boot.

## Build from source

On a PC with Python 3.10 or newer:

```sh
python tools/build.py
```

The installable ZIP is created in `dist/`. Building requires only the Python standard library. The source is in [`module/`](module/).

`tools/verify_libraries.py` is an optional development tool for checking the exact binary patch and installer behavior. Its dependencies are listed in `requirements-analysis.txt`; normal installation and packaging do not need them. Supply your own original library copies when running it.

## Documentation

- [Analysis](docs/analysis.md): crash signature, method mismatch, and patch offsets.
- [Testing](docs/testing.md): completed checks and remaining test coverage.
- [Troubleshooting](docs/troubleshooting.md): mounting checks, status messages, and recovery steps.

## License

Maintained by **Muhammed Dilshad A ([xCaptaiN09](https://github.com/xCaptaiN09))**.

Project code and documentation are available under the [MIT License](LICENSE). Vendor libraries are not bundled or relicensed. KernelSU Next and Magic Mount-rs retain their own licenses.
