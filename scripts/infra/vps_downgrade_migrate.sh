#!/usr/bin/env bash
# Перенос Empire VPS Aeza VIEs-3 → VIEs-2 (или любой новый хост) без dd-клона диска.
#
# Использование (с машины, у которой есть SSH на ОБА сервера — обычно Cursor/старый VPS):
#
#   export OLD_HOST=root@193.233.232.48
#   export NEW_HOST=root@NEW_IP
#   export OLD_SSH_KEY=~/.ssh/id_ed25519          # опционально
#   export NEW_SSH_KEY=~/.ssh/id_ed25519_new      # ключ нового VPS
#   bash scripts/infra/vps_downgrade_migrate.sh preflight
#   bash scripts/infra/vps_downgrade_migrate.sh sync
#   bash scripts/infra/vps_downgrade_migrate.sh activate   # на NEW: пакеты, systemd, nginx
#   bash scripts/infra/vps_downgrade_migrate.sh verify
#
# После verify вручную: DNS/Cloudflare → NEW_IP, Flint Amnezia+VLESS endpoint,
# подождать, удалить старый VPS.
#
# Не трогает: удаление старого сервера, смену DNS (осознанно вручную).
set -euo pipefail

OLD_HOST="${OLD_HOST:-root@193.233.232.48}"
NEW_HOST="${NEW_HOST:?NEW_HOST=root@NEW_IP required}"
OLD_SSH_KEY="${OLD_SSH_KEY:-}"
NEW_SSH_KEY="${NEW_SSH_KEY:-}"
RSYNC_EXCLUDES=(
  --exclude '.cache/'
  --exclude '**/__pycache__/'
  --exclude 'desktop/empire-tasks/node_modules/'
  --exclude 'desktop/empire-tasks/dist/'
  --exclude '.cursor-server/'
)

ssh_old() {
  local opts=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20)
  [[ -n "$OLD_SSH_KEY" ]] && opts+=(-i "$OLD_SSH_KEY")
  ssh "${opts[@]}" "$OLD_HOST" "$@"
}

ssh_new() {
  local opts=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20)
  [[ -n "$NEW_SSH_KEY" ]] && opts+=(-i "$NEW_SSH_KEY")
  ssh "${opts[@]}" "$NEW_HOST" "$@"
}

rsync_to_new() {
  local src="$1" dst="$2"
  local opts=(-aHAX --info=progress2 -e)
  local sshcmd="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20"
  [[ -n "$NEW_SSH_KEY" ]] && sshcmd="$sshcmd -i $NEW_SSH_KEY"
  # pull from OLD via this host acting as: rsync from old over ssh pipe is complex;
  # we rsync FROM old TO new by running rsync on controller with both remotes —
  # simplest: ssh old 'tar' | ssh new 'tar x'
  echo "==> $src → $NEW_HOST:$dst"
  ssh_old "tar czf - -C / $(printf '%q' "${src#/}")" | ssh_new "mkdir -p $(printf '%q' "$dst") && tar xzf - -C /"
}

cmd="${1:-}"

case "$cmd" in
  preflight)
    echo "==> OLD $OLD_HOST"
    ssh_old 'hostname; df -h / | tail -1; free -h | head -2; docker ps --format "{{.Names}}" 2>/dev/null; systemctl is-active nginx empire_webapp empire_gdepar 2>/dev/null || true'
    echo "==> NEW $NEW_HOST"
    ssh_new 'hostname; df -h / | tail -1; free -h | head -2; uname -a'
    used=$(ssh_old "df -BG / | awk 'NR==2{gsub(/G/,\"\",\$3); print \$3}'")
    avail=$(ssh_new "df -BG / | awk 'NR==2{gsub(/G/,\"\",\$4); print \$4}'")
    echo "OLD used≈${used}G  NEW avail≈${avail}G"
    if [[ "${used:-999}" -gt "${avail:-0}" ]]; then
      echo "FAIL: на новом мало места (нужно used+запас). Дочисти OLD или возьми диск больше."
      exit 1
    fi
    echo "OK preflight"
    ;;

  sync)
    echo "==> sync projects (rsync over SSH from OLD→NEW via controller stream)"
    # Prefer rsync daemon-less: run rsync ON new, pulling from old if new can reach old
    if ssh_new "true" && ssh_old "true"; then
      # NEW pulls from OLD (both must allow key auth; we inject OLD key to NEW temporarily optional)
      # Controller-side rsync with two remotes needs rsync 3.1+ ; use tar pipe for reliability:
      for path in \
        root/projects \
        etc/empire \
        etc/letsencrypt \
        etc/nginx \
        root/.config/rclone \
        root/.ssh \
        var/backups/empire \
        etc/empire/flint-ui.token \
        ; do
        echo "-- $path"
        ssh_old "test -e /$path" 2>/dev/null || { echo "skip missing /$path"; continue; }
        ssh_old "tar czf - -C / $path" | ssh_new "tar xzf - -C /"
      done
      # systemd units
      ssh_old 'tar czf - -C / etc/systemd/system/empire*.service etc/systemd/system/empire*.timer etc/systemd/system/*home-ops* etc/systemd/system/*healer* 2>/dev/null' \
        | ssh_new 'tar xzf - -C /' || true
      # docker amnezia volume (if any)
      ssh_old 'docker ps -a --format "{{.Names}}" | grep -i amnezia || true'
      vol=$(ssh_old 'docker inspect amnezia-awg2 --format "{{ range .Mounts }}{{ .Source }}{{ \"\\n\" }}{{ end }}" 2>/dev/null | head -1' || true)
      if [[ -n "${vol:-}" ]]; then
        echo "-- docker volume path $vol"
        ssh_old "tar czf - -C / ${vol#/}" | ssh_new "mkdir -p $(dirname "$vol") && tar xzf - -C /" || true
      fi
      # env dots
      ssh_old 'tar czf - -C /root .env .flint-admin.env .keenetic-admin.env .xkeen-reality.env 2>/dev/null' \
        | ssh_new 'tar xzf - -C /root' || true
      # copy empire .env from projects
      ssh_old 'test -f /root/projects/empire/.env && tar czf - -C /root/projects/empire .env' \
        | ssh_new 'tar xzf - -C /root/projects/empire' || true
    fi
    echo "OK sync (проверь activate)"
    ;;

  activate)
    echo "==> activate on NEW"
    ssh_new 'bash -s' <<'REMOTE'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git python3 python3-venv python3-pip nginx certbot python3-certbot-nginx \
  sqlite3 rclone curl tmux docker.io docker-compose-v2 jq 2>/dev/null \
  || apt-get install -y -qq git python3 python3-venv nginx certbot python3-certbot-nginx \
  sqlite3 rclone curl tmux docker.io jq

