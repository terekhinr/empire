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
sudo chmod 600 /etc/empire/dashboard.htpasswd
echo "OK: /etc/empire/dashboard.htpasswd (user $USER)"
