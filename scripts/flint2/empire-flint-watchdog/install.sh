#!/bin/bash
# Установка empire-flint-watchdog + PWA UI на Flint (reverse SSH :6223).
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
SSH=(ssh -p 6223 -o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new root@127.0.0.1)
EMPIRE_ROOT="$(cd "$ROOT/../../.." && pwd)"

echo "==> upload watchdog"
"${SSH[@]}" 'cat > /tmp/empire-flint-watchdog' <"$ROOT/empire-flint-watchdog"
"${SSH[@]}" 'cat > /tmp/empire-flint-watchdog.init' <"$ROOT/empire-flint-watchdog.init"
"${SSH[@]}" 'cat > /tmp/empire-usb-mount.init' <"$ROOT/empire-usb-mount.init"
"${SSH[@]}" 'cat > /tmp/hotplug-20-empire-usb' <"$ROOT/hotplug-20-empire-usb"
"${SSH[@]}" 'cat > /tmp/empire-api' <"$ROOT/cgi/empire-api"
"${SSH[@]}" 'cat > /tmp/empire-lan-fix.sh' <"$ROOT/empire-lan-fix.sh"
"${SSH[@]}" 'cat > /tmp/empire-lan-watch.sh' <"$ROOT/empire-lan-watch.sh"
"${SSH[@]}" 'cat > /tmp/torrent-domains.txt' <"$ROOT/../torrent-domains.txt"
"${SSH[@]}" 'cat > /tmp/block-doh.nft' <"$ROOT/block-doh.nft"
"${SSH[@]}" 'cat > /tmp/99-block-doh.conf' <"$ROOT/99-block-doh.conf"

echo "==> upload PWA www"
"${SSH[@]}" 'rm -rf /tmp/empire-www && mkdir -p /tmp/empire-www'
for f in index.html app.js styles.css manifest.json sw.js icon-192.png icon-512.png usb.html usb-disk.bat; do
  "${SSH[@]}" "cat > /tmp/empire-www/$f" <"$ROOT/www/$f"
done

# token + HA env from VPS .env
TOKEN_LOCAL=/etc/empire/flint-ui.token
mkdir -p /etc/empire
if [[ ! -f "$TOKEN_LOCAL" ]]; then
  TOKEN=$(openssl rand -hex 16)
  echo -n "$TOKEN" >"$TOKEN_LOCAL"
  chmod 600 "$TOKEN_LOCAL"
  echo "==> generated token → $TOKEN_LOCAL"
else
  TOKEN=$(tr -d '\r\n' <"$TOKEN_LOCAL")
  echo "==> reuse token from $TOKEN_LOCAL"
fi

