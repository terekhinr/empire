#!/bin/bash
# Run AFTER DNS A for domains point to this JustHost IP (grey cloud / no CF proxy).
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq certbot

mkdir -p /var/www/certbot /etc/empire-front/certs

issue_one() {
  local primary="$1"; shift
  local -a extras=("$@")
  local args=(-d "$primary")
  local e
  for e in "${extras[@]}"; do args+=(-d "$e"); done
  certbot certonly --webroot -w /var/www/certbot --agree-tos --register-unsafely-without-email \
    --non-interactive "${args[@]}" || return 1
  mkdir -p "/etc/empire-front/certs/${primary}"
  cp -L "/etc/letsencrypt/live/${primary}/fullchain.pem" "/etc/empire-front/certs/${primary}/fullchain.pem"
  cp -L "/etc/letsencrypt/live/${primary}/privkey.pem" "/etc/empire-front/certs/${primary}/privkey.pem"
  echo "issued ${primary}"
}

issue_one gdepar.ru www.gdepar.ru
issue_one neverretire.ru www.neverretire.ru
issue_one par.neverretire.ru
issue_one snegirinegiri.ru www.snegirinegiri.ru || echo "WARN: snegiri cert skipped"

nginx -t && systemctl reload nginx
echo "certs installed; HTTPS should be valid"