systemctl enable --now docker nginx || true

# venv — если скопирован целиком с OLD (linux aarch/x86 same) можно не пересобирать;
# безопаснее пересобрать на той же arch:
if [[ -d /root/projects/empire ]]; then
  cd /root/projects/empire
  if [[ ! -x venv/bin/python ]]; then
    python3 -m venv venv
  fi
  # лёгкая проверка: если pip сломан — reinstall
  ./venv/bin/pip install -q -U pip wheel || true
  if [[ -f requirements.txt ]]; then
    ./venv/bin/pip install -q -r requirements.txt || echo "WARN: pip install requirements failed — проверь вручную"
  fi
fi

systemctl daemon-reload
# включить известные юниты если файлы есть
for u in empire_webapp empire_gdepar empire_sales empire_main empire_worker \
  empire_dashboard empire_planning empire_ha_notify \
  empire-home-ops empire-flint2-bootstrap \
  empire-service-healer.timer empire-status-digest.timer empire-daily-audit.timer \
  empire-morning-brief.timer; do
  if systemctl cat "$u" &>/dev/null; then
    systemctl enable --now "$u" 2>/dev/null || systemctl restart "$u" 2>/dev/null || true
  fi
done

# postgres/mysql companion if any
docker start empire-db-1 2>/dev/null || true

nginx -t && systemctl reload nginx || true
# docker amnezia — если контейнер был, попробовать start
docker start amnezia-awg2 2>/dev/null || echo "Amnezia: подними вручную / через Amnezia app"

echo "NEW hostname=$(hostname) ip=$(hostname -I | awk '{print $1}')"
REMOTE
    echo "OK activate"
    ;;

  verify)
    echo "==> verify NEW"
    ssh_new 'bash -s' <<'REMOTE'
set -e
df -h / | tail -1
free -h | head -2
systemctl is-active nginx || true
curl -fsS -o /dev/null -w "webapp:%{http_code}\n" http://127.0.0.1:8000/api/health || echo "webapp:fail"
curl -fsS -o /dev/null -w "gdepar:%{http_code}\n" http://127.0.0.1:8001/api/gdepar/health || echo "gdepar:fail"
docker ps --format '{{.Names}} {{.Status}}' | head -10
test -d /root/projects/empire/data/snegiri && echo "snegiri:ok" || echo "snegiri:MISSING"
test -d /root/projects/kalitka && echo "kalitka:ok" || echo "kalitka:MISSING"
test -f /etc/empire/flint-ui.token && echo "flint-token:ok" || echo "flint-token:MISSING"
REMOTE
    echo
    echo "Дальше ВРУЧНУЮ:"
    echo "  1) Cloudflare A-записи neverretire.ru / gdepar.ru → IP нового"
    echo "  2) Flint: Amnezia Endpoint + VLESS Reality IP → новый"
    echo "  3) Tailscale на новом: tailscale up"
    echo "  4) Сутки проверки → удалить старый VPS в Aeza"
    ;;

  *)
    cat <<EOF
Usage:
  NEW_HOST=root@IP NEW_SSH_KEY=... [OLD_SSH_KEY=...] $0 preflight|sync|activate|verify

Шаги: preflight → sync → activate → verify → DNS/Flint → удалить OLD
Чеклист: docs/infra/VPS_DOWNGRADE_VIES2.md
EOF
    exit 1
    ;;
esac
