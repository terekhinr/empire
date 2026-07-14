#!/bin/sh
# Открыть SSH/HTTP на WAN Flint с LAN (один раз, с ПК в LAN Flint или после cutover).
set -eu
uci add firewall rule 2>/dev/null || true
uci set firewall.@rule[-1].name='Allow-SSH-WAN'
uci set firewall.@rule[-1].src='wan'
uci set firewall.@rule[-1].proto='tcp'
uci set firewall.@rule[-1].dest_port='22'
uci set firewall.@rule[-1].target='ACCEPT'
uci add firewall rule 2>/dev/null || true
uci set firewall.@rule[-1].name='Allow-HTTP-WAN'
uci set firewall.@rule[-1].src='wan'
uci set firewall.@rule[-1].proto='tcp'
uci set firewall.@rule[-1].dest_port='80'
uci set firewall.@rule[-1].target='ACCEPT'
uci commit firewall
/etc/init.d/firewall reload
echo "WAN SSH/HTTP open"
