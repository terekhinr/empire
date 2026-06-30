#!/usr/bin/env bash
# Generate wpa_supplicant.conf for TC100 SD hack (Wi-Fi without Teckin app).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$SCRIPT_DIR/wpa_supplicant.conf}"

read -r -p "Wi-Fi SSID (2.4 GHz): " SSID
read -r -s -p "Wi-Fi password: " PSK
echo

cat >"$OUT" <<EOF
ctrl_interface=/var/run/wpa_supplicant
ctrl_interface_group=0
ap_scan=1
network={
    ssid="${SSID}"
    key_mgmt=WPA-PSK
    psk="${PSK}"
    priority=2
}
EOF

echo "Written: $OUT"
echo "Copy to microSD root together with hack-files/, then reboot camera (SD must stay inserted)."
