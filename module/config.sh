# Exact identities of the two user-supplied libraries.
AUDIO_ORIGINAL_SHA256=f080b9f3f607590b00aeca4a4a043eba4d594291bde287b20629ef35591db7fa
AUDIO_PATCHED_SHA256=b334b7ed5a4819eb1a922e958531ea964e985d0482456c42ab969d03c7cbf33e
PERFORMANCE_SHA256=7ae966ef80ef45f7dcda16f011d6454a635690af774dc3bfe84e5ff5caa7fca7
LIVE_AUDIO=/vendor/lib/hw/audio.primary.mt6893.so
LIVE_PERFORMANCE=/odm/lib/vendor.oplus.hardware.performance-V1-ndk_platform.so

file_sha256() {
  sha256sum "$1" 2>/dev/null | awk '{print $1}'
}
