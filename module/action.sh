#!/system/bin/sh
MODDIR=${0%/*}
if [ ! -r "$MODDIR/config.sh" ]; then
  printf '%s\n' 'Module configuration is missing.' 'Reinstall the module ZIP.'
  exit 1
fi
. "$MODDIR/config.sh"

FIX_VERSION=$(awk -F= '$1 == "version" { print $2; exit }' "$MODDIR/module.prop" 2>/dev/null)
FIX_AUDIO_HASH=$(file_sha256 "$LIVE_AUDIO")
FIX_PERF_HASH=$(file_sha256 "$LIVE_PERFORMANCE")
FIX_AUDIO_LABEL='Unsupported'
case "$FIX_AUDIO_HASH" in
  "$AUDIO_PATCHED_SHA256") FIX_AUDIO_LABEL='Patched' ;;
  "$AUDIO_ORIGINAL_SHA256") FIX_AUDIO_LABEL='Original' ;;
esac
FIX_PERF_LABEL='MISMATCH'
[ "$FIX_PERF_HASH" = "$PERFORMANCE_SHA256" ] && FIX_PERF_LABEL='MATCH'
FIX_MODULE_LABEL='Enabled'
[ -f "$MODDIR/disable" ] && FIX_MODULE_LABEL='Disabled; reboot pending'
[ -f "$MODDIR/remove" ] && FIX_MODULE_LABEL='Removal; reboot pending'
FIX_AUDIO_PID=$(pidof audioserver 2>/dev/null)

printf '\n%s\n' '--------------------------------'
printf '%s\n' ' MT6893 USB Audio Fix'
printf ' v%s | xCaptaiN09\n' "${FIX_VERSION:-unknown}"
printf '%s\n\n' '--------------------------------'

if [ "$FIX_AUDIO_LABEL" = 'Unsupported' ] || [ "$FIX_PERF_LABEL" = 'MISMATCH' ]; then
  printf '%s\n' 'BUILD MISMATCH: unsupported files'
elif [ "$FIX_AUDIO_LABEL" = 'Patched' ]; then
  printf '%s\n' 'ACTIVE: patched library visible'
else
  printf '%s\n' 'NOT ACTIVE: original library visible'
fi

printf '\nAudio HAL  : %s\n' "$FIX_AUDIO_LABEL"
printf 'Performance: %s\n' "$FIX_PERF_LABEL"
printf 'Module     : %s\n' "$FIX_MODULE_LABEL"
printf 'audioserver: %s\n\n' "${FIX_AUDIO_PID:-Not running}"

if [ -f "$MODDIR/disable" ] || [ -f "$MODDIR/remove" ]; then
  printf '%s\n' 'Next: reboot to finish the change.'
elif [ "$FIX_AUDIO_LABEL" = 'Unsupported' ] || [ "$FIX_PERF_LABEL" = 'MISMATCH' ]; then
  printf '%s\n' 'Next: disable this module and reboot.' 'Check compatibility before reinstalling.'
elif [ "$FIX_AUDIO_LABEL" = 'Original' ]; then
  printf '%s\n' 'Next: reboot and check again.' 'If unchanged, check the mount backend.'
else
  printf '%s\n' 'Next: play a song to check sound.'
fi
