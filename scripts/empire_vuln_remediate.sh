#!/usr/bin/env bash
# Авто-устранение известных уязвимостей Python (pip-audit) + APT security.
# Без Telegram: результат в лог; утренний/вечерний digest подхватит итог аудита.
set -uo pipefail

ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
LOG_DIR="${EMPIRE_LOG_DIR:-/var/log/empire}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="${LOG_DIR}/vuln-remediate-${STAMP}.log"
PIP="${ROOT}/venv/bin/pip"
PIP_AUDIT="${ROOT}/venv/bin/pip-audit"
mkdir -p "$LOG_DIR"
exec >>"$LOG" 2>&1
ln -sf "$LOG" "${LOG_DIR}/vuln-remediate-latest.log"

log() { echo "[$(date -Iseconds)] $*"; }

log "=== vuln remediate ==="

if [[ -x "$PIP" ]]; then
  # Пакеты с известным фиксом (torch≥2.13 CPU — без CUDA на VPS)
  log "--- pip upgrade fixable ---"
  "$PIP" install -U \
    'click>=8.3.3' \
    'langchain-classic>=1.0.7' \
    'pillow>=12.3.0' \
    'setuptools>=83.0.0' \
    'pypdf>=5.1.0' \
    || log "WARN: pip upgrade partial fail"
  log "--- torch CPU >=2.13 (PYSEC-2025-194) ---"
  "$PIP" install -U --index-url https://download.pytorch.org/whl/cpu \
    'torch>=2.13.0' \
    || log "WARN: torch CPU upgrade failed"
  # PyPDF2 → pypdf (CVE + rename)
  if "$PIP" show PyPDF2 >/dev/null 2>&1; then
    "$PIP" uninstall -y PyPDF2 || true
  fi
else
  log "WARN: нет $PIP"
fi

if [[ -x "$PIP_AUDIT" ]]; then
  log "--- pip-audit after ---"
  set +e
  "$PIP_AUDIT" --progress-spinner off 2>&1 | tee "${LOG_DIR}/pip-audit-latest.txt"
  rc=${PIPESTATUS[0]}
  set -e
  log "pip-audit exit=$rc"
fi

# APT: сначала update (иначе 404 на устаревшие URI), затем unattended-upgrade
log "--- apt-get update ---"
apt-get update -qq 2>&1 | tail -15 || log "WARN: apt-get update failed"

if command -v unattended-upgrade >/dev/null 2>&1; then
  log "--- unattended-upgrade --dry-run ---"
  unattended-upgrade --dry-run 2>&1 | tail -20 || true
  if [[ "${EMPIRE_APT_AUTOFIX:-1}" == "1" ]]; then
    log "--- unattended-upgrade (security) ---"
    if ! unattended-upgrade 2>&1 | tee /dev/stderr | tail -40; then
      log "WARN: unattended-upgrade failed — fallback apt security upgrade"
      DEBIAN_FRONTEND=noninteractive apt-get -y \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        upgrade --with-new-pkgs 2>&1 | tail -40 || log "WARN: apt upgrade failed"
    fi
  fi
else
  log "INFO: unattended-upgrade не установлен — APT security через apt-get"
  if [[ "${EMPIRE_APT_AUTOFIX:-1}" == "1" ]]; then
    DEBIAN_FRONTEND=noninteractive apt-get -y \
      -o Dpkg::Options::="--force-confdef" \
      -o Dpkg::Options::="--force-confold" \
      upgrade --with-new-pkgs 2>&1 | tail -40 || log "WARN: apt upgrade failed"
  fi
fi

log "=== DONE ==="
echo "$LOG"
