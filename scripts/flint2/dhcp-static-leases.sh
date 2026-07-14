#!/bin/sh
# Static DHCP — автоген из keenetic-export.json
set -eu
# очистка старых host-секций (OpenWrt)
while uci -q delete dhcp.@host[0]; do :; done

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='8c:4b:14:ea:e1:28'
uci set dhcp.@host[-1].ip='192.168.1.101'
uci set dhcp.@host[-1].name='SmartIntercom'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='94:de:80:64:ed:e6'
uci set dhcp.@host[-1].ip='192.168.1.112'
uci set dhcp.@host[-1].name='WIN-2IK85AJ86AQ'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='b8:87:6e:80:52:40'
uci set dhcp.@host[-1].ip='192.168.1.113'
uci set dhcp.@host[-1].name='yandex-station-lite'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='e8:f4:94:fe:6d:36'
uci set dhcp.@host[-1].ip='192.168.1.119'
uci set dhcp.@host[-1].name='H1c-BF5488322-EZVIZ'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='00:ae:f7:6b:c9:b8'
uci set dhcp.@host[-1].ip='192.168.1.121'
uci set dhcp.@host[-1].name='dreame-vacuum-r5021a'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='e8:68:e7:8e:31:0a'
uci set dhcp.@host[-1].ip='192.168.1.123'
uci set dhcp.@host[-1].name='ESP-8E310A'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='b8:99:ae:6a:d7:62'
uci set dhcp.@host[-1].ip='192.168.1.124'
uci set dhcp.@host[-1].name='Приставка_детская_ви_фи_b8_99_ae'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='04:05:dd:c5:eb:a4'
uci set dhcp.@host[-1].ip='192.168.1.141'
uci set dhcp.@host[-1].name='СберТелек_04_05_dd_c5_eb_a4'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='70:89:76:35:8e:16'
uci set dhcp.@host[-1].ip='192.168.1.143'
uci set dhcp.@host[-1].name='wlan0'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='88:46:04:51:4c:13'
uci set dhcp.@host[-1].ip='192.168.1.148'
uci set dhcp.@host[-1].name='M2012K11AG'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='84:e3:42:52:69:4a'
uci set dhcp.@host[-1].ip='192.168.1.190'
uci set dhcp.@host[-1].name='TY-WR'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='b8:87:6e:77:9c:a0'
uci set dhcp.@host[-1].ip='192.168.1.33'
uci set dhcp.@host[-1].name='yandex-station-lite'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='bc:fa:b8:c5:e7:90'
uci set dhcp.@host[-1].ip='192.168.1.34'
uci set dhcp.@host[-1].name='TECKIN-YZ01F37'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='40:ca:63:2a:6e:3d'
uci set dhcp.@host[-1].ip='192.168.1.38'
uci set dhcp.@host[-1].name='washer'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='1c:90:ff:a5:50:e7'
uci set dhcp.@host[-1].ip='192.168.1.40'
uci set dhcp.@host[-1].name='wlan0'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='a8:21:08:f0:34:d7'
uci set dhcp.@host[-1].ip='192.168.1.41'
uci set dhcp.@host[-1].name='armbian'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='e0:cb:ee:8a:5a:2b'
uci set dhcp.@host[-1].ip='192.168.1.52'
uci set dhcp.@host[-1].name='android-f0d02d77ecfbd6e7'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='b0:02:47:4d:93:76'
uci set dhcp.@host[-1].ip='192.168.1.55'
uci set dhcp.@host[-1].name='YandexStationMini-9376'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='60:56:ee:f4:89:af'
uci set dhcp.@host[-1].ip='192.168.1.56'
uci set dhcp.@host[-1].name='H1c-BF0241992-EZVIZ'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='c0:06:c3:39:7e:ce'
uci set dhcp.@host[-1].ip='192.168.1.58'
uci set dhcp.@host[-1].name='RE200'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='c6:06:c3:39:7e:cf'
uci set dhcp.@host[-1].ip='192.168.1.59'
uci set dhcp.@host[-1].name='RE200'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='a8:21:02:c9:60:5b'
uci set dhcp.@host[-1].ip='192.168.1.60'
uci set dhcp.@host[-1].name='Проектор_провод_a8_21_02_c9_60_5'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='86:84:d9:77:8e:86'
uci set dhcp.@host[-1].ip='192.168.1.71'
uci set dhcp.@host[-1].name='Pixel-9a'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='bc:fa:b8:be:18:7b'
uci set dhcp.@host[-1].ip='192.168.1.84'
uci set dhcp.@host[-1].name='Front_Door'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='70:03:9f:6a:97:d3'
uci set dhcp.@host[-1].ip='192.168.1.85'
uci set dhcp.@host[-1].name='ESP-6A97D3'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='6a:33:7d:43:85:f7'
uci set dhcp.@host[-1].ip='192.168.1.88'
uci set dhcp.@host[-1].name='Pixel-4a'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='e8:68:e7:44:79:39'
uci set dhcp.@host[-1].ip='192.168.1.90'
uci set dhcp.@host[-1].name='ESP-447939'

uci add dhcp host 2>/dev/null || true
uci set dhcp.@host[-1].mac='94:83:c4:df:8a:b2'
uci set dhcp.@host[-1].ip='192.168.1.99'
uci set dhcp.@host[-1].name='OpenWrt'

uci commit dhcp
/etc/init.d/dnsmasq restart
