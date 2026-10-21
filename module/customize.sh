#!/system/bin/sh
# Sourced by the root manager after normal ZIP extraction.
# All binary writes are confined to the module's private system overlay.

[ "$BOOTMODE" = true ] || abort "Install this test from your root manager app, not recovery."
case "$ARCH" in
  arm|arm64) ;;
  *) abort "This test requires an ARM device with the exact supplied libraries." ;;
esac
[ -n "$MODPATH" ] && [ -f "$MODPATH/config.sh" ] || abort "Module extraction is incomplete."
. "$MODPATH/config.sh"

FIX_VERSION=$(awk -F= '$1 == "version" { print $2; exit }' "$MODPATH/module.prop" 2>/dev/null)
ui_print ""
ui_print "--------------------------------"
ui_print " MT6893 USB Audio Fix"
ui_print " v${FIX_VERSION:-unknown} | xCaptaiN09"
ui_print "--------------------------------"
ui_print ""
ui_print "[1/3] Verify compatibility"

command -v sha256sum >/dev/null 2>&1 || abort "sha256sum is required for the exact-build checks."
[ -f "$LIVE_AUDIO" ] || abort "The expected 32-bit MT6893 audio library is missing."
[ -f "$LIVE_PERFORMANCE" ] || abort "The expected OPlus performance library is missing."

AUDIO_LIVE_HASH=$(file_sha256 "$LIVE_AUDIO")
case "$AUDIO_LIVE_HASH" in
  "$AUDIO_ORIGINAL_SHA256"|"$AUDIO_PATCHED_SHA256") ;;
  *) abort "Audio library differs from the inspected build. Nothing has been patched." ;;
esac
[ "$(file_sha256 "$LIVE_PERFORMANCE")" = "$PERFORMANCE_SHA256" ] || abort "Performance library differs from the inspected build. Nothing has been patched."
ui_print "      Audio HAL : MATCH"
ui_print "      OPlus lib : MATCH"
ui_print ""
ui_print "[2/3] Prepare repaired copy"

AUDIO_FILE_CONTEXT=$(ls -Zd "$LIVE_AUDIO" 2>/dev/null | awk '{print $1}')
case "$AUDIO_FILE_CONTEXT" in
  u:object_r:*:s0*) ;;
  *) abort "Could not read the original library's SELinux context." ;;
esac

PATCH_AUDIO="$MODPATH/system/vendor/lib/hw/audio.primary.mt6893.so"
mkdir -p "$MODPATH/system/vendor/lib/hw" || abort "Cannot create the module overlay."
cp -p "$LIVE_AUDIO" "$PATCH_AUDIO" || abort "Cannot copy the audio library into the module."

# ARM LDR r3,[r0,#0xcc] -> LDR r3,[r0,#0xd0]
# Select getKernelVersion(int*) rather than getHIUfsFeature(ProcReqHal*).
printf '\320' | dd of="$PATCH_AUDIO" bs=1 seek=2763936 count=1 conv=notrunc 2>/dev/null || abort "First patch failed."

# ARM LDR r6,[r0,#0x270] -> LDR r6,[r0,#0x274]
# Select writeUxState(strings...,int*) rather than writeTidsSet(string).
printf '\164' | dd of="$PATCH_AUDIO" bs=1 seek=2764092 count=1 conv=notrunc 2>/dev/null || abort "Second patch failed."

ui_print "      Method targets : 2 corrected"
ui_print ""
ui_print "[3/3] Verify output"
[ "$(file_sha256 "$PATCH_AUDIO")" = "$AUDIO_PATCHED_SHA256" ] || abort "Patched checksum failed; installation aborted."
set_perm_recursive "$MODPATH/system" 0 0 0755 0644
set_perm_recursive "$MODPATH/system/vendor" 0 0 0755 0644 u:object_r:vendor_file:s0
set_perm "$PATCH_AUDIO" 0 0 0644 "$AUDIO_FILE_CONTEXT"
set_perm "$MODPATH/action.sh" 0 0 0755

ui_print "      SHA-256     : MATCH"
ui_print "      Permissions: SET"
ui_print ""
ui_print "READY - reboot to activate."
ui_print "After reboot, open Action."
ui_print "Then connect USB audio and test."
ui_print ""
ui_print "Undo: disable/remove, then reboot."
ui_print "Remove before a ROM update."
