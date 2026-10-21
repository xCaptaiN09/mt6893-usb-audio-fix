# Installation and status checks

## Installer rejects a library version

Stop and keep the rejection message. The installer supports only the full hashes in `module/config.sh`. Do not remove the guard or apply these offsets to a different library merely because the filename or chipset matches.

## Action says NOT ACTIVE

This means Action can see the original library in its own mount namespace. It does not by itself establish what every system process sees.

For the tested KernelSU Next + Magic Mount-rs setup:

1. Confirm the metamodule is installed and enabled.
2. If the audio module was installed first, reinstall the same audio ZIP with the backend already present.
3. Check for `Using mmrs metainstall` and `Handle partition /vendor` in the installer output.
4. Reboot and check Action again.

Useful read-only checks in Termux:

```sh
su
ls -ld /data/adb/modules/mt6893-usb-audio-fix/vendor /data/adb/modules/mt6893-usb-audio-fix/system/vendor
sha256sum /proc/1/root/vendor/lib/hw/audio.primary.mt6893.so
logcat -d -s MagicMount:V '*:S' | tail -n 60
```

The expected patched hash starts with `b334b7ed`; the original starts with `f080b9f3`. Compare the complete values in the README. `/proc/1/root` checks init's filesystem view; it does not directly inspect the bytes already mapped into a particular audio-service process. A reboot is part of the test procedure.

An empty filtered logcat result means no matching messages were returned from the retained buffers. It does not prove that the backend succeeded.

## Action says ACTIVE but audio is still silent

Check OTG, the selected playback output, volume, and that **Disable USB audio routing** is off. Record a short new reproduction with its timestamp and capture relevant crash/system logs. Old crash-buffer entries can survive earlier tests and do not prove a new failure.

Report the ROM, real kernel version if spoofing is enabled, root manager, backend, full checksums, Action output, and whether speaker playback still works. Redact personal data before posting logs. Do not upload vendor binaries into the repository.

## Undo or update the ROM

Disable/remove the audio module and reboot. The module does not overwrite the original partition file. Remove it before a ROM/library update because compatibility checks run only at installation.
