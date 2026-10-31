#!/bin/sh
# Постоянный Tailscale на Flint (доступ к роутеру без VPS).
# Откат: /usr/sbin/empire-tailscale-rollback.sh
set -eu
export PATH="/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

HOSTNAME_TS="${HOSTNAME_TS:-flint2}"

mkdir -p /etc/empire /etc/tailscale/statedir

# firewall: вход с tailscale0
if ! uci show firewall 2>/dev/null | grep -q "name='tailscale'"; then
  uci add firewall zone >/dev/null
  uci set firewall.@zone[-1].name="tailscale"
  uci set firewall.@zone[-1].input="ACCEPT"
  uci set firewall.@zone[-1].output="ACCEPT"
  uci set firewall.@zone[-1].forward="REJECT"
  uci add_list firewall.@zone[-1].device="tailscale0"
  uci commit firewall
  fw4 reload 2>/dev/null || /etc/init.d/firewall reload 2>/dev/null || true
fi

/etc/init.d/tailscale enable 2>/dev/null || true
/etc/init.d/tailscale start 2>/dev/null || true
sleep 2

# node-only: быстрый доступ к роутеру. LAN — через armbian Subnets (уже Approve).
/usr/sbin/tailscale up \
  --hostname="$HOSTNAME_TS" \
  --accept-routes=false \
  --accept-dns=false \
  --netfilter-mode=off \
  --timeout=30s 2>&1 || true

/usr/sbin/tailscale set --netfilter-mode=off --accept-dns=false 2>/dev/null || true

# reboot hook: netfilter off после старта
cat >/etc/rc.local.d-empire-ts.sh <<'EOF'
#!/bin/sh
sleep 8
/usr/sbin/tailscale set --netfilter-mode=off --accept-dns=false 2>/dev/null || true
EOF
chmod +x /etc/rc.local.d-empire-ts.sh 2>/dev/null || true

# отключить trial-watchdog если остался
rm -f /tmp/empire-ts-trial/watchdog.pid /tmp/empire-ts-trial/end_epoch
touch /etc/empire/ts-permanent
rm -f /etc/empire/ts-trial-hold

echo "OK Tailscale permanent"
/usr/sbin/tailscale status 2>&1 | head -8
/usr/sbin/tailscale ip -4 2>&1 || true
echo "Rollback: sh /usr/sbin/empire-tailscale-rollback.sh"