HA_URL='http://192.168.1.41:8123'
HA_TOKEN=$(grep -E '^HA_TOKEN=' "$EMPIRE_ROOT/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' || true)

echo "==> install on Flint"
"${SSH[@]}" "cat > /tmp/empire-flint-ui.token" <<<"$TOKEN"
{
  echo "HA_URL=$HA_URL"
  echo "HA_TOKEN=$HA_TOKEN"
} | "${SSH[@]}" 'cat > /tmp/empire-flint-ui.env'

"${SSH[@]}" 'sh -s' <<'EOF'
set -eu
mv /tmp/empire-flint-watchdog /usr/sbin/empire-flint-watchdog
chmod 755 /usr/sbin/empire-flint-watchdog
sed -i 's/\r$//' /usr/sbin/empire-flint-watchdog

mv /tmp/empire-lan-fix.sh /etc/podkop/empire-lan-fix.sh
chmod 755 /etc/podkop/empire-lan-fix.sh
sed -i 's/\r$//' /etc/podkop/empire-lan-fix.sh
mv /tmp/empire-lan-watch.sh /etc/podkop/empire-lan-watch.sh
chmod 755 /etc/podkop/empire-lan-watch.sh
sed -i 's/\r$//' /etc/podkop/empire-lan-watch.sh
mv /tmp/torrent-domains.txt /etc/podkop/torrent-domains.txt
sed -i 's/\r$//' /etc/podkop/torrent-domains.txt
mv /tmp/block-doh.nft /etc/podkop/block-doh.nft
sed -i 's/\r$//' /etc/podkop/block-doh.nft
mkdir -p /etc/dnsmasq.d /tmp/dnsmasq.d
mv /tmp/99-block-doh.conf /etc/dnsmasq.d/99-block-doh.conf
cp -a /etc/dnsmasq.d/99-block-doh.conf /tmp/dnsmasq.d/99-block-doh.conf
sed -i 's/\r$//' /etc/dnsmasq.d/99-block-doh.conf

mv /tmp/empire-flint-watchdog.init /etc/init.d/empire-flint-watchdog
chmod 755 /etc/init.d/empire-flint-watchdog
sed -i 's/\r$//' /etc/init.d/empire-flint-watchdog

mv /tmp/empire-usb-mount.init /etc/init.d/empire-usb-mount
chmod 755 /etc/init.d/empire-usb-mount
sed -i 's/\r$//' /etc/init.d/empire-usb-mount
mkdir -p /etc/hotplug.d/block
mv /tmp/hotplug-20-empire-usb /etc/hotplug.d/block/20-empire-usb
chmod 755 /etc/hotplug.d/block/20-empire-usb
sed -i 's/\r$//' /etc/hotplug.d/block/20-empire-usb
/etc/init.d/empire-usb-mount enable 2>/dev/null || true
/etc/init.d/empire-usb-mount start 2>/dev/null || true

mkdir -p /www/cgi-bin /www/empire
mv /tmp/empire-api /www/cgi-bin/empire-api
chmod 755 /www/cgi-bin/empire-api
sed -i 's/\r$//' /www/cgi-bin/empire-api

cp -a /tmp/empire-www/. /www/empire/
# убрать случайно лежавшие ключи из webroot
rm -f /www/phone.conf /www/phone.key /www/phone.pub 2>/dev/null || true

mv /tmp/empire-flint-ui.token /etc/empire-flint-ui.token
chmod 600 /etc/empire-flint-ui.token
mv /tmp/empire-flint-ui.env /etc/empire-flint-ui.env
chmod 600 /etc/empire-flint-ui.env

# uhttpd cgi already /cgi-bin — ensure enabled
uci set uhttpd.main.cgi_prefix='/cgi-bin'
uci set uhttpd.main.home='/www'
uci set uhttpd.main.rfc1918_filter='0'
uci commit uhttpd
/etc/init.d/uhttpd restart

# cron: minute lan-watch + 5min full watchdog
CRON_FILE=/etc/crontabs/root
mkdir -p /etc/crontabs /etc/podkop
grep -vE 'empire-flint-watchdog|empire-lan-watch' "$CRON_FILE" >"${CRON_FILE}.tmp" 2>/dev/null || true
mv "${CRON_FILE}.tmp" "$CRON_FILE" 2>/dev/null || : >"$CRON_FILE"
echo '* * * * * /etc/podkop/empire-lan-watch.sh' >>"$CRON_FILE"
echo '*/5 * * * * /usr/sbin/empire-flint-watchdog >/dev/null 2>&1' >>"$CRON_FILE"
/etc/init.d/cron enable 2>/dev/null || true
/etc/init.d/cron restart 2>/dev/null || true
ln -sf /etc/init.d/empire-flint-watchdog /etc/rc.d/S99empire-flint-watchdog 2>/dev/null || true

# golden snapshot + first heal pass
/usr/sbin/empire-flint-watchdog >/dev/null 2>&1 || true

echo "PWA http://192.168.1.1/empire/"
echo "API /cgi-bin/empire-api"
EOF

echo "==> smoke API status (keys only)"
"${SSH[@]}" 'TOKEN=$(cat /etc/empire-flint-ui.token); wget -qO- "http://127.0.0.1/cgi-bin/empire-api?action=status&token=$TOKEN" | grep -oE "\"(ok|youtube|ha|usb)\":[a-z]+" | head -6'

echo "==> token file on VPS: $TOKEN_LOCAL"
echo "OK — open http://192.168.1.1/empire/?token=\$(cat $TOKEN_LOCAL)"
echo "     or https://neverretire.ru/home-ops/ (тот же токен)"
