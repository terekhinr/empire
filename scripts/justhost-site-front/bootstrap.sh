#!/bin/bash
# Temporary site front on JustHost Vienna (132.243.254.241).
# Keeps VLESS Reality on public :443 via nginx stream SNI split;
# empire hostnames go to local :8443 → proxy HTTP to Aeza 138.124.90.47.
#
# Run ON JustHost as root:
#   curl -fsSL http://138.124.90.47:8789/justhost-site-front/bootstrap.sh | bash
# or copy this directory and: bash bootstrap.sh
set -euo pipefail

AEZA_IP="${AEZA_IP:-138.124.90.47}"
XRAY_PORT_INTERNAL="${XRAY_PORT_INTERNAL:-4443}"
WEB_PORT_INTERNAL="${WEB_PORT_INTERNAL:-8443}"
BASE_URL="${BASE_URL:-http://${AEZA_IP}:8789/justhost-site-front}"
INSTALL_DIR="${INSTALL_DIR:-/root/justhost-site-front}"
DOMAINS=(gdepar.ru neverretire.ru par.neverretire.ru snegirinegiri.ru)

echo "==> JustHost site-front bootstrap (origin ${AEZA_IP})"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx openssl curl ca-certificates

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
for f in nginx-stream-sni.conf nginx-sites-proxy.conf issue-certs.sh bootstrap.sh; do
  if [[ ! -s "$f" ]]; then
    curl -fsSL "${BASE_URL}/${f}" -o "$f"
  fi
done
chmod +x issue-certs.sh bootstrap.sh 2>/dev/null || true
SCRIPT_DIR="$INSTALL_DIR"

# --- stream module (Ubuntu: dynamic ngx_stream_module.so) ---
if ! nginx -V 2>&1 | grep -qE 'with-stream|stream_module' \
   && ! [[ -f /usr/lib/nginx/modules/ngx_stream_module.so || -f /usr/share/nginx/modules/ngx_stream_module.so ]]; then
  echo "ERROR: nginx without stream module"; exit 1
fi
# Enable dynamic stream module if packaged but not linked
if [[ -d /etc/nginx/modules-enabled ]] && [[ ! -e /etc/nginx/modules-enabled/50-mod-stream.conf ]]; then
  for cand in /usr/share/nginx/modules-available/mod-stream.conf \
              /etc/nginx/modules-available/mod-stream.conf; do
    if [[ -f "$cand" ]]; then
      ln -sfn "$cand" /etc/nginx/modules-enabled/50-mod-stream.conf
      break
    fi
  done
fi
if [[ ! -e /etc/nginx/modules-enabled/50-mod-stream.conf ]] && [[ -f /usr/share/nginx/modules/ngx_stream_module.so || -f /usr/lib/nginx/modules/ngx_stream_module.so ]]; then
  modpath=$(ls /usr/lib/nginx/modules/ngx_stream_module.so /usr/share/nginx/modules/ngx_stream_module.so 2>/dev/null | head -1)
  echo "load_module ${modpath};" > /etc/nginx/modules-enabled/50-mod-stream.conf
fi

# --- move xray/3x-ui inbound 443 → 127.0.0.1:4443 ---
move_xray_port() {
  local cfg=""
  for c in /usr/local/x-ui/bin/config.json /etc/x-ui/bin/config.json; do
    [[ -f "$c" ]] && cfg="$c" && break
  done
  if [[ -z "$cfg" ]]; then
    echo "WARN: xray config.json not found — ensure Reality listens on 127.0.0.1:${XRAY_PORT_INTERNAL}"
    return 0
  fi
  cp -a "$cfg" "${cfg}.bak.$(date +%s)"
  python3 - "$cfg" "$XRAY_PORT_INTERNAL" <<'PY'
import json, sys
path, port = sys.argv[1], int(sys.argv[2])
with open(path) as f:
    cfg = json.load(f)
changed = 0
for inbound in cfg.get("inbounds") or []:
    p = inbound.get("port")
    if p in (443, "443"):
        inbound["port"] = port
        inbound["listen"] = "127.0.0.1"
        changed += 1
        print(f"inbound {inbound.get('tag') or inbound.get('protocol')} 443 -> 127.0.0.1:{port}")
if not changed:
    print("WARN: no inbound on 443 found")
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
PY
  # 3x-ui DB port if present
  if command -v sqlite3 >/dev/null && [[ -f /etc/x-ui/x-ui.db ]]; then
    sqlite3 /etc/x-ui/x-ui.db "UPDATE inbounds SET port=${XRAY_PORT_INTERNAL} WHERE port=443;" || true
  fi
  systemctl restart x-ui 2>/dev/null || systemctl restart xray 2>/dev/null || true
  sleep 1
  ss -lntp | grep -E ":${XRAY_PORT_INTERNAL}\\b" || echo "WARN: nothing on ${XRAY_PORT_INTERNAL} yet"
}

move_xray_port

# --- certs: self-signed placeholders (replace with certbot after DNS) ---
mkdir -p /var/www/certbot /etc/empire-front/certs
for d in "${DOMAINS[@]}"; do
  dir="/etc/empire-front/certs/${d}"
  mkdir -p "$dir"
  if [[ ! -f "$dir/fullchain.pem" ]]; then
    openssl req -x509 -nodes -newkey rsa:2048 -days 14 \
      -keyout "$dir/privkey.pem" -out "$dir/fullchain.pem" \
      -subj "/CN=${d}" >/dev/null 2>&1
    echo "self-signed ${d}"
  fi
done

# --- install nginx configs ---
install -d /etc/nginx/stream.d
install -m 644 "${SCRIPT_DIR}/nginx-stream-sni.conf" /etc/nginx/stream.d/empire-sni.conf
install -m 644 "${SCRIPT_DIR}/nginx-sites-proxy.conf" /etc/nginx/sites-available/empire-front.conf
ln -sfn /etc/nginx/sites-available/empire-front.conf /etc/nginx/sites-enabled/empire-front.conf
rm -f /etc/nginx/sites-enabled/default

# Ensure stream include in nginx.conf
if ! grep -q 'stream\.d' /etc/nginx/nginx.conf; then
  if grep -q '^stream {' /etc/nginx/nginx.conf; then
    sed -i '/^stream {/a\    include /etc/nginx/stream.d/*.conf;' /etc/nginx/nginx.conf
  else
    cat >> /etc/nginx/nginx.conf <<'EOF'

stream {
    include /etc/nginx/stream.d/*.conf;
}
EOF
  fi
fi

# Patch AEZA IP if overridden
sed -i "s/138\\.124\\.90\\.47/${AEZA_IP}/g" /etc/nginx/sites-available/empire-front.conf

nginx -t
systemctl enable nginx
systemctl restart nginx

echo
echo "OK: public :443 = SNI split (sites|VLESS), sites → ${AEZA_IP}:80"
echo "Next: point DNS A records to this VPS IP, then:"
echo "  bash ${SCRIPT_DIR}/issue-certs.sh"
ss -lntp | grep -E ':(80|443|4443|8443)\\b' || ss -lntp | grep -E ':80|:443|:4443|:8443'
