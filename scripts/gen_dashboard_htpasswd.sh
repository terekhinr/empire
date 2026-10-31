#!/usr/bin/env bash
# Создать /etc/empire/dashboard.htpasswd для nginx basic auth дашборда.
# Использование: sudo ./scripts/gen_dashboard_htpasswd.sh USER PASSWORD
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo "Usage: sudo $0 USER PASSWORD" >&2
  exit 1
fi
USER="$1"
PASS="$2"
sudo mkdir -p /etc/empire
if [[ ! -f /etc/empire/dashboard.htpasswd ]]; then
  sudo htpasswd -cb /etc/empire/dashboard.htpasswd "$USER" "$PASS"
else
  sudo htpasswd -b /etc/empire/dashboard.htpasswd "$USER" "$PASS"
fi
# nginx (www-data) должен читать htpasswd, но не листать /etc/empire с секретами.
sudo chgrp www-data /etc/empire /etc/empire/dashboard.htpasswd
sudo chmod 710 /etc/empire
sudo chmod 640 /etc/empire/dashboard.htpasswd
# nginx (www-data) читает только htpasswd; каталог 710, секреты *.env остаются 600.
echo "OK: /etc/empire/dashboard.htpasswd (user $USER)"
