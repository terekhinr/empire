#!/usr/bin/env bash
# Однократная настройка защиты от обнуления main.py и потери кода на VPS.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

chmod +x "$ROOT/scripts/guard_critical_files.sh" \
  "$ROOT/scripts/safe_push_to_vps.sh" \
  "$ROOT/scripts/vps_backup_to_yandex.sh" 2>/dev/null || true

echo "==> guard_critical_files (smoke)"
"$ROOT/scripts/guard_critical_files.sh"

echo "==> systemd: ExecStartPre guard для empire_main"
install -D -m 644 "$ROOT/deploy/empire_main.service" /etc/systemd/system/empire_main.service
install -D -m 644 "$ROOT/deploy/empire-vps-backup-yandex.service" /etc/systemd/system/empire-vps-backup-yandex.service
install -D -m 644 "$ROOT/deploy/empire-vps-backup-yandex.timer" /etc/systemd/system/empire-vps-backup-yandex.timer
systemctl daemon-reload
systemctl enable empire-vps-backup-yandex.timer
systemctl start empire-vps-backup-yandex.timer 2>/dev/null || true

echo "==> git (локальная история на VPS, без секретов)"
if [[ ! -d "$ROOT/.git" ]]; then
  git -C "$ROOT" init -b main
fi
git -C "$ROOT" config --local commit.gpgsign false 2>/dev/null || true

HOOK="$ROOT/.git/hooks/pre-commit"
cat >"$HOOK" <<'HOOK'
#!/usr/bin/env bash
# Не коммитить пустой/обрезанный main.py
ROOT="$(git rev-parse --show-toplevel)"
if git diff --cached --name-only | grep -qx 'main.py'; then
  "$ROOT/scripts/guard_critical_files.sh" || {
    echo "pre-commit: main.py не прошёл guard — коммит отменён" >&2
    exit 1
  }
fi
exit 0
HOOK
chmod +x "$HOOK"

echo "==> deploy_empire_infra: guard перед unit-ами"
# deploy_empire_infra уже копирует units — достаточно обновить empire_main.service

echo ""
echo "Готово."
echo "  • guard: scripts/guard_critical_files.sh"
echo "  • с ПК:  EMPIRE_VPS=root@HOST ./scripts/safe_push_to_vps.sh"
echo "  • бэкап: systemctl status empire-vps-backup-yandex.timer"
echo "  • git:   cd $ROOT && git status"
