#!/usr/bin/env bash
# Однократная настройка защиты от обнуления main.py и потери кода на VPS.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

chmod +x "$ROOT/scripts/guard_critical_files.sh" \
  "$ROOT/scripts/safe_push_to_vps.sh" \
  "$ROOT/scripts/vps_backup_to_yandex.sh" \
  "$ROOT/scripts/setup_empire_safety.sh" 2>/dev/null || true

echo "==> guard_critical_files (smoke)"
"$ROOT/scripts/guard_critical_files.sh"

echo "==> systemd: ExecStartPre guard + таймер автопроверки main.py"
for u in empire_main empire-vps-backup-yandex empire-main-py-guard; do
  install -D -m 644 "$ROOT/deploy/${u}.service" "/etc/systemd/system/${u}.service"
done
install -D -m 644 "$ROOT/deploy/empire-vps-backup-yandex.timer" /etc/systemd/system/empire-vps-backup-yandex.timer
install -D -m 644 "$ROOT/deploy/empire-main-py-guard.timer" /etc/systemd/system/empire-main-py-guard.timer
systemctl daemon-reload
systemctl enable empire-vps-backup-yandex.timer empire-main-py-guard.timer
systemctl start empire-vps-backup-yandex.timer empire-main-py-guard.timer 2>/dev/null || true

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
echo "  • guard: systemctl status empire-main-py-guard.timer"
echo "  • git:   cd $ROOT && git status"
echo ""
echo "С ПК НЕ используйте scp main.py — только:"
echo "  EMPIRE_VPS=root@moderate-amethys ./scripts/safe_push_to_vps.sh"
