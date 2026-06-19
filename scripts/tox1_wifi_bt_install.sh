#!/bin/bash
# TOX1 RTL8822BS: WiFi + Bluetooth (после свежего Armbian / restore HA).
# Запуск на боксе (root): bash tox1_wifi_bt_install.sh
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y bluez bluetooth network-manager

cat > /etc/modprobe.d/tox1-bt-delay.conf <<'EOF'
blacklist hci_uart
install hci_uart /bin/true
EOF

cat > /usr/local/sbin/tox1-wireless-init.sh <<'SCRIPT'
#!/bin/bash
set -uo pipefail
log() { echo "[tox1-wireless] $*"; }
systemctl stop bluetooth 2>/dev/null || true
if [ -e /sys/bus/serial/drivers/hci_uart_h5/serial0-0 ]; then
  echo serial0-0 > /sys/bus/serial/drivers/hci_uart_h5/unbind 2>/dev/null || true
  sleep 1
fi
log "Loading WiFi rtw88_8822bs"
modprobe -r rtw88_8822bs 2>/dev/null || true
sleep 1
modprobe rtw88_8822bs
for i in $(seq 1 30); do ip link show wlan0 &>/dev/null && break; sleep 1; done
ip link set wlan0 up 2>/dev/null || true
log "wlan0: $(ip -br link show wlan0 2>/dev/null || echo missing)"
rm -f /etc/modprobe.d/tox1-bt-delay.conf
depmod -a 2>/dev/null || true
( modprobe hci_uart 2>/dev/null; [ -e /sys/bus/serial/drivers/hci_uart_h5/bind ] && echo serial0-0 > /sys/bus/serial/drivers/hci_uart_h5/bind 2>/dev/null; systemctl start bluetooth 2>/dev/null ) &
log "BT init in background"
SCRIPT
chmod +x /usr/local/sbin/tox1-wireless-init.sh

echo rtw88_8822bs > /etc/modules-load.d/tox1-wifi.conf

cat > /etc/systemd/system/tox1-wireless.service <<'UNIT'
[Unit]
Description=TOX1 WiFi before Bluetooth (RTL8822BS)
DefaultDependencies=no
After=local-fs.target
Before=bluetooth.service NetworkManager.service sysinit.target
Wants=local-fs.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/tox1-wireless-init.sh
TimeoutStartSec=60

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable tox1-wireless.service
/usr/local/sbin/tox1-wireless-init.sh

echo "=== wlan0 ==="
ip -br link show wlan0 || true
iw dev wlan0 scan 2>/dev/null | grep -E '^BSS|SSID' | head -10 || echo "scan: подключите WiFi вручную: nmcli device wifi list"

echo "=== bluetooth ==="
hciconfig -a 2>/dev/null | head -6 || true

echo "Готово. WiFi: nmcli device wifi connect SSID password PASS"
