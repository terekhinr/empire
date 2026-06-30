#!/usr/bin/env bash
# Prepare microSD for Teckin TC100 RTSP hack (Anyka AK3918).
# Source: https://github.com/ThatUsernameAlreadyExist/TECKIN-TC100-Anyka-AK3918-camera-hacks
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HACK_SRC="${SCRIPT_DIR}/hack-files"
MOUNT_POINT="${MOUNT_POINT:-/mnt/tc100-sdcard}"

usage() {
  cat <<'EOF'
Usage:
  prepare-sdcard.sh copy-only <mount-point>
      Copy hack files to an already FAT32-formatted card (32 KB clusters).
  prepare-sdcard.sh format <block-device>
      WARNING: erases the device. Formats FAT32 (32 KB clusters) and copies files.
      Example: sudo ./prepare-sdcard.sh format /dev/sdb

Optional env:
  WIFI_SSID=MyNet WIFI_PSK=secret ./prepare-sdcard.sh ...
      Writes wpa_supplicant.conf on the card (Wi-Fi without Teckin app).

After flashing:
  1. Connect camera to Wi-Fi via Teckin app (or use wpa_supplicant.conf).
  2. Insert SD card, power-cycle camera.
  3. RTSP: rtsp://CAMERA-IP:554/video0_unicast  (login root / pass)
  4. Web UI: https://CAMERA-IP
EOF
}

copy_hack_files() {
  local dest="$1"
  if [[ ! -d "$HACK_SRC" ]]; then
    echo "Missing hack-files at $HACK_SRC — run: git clone https://github.com/ThatUsernameAlreadyExist/TECKIN-TC100-Anyka-AK3918-camera-hacks.git $HACK_SRC"
    exit 1
  fi
  echo "Copying hack files to $dest ..."
  rsync -a --delete "$HACK_SRC/" "$dest/"
  if [[ -n "${WIFI_SSID:-}" && -n "${WIFI_PSK:-}" ]]; then
    cat >"$dest/wpa_supplicant.conf" <<EOF
ctrl_interface=/var/run/wpa_supplicant
ctrl_interface_group=0
ap_scan=1
network={
    ssid="${WIFI_SSID}"
    key_mgmt=WPA-PSK
    psk="${WIFI_PSK}"
    priority=2
}
EOF
    echo "Wrote wpa_supplicant.conf (SSID=${WIFI_SSID})"
  fi
  sync
  echo "Done. Safely eject the card before inserting into the camera."
}

cmd_copy_only() {
  local mp="$1"
  if [[ ! -d "$mp" ]]; then
    echo "Mount point not found: $mp"
    exit 1
  fi
  copy_hack_files "$mp"
}

cmd_format() {
  local dev="$1"
  if [[ ! -b "$dev" ]]; then
    echo "Not a block device: $dev"
    exit 1
  fi
  if [[ "$dev" == /dev/sd* ]] && [[ "$dev" =~ [0-9]$ ]]; then
    echo "Use whole disk (e.g. /dev/sdb), not a partition ($dev)."
    exit 1
  fi
  echo "This will ERASE $dev. Type YES to continue:"
  read -r confirm
  [[ "$confirm" == "YES" ]] || { echo "Aborted."; exit 1; }

  if mount | grep -q "^${dev}"; then
    echo "Unmount partitions on $dev first."
    exit 1
  fi

  echo "Creating single FAT32 partition ..."
  parted -s "$dev" mklabel msdos
  parted -s "$dev" mkpart primary fat32 1MiB 100%
  partprobe "$dev" 2>/dev/null || true
  sleep 1

  local part="${dev}1"
  if [[ ! -b "$part" ]]; then
    part="$dev"
  fi

  # 32 KB clusters: 64 sectors × 512 bytes (required by the hack author).
  echo "Formatting $part (FAT32, 32 KB clusters) ..."
  mkfs.vfat -F 32 -n TC100HACK -s 64 -S 512 "$part"

  mkdir -p "$MOUNT_POINT"
  mount "$part" "$MOUNT_POINT"
  copy_hack_files "$MOUNT_POINT"
  umount "$MOUNT_POINT"
  echo "Card ready on $part"
}

main() {
  [[ $# -ge 1 ]] || { usage; exit 1; }
  case "$1" in
    copy-only) [[ $# -eq 2 ]] || { usage; exit 1; }; cmd_copy_only "$2" ;;
    format)    [[ $# -eq 2 ]] || { usage; exit 1; }; cmd_format "$2" ;;
    -h|--help) usage ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
