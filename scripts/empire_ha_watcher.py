#!/usr/bin/env python3
"""Empire HA Watcher/Healer — контроль Home Assistant с VPS (и через Flint).

Слои (как у большинства HA-пользователей + self-heal):
  1) Liveness: GET /api/  (или /api/config) с Bearer
  2) Readiness: system_health / critical entities
  3) Dead-man's switch: опциональный ping Healthchecks.io
  4) Heal: reload config entry / restart (через Flint LAN или SSH), с cooldown

ENV:
  HA_URL / HA_TOKEN          — основной API
  EMPIRE_HA_LAN_URL          — запасной через Flint (напр. http://192.168.1.41:8123
                               через reverse SSH LocalForward)
  EMPIRE_HA_SSH              — root@ha-host для ha core restart
  EMPIRE_HA_CRITICAL_ENTITIES— csv entity_id
  EMPIRE_HA_HC_PING_URL      — https://hc-ping.com/<uuid> (опц.)
  EMPIRE_HA_WATCH_DRY=1      — без фиксов
  EMPIRE_HA_WATCH_NO_FIX=1

Запуск:
  ./venv/bin/python scripts/empire_ha_watcher.py
  ./venv/bin/python scripts/empire_ha_watcher.py --check
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

LOG_DIR = Path(os.getenv("EMPIRE_LOG_DIR", "/var/log/empire"))
STATE_PATH = Path(
    os.getenv("EMPIRE_HA_WATCH_STATE", str(LOG_DIR / "ha-watcher-state.json"))
)
LOG_PATH = LOG_DIR / "ha-watcher.log"

MAX_RESTARTS_PER_HOUR = int(os.getenv("EMPIRE_HA_WATCH_MAX_RESTARTS", "2"))
DEFAULT_CRITICAL = (
    "binary_sensor.sonoff_snzb_06p",
    "binary_sensor.sonoff_snzb_06p_2",
    "binary_sensor.sonoff_snzb_06p_3",
    "light.empire_vannaya_svet",
    "light.tz3000_mgusv51k_ts0052",
    "light.tz3000_mgusv51k_ts0052_2",
    "light.empire_prihozhaya_svet",
    "sensor.srw_th01_balkon_balkon_tdeg_raw",
    "switch.kuhnya_chainik",
    "camera.ezviz_podezd",
    "binary_sensor.smartintercom_detektor_vyzova",
    "switch.smartintercom_otkryt_dver",
)

ENTITY_LABELS = {
    "binary_sensor.sonoff_snzb_06p": "Ванная · присутствие",
    "binary_sensor.sonoff_snzb_06p_2": "Прихожая · присутствие",
    "binary_sensor.sonoff_snzb_06p_3": "Туалет · присутствие",
    "light.empire_vannaya_svet": "Ванная · свет",
    "light.tz3000_mgusv51k_ts0052": "Ванная · диммер",
    "light.tz3000_mgusv51k_ts0052_2": "Прихожая · диммер TS0052",
    "light.empire_prihozhaya_svet": "Прихожая · свет",
    "sensor.srw_th01_balkon_balkon_tdeg_raw": "Балкон · SRW-TH01",
    "switch.kuhnya_chainik": "Кухня · розетка",
    "camera.ezviz_podezd": "Камера подъезд",
    "binary_sensor.smartintercom_detektor_vyzova": "Домофон · вызов",
    "switch.smartintercom_otkryt_dver": "Домофон · открыть",
}

# Эталон комнат — docs/HA_ROOM_CONTRACTS.md
ROOM_CONTRACTS: list[dict[str, Any]] = [
    {
        "id": "vannaya",
        "title": "Ванная",
        "presence": "binary_sensor.sonoff_snzb_06p",
        "light": "light.empire_vannaya_svet",
        "raw": "light.tz3000_mgusv51k_ts0052",
        "sens_entity": "select.sonoff_snzb_06p_chuvstvitelnost_obnaruzheniia",
        "sens_want": "Medium",
        "timeout_entity": "number.sonoff_snzb_06p_taim_aut_obnaruzheniia_prisutstviia",
        "timeout_want": 15,
        "desync_sec": 120,
    },
    {
        "id": "prihozhaya",
        "title": "Прихожая",
        "presence": "binary_sensor.sonoff_snzb_06p_2",
        "light": "light.empire_prihozhaya_svet",
        "raw": "light.tz3000_mgusv51k_ts0052_2",
        "sens_entity": "select.prikhozhaia_sonoff_snzb_06p_chuvstvitelnost_obnaruzheniia",
        "sens_want": "Low",
        "timeout_entity": "number.prikhozhaia_sonoff_snzb_06p_taim_aut_obnaruzheniia_prisutstviia",
        "timeout_want": 15,
        "desync_sec": 120,
    },
    {
        "id": "tualet",
        "title": "Туалет",
        "presence": "binary_sensor.sonoff_snzb_06p_3",
        "light": "light.empire_tualet_svet",
        "raw": "light.hobeian_zg_301z",
        "desync_sec": 120,
    },
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    fixed: bool = False
    skipped: bool = False


@dataclass
class Report:
    results: list[CheckResult] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except Exception:
        pass


def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_state() -> dict[str, Any]:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"restarts": {}}


def save_state(st: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def can_restart(st: dict[str, Any], key: str) -> bool:
    hist = st.setdefault("restarts", {}).setdefault(key, [])
    now = time.time()
    hist[:] = [t for t in hist if now - float(t) < 3600]
    return len(hist) < MAX_RESTARTS_PER_HOUR


def record_restart(st: dict[str, Any], key: str) -> None:
    hist = st.setdefault("restarts", {}).setdefault(key, [])
    hist.append(time.time())
    save_state(st)


def ha_urls() -> list[str]:
    _load_dotenv()
    urls: list[str] = []
    for key in ("HA_URL", "EMPIRE_HA_LAN_URL", "EMPIRE_HA_TUNNEL_URL"):
        v = (os.getenv(key) or "").strip().rstrip("/")
        if v and v not in urls:
            urls.append(v)
    # типичный LAN из Flint README, если ничего не задано
    if not urls:
        urls.append("http://127.0.0.1:18123")
    return urls


def ha_token() -> str:
    _load_dotenv()
    return (os.getenv("HA_TOKEN") or "").strip()


def http_ha(
    path: str,
    *,
    base: str,
    token: str,
    timeout: float = 12.0,
    method: str = "GET",
    json_body: dict | None = None,
) -> tuple[int, Any]:
    import httpx

    r = httpx.request(
        method,
        f"{base}{path}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=json_body,
        timeout=timeout,
    )
    try:
        body = r.json() if r.content else None
    except Exception:
        body = None
    return r.status_code, body


def _entity_state(base: str, token: str, entity_id: str) -> str | None:
    code, body = http_ha(f"/api/states/{entity_id}", base=base, token=token, timeout=10)
    if code != 200 or not isinstance(body, dict):
        return None
    return str(body.get("state") or "")


def _entity_payload(base: str, token: str, entity_id: str) -> dict[str, Any] | None:
    code, body = http_ha(f"/api/states/{entity_id}", base=base, token=token, timeout=10)
    if code != 200 or not isinstance(body, dict):
        return None
    return body


def check_room_contracts(*, dry: bool, no_fix: bool, st: dict[str, Any]) -> CheckResult:
    """Контракты комнат: дрейф Sonoff + desync presence/light. Без TG-спама."""
    del dry, no_fix  # report-only for now (heal = Flint/HA packages)
    token = ha_token()
    if not token:
        return CheckResult("room_contracts", True, "skip: нет HA_TOKEN", skipped=True)

    last_err = ""
    for base in ha_urls():
        try:
            issues: list[str] = []
            digest_rows: list[str] = []
            now = time.time()
            desync_track: dict[str, float] = st.setdefault("room_desync_since", {})

            for room in ROOM_CONTRACTS:
                title = str(room["title"])
                presence = str(room["presence"])
                light = str(room["light"])
                raw = str(room.get("raw") or "")

                p = _entity_payload(base, token, presence)
                lit = _entity_payload(base, token, light)
                raw_p = _entity_payload(base, token, raw) if raw else None
                p_st = (p or {}).get("state")
                lit_st = (lit or {}).get("state")
                raw_st = (raw_p or {}).get("state") if raw_p else None

                # drift: sensitivity / timeout
                sens_e = room.get("sens_entity")
                if sens_e and room.get("sens_want"):
                    sens = _entity_state(base, token, str(sens_e))
                    if sens and sens != room["sens_want"]:
                        issues.append(f"{title}: sens={sens} want={room['sens_want']}")

                to_e = room.get("timeout_entity")
                if to_e and room.get("timeout_want") is not None:
                    to_s = _entity_state(base, token, str(to_e))
                    try:
                        to_v = float(to_s) if to_s not in (None, "unavailable", "unknown") else None
                    except ValueError:
                        to_v = None
                    if to_v is not None and abs(to_v - float(room["timeout_want"])) > 0.5:
                        issues.append(f"{title}: timeout={to_v} want={room['timeout_want']}")

                # desync: empty room, light still on
                key = f"desync_{room['id']}"
                if p_st == "off" and lit_st == "on":
                    since = float(desync_track.get(key) or now)
                    desync_track[key] = since
                    age = now - since
                    if age >= float(room.get("desync_sec") or 120):
                        issues.append(f"{title}: desync presence=off light=on ≥{int(age)}с")
                else:
                    desync_track.pop(key, None)

                if p_st in ("unavailable", "unknown", None):
                    issues.append(f"{title}: presence {p_st or 'missing'}")
                if lit_st in ("unavailable", "unknown", None):
                    issues.append(f"{title}: light {lit_st or 'missing'}")
                if raw and raw_st in ("unavailable", "unknown", None):
                    issues.append(f"{title}: raw {raw_st or 'missing'}")

                digest_rows.append(
                    f"{title}: pir={p_st} light={lit_st}"
                    + (f" raw={raw_st}" if raw else "")
                )

            st["room_desync_since"] = desync_track
            st["room_contracts_digest"] = digest_rows
            st["room_contracts_issues"] = issues
            st["room_contracts_ts"] = datetime.now(timezone.utc).isoformat()
            save_state(st)

            if issues:
                return CheckResult(
                    "room_contracts",
                    False,
                    "; ".join(issues)[:240],
                )
            return CheckResult(
                "room_contracts",
                True,
                f"ok via {base} · " + " · ".join(digest_rows)[:200],
            )
        except Exception as exc:
            last_err = str(exc)[:120]
            continue
    return CheckResult("room_contracts", False, last_err or "no HA URL")


def fix_stuck_bathroom_light(*, dry: bool, no_fix: bool, st: dict[str, Any]) -> CheckResult:
    """Диагностика света ванной. НЕ гасим автоматически.

    Раньше healer тушил лампу при offline SNZB-06P и дрался с руками/Алисой.
    Гашение при мёртвом датчике — только HA failsafe (и только когда явно включён).
    """
    token = ha_token()
    if not token:
        return CheckResult("bath_light", True, "skip: нет HA_TOKEN", skipped=True)

    presence = "binary_sensor.sonoff_snzb_06p"
    lights = ("light.empire_vannaya_svet", "light.tz3000_mgusv51k_ts0052")
    last_err = ""
    for base in ha_urls():
        try:
            p_state = _entity_state(base, token, presence)
            lit_on = [
                lid
                for lid in lights
                if _entity_state(base, token, lid) == "on"
            ]
            detail = f"presence={p_state}; light_on={','.join(lit_on) or '-'}"
            if p_state in ("unavailable", "unknown", None) and lit_on:
                # report only — do not turn_off (fought Alice/manual)
                return CheckResult(
                    "bath_light",
                    False,
                    f"{detail}; sensor missing — no auto-off",
                )
            if p_state in ("unavailable", "unknown", None):
                return CheckResult(
                    "bath_light",
                    False,
                    f"{detail}; sensor missing",
                )
            return CheckResult(
                "bath_light",
                True,
                f"ok via {base} {detail}",
            )
        except Exception as exc:
            last_err = str(exc)[:120]
            continue
    return CheckResult("bath_light", False, last_err or "no HA URL")


def check_api(st: dict[str, Any], *, dry: bool, no_fix: bool) -> CheckResult:
    token = ha_token()
    if not token:
        return CheckResult("ha_api", True, "skip: нет HA_TOKEN", skipped=True)

    last_err = ""
    for base in ha_urls():
        try:
            code, body = http_ha("/api/", base=base, token=token)
            if code == 200:
                return CheckResult("ha_api", True, f"OK {base}")
            last_err = f"{base} HTTP {code}"
        except Exception as exc:
            last_err = f"{base} {exc}"[:140]

    # Tailscale с NEW часто недоступен — LAN через home-ops / Flint
    hop_ok, hop_detail = home_ops_ha_ok()
    if hop_ok is True:
        return CheckResult("ha_api", True, f"{last_err or 'api unreachable'}; fallback OK ({hop_detail})")

    if dry or no_fix:
        return CheckResult("ha_api", False, f"{last_err}; skip fix")

    if not can_restart(st, "ha_core"):
        return CheckResult("ha_api", False, f"{last_err}; лимит restart")

    # 1) попросить Flint home-ops / empire-ha-healer через reverse SSH
    fixed = False
    detail = last_err
    ssh_host = os.getenv("EMPIRE_HA_SSH", "").strip()
    if ssh_host:
        log(f"HA: restart via SSH {ssh_host}")
        subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=12",
                "-o",
                "StrictHostKeyChecking=accept-new",
                ssh_host,
                "ha core restart || systemctl restart home-assistant@homeassistant "
                "|| docker restart homeassistant || true",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        record_restart(st, "ha_core")
        time.sleep(10)
        for base in ha_urls():
            try:
                code, _ = http_ha("/api/", base=base, token=token, timeout=20)
                if code == 200:
                    return CheckResult("ha_api", True, f"{detail}; SSH restart → OK", fixed=True)
            except Exception:
                pass
        detail = f"{detail}; SSH restart tried"
        fixed = True

    # 2) через Flint reverse: дернуть local healer
    try:
        key = "/root/.ssh/id_ed25519"
        cmd = (
            "ssh -i {key} -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=no "
            "-p 6223 root@127.0.0.1 "
            "'/usr/sbin/empire-ha-healer --force 2>/dev/null | tail -5'"
        ).format(key=key)
        subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=90)
        record_restart(st, "ha_flint_healer")
        time.sleep(5)
        for base in ha_urls():
            try:
                code, _ = http_ha("/api/", base=base, token=token, timeout=15)
                if code == 200:
                    return CheckResult(
                        "ha_api", True, f"{detail}; flint healer → OK", fixed=True
                    )
            except Exception:
                pass
    except Exception as exc:
        detail = f"{detail}; flint healer: {exc}"[:160]

    # 3) home-ops fallback (LAN path)
    try:
        import httpx

        tok = ""
        tf = Path(os.getenv("EMPIRE_FLINT_UI_TOKEN", "/etc/empire/flint-ui.token"))
        if tf.is_file():
            tok = tf.read_text(encoding="utf-8").strip()
        api = os.getenv("EMPIRE_HOME_OPS_API", "http://127.0.0.1:8767/api").rstrip("/")
        if tok:
            r = httpx.get(
                api,
                params={"action": "status", "token": tok},
                timeout=15,
                headers={"Authorization": f"Bearer {tok}", "X-Empire-Token": tok},
            )
            body = r.json() if r.content else {}
            if isinstance(body, dict) and (body.get("checks") or {}).get("ha") is True:
                return CheckResult(
                    "ha_api",
                    True,
                    f"{detail}; home-ops checks.ha=true (LAN alive)",
                    fixed=fixed,
                )
    except Exception:
        pass

    return CheckResult("ha_api", False, detail, fixed=fixed)


def home_ops_ha_ok() -> tuple[bool | None, str]:
    """True/False если home-ops ответил; None если proxy недоступен."""
    try:
        import httpx

        tok = ""
        tf = Path(os.getenv("EMPIRE_FLINT_UI_TOKEN", "/etc/empire/flint-ui.token"))
        if tf.is_file():
            tok = tf.read_text(encoding="utf-8").strip()
        if not tok:
            return None, "no flint token"
        api = os.getenv("EMPIRE_HOME_OPS_API", "http://127.0.0.1:8767/api").rstrip("/")
        r = httpx.get(
            api,
            params={"action": "status", "token": tok},
            timeout=15,
            headers={"Authorization": f"Bearer {tok}", "X-Empire-Token": tok},
        )
        body = r.json() if r.content else {}
        if not isinstance(body, dict) or body.get("ok") is not True:
            return None, f"home-ops HTTP {r.status_code}"
        ha = (body.get("checks") or {}).get("ha")
        if ha is True:
            return True, "home-ops checks.ha=true"
        if ha is False:
            return False, "home-ops checks.ha=false"
        return None, "home-ops: no ha field"
    except Exception as exc:
        return None, str(exc)[:100]


def _tg_via_ha(base: str, token: str, message: str) -> None:
    """Алерт через HA rest_command (тот же канал, что у автоматик)."""
    try:
        http_ha(
            "/api/services/rest_command/empire_telegram",
            base=base,
            token=token,
            method="POST",
            json_body={"message": message[:3500]},
            timeout=15,
        )
    except Exception:
        pass


def check_critical_entities(*, dry: bool, no_fix: bool, st: dict[str, Any]) -> CheckResult:
    token = ha_token()
    if not token:
        return CheckResult("ha_entities", True, "skip: нет HA_TOKEN", skipped=True)

    raw = os.getenv("EMPIRE_HA_CRITICAL_ENTITIES", "").strip()
    if raw:
        entities = [x.strip() for x in raw.split(",") if x.strip()]
    else:
        entities = [x.strip() for x in DEFAULT_CRITICAL if str(x).strip()]
    if not entities:
        return CheckResult("ha_entities", True, "no critical entities", skipped=True)

    bad: list[str] = []
    base_ok = None
    probe_errors: list[str] = []
    for base in ha_urls():
        try:
            local_bad: list[str] = []
            for ent in entities:
                code, body = http_ha(f"/api/states/{ent}", base=base, token=token, timeout=10)
                if code == 404:
                    local_bad.append(f"{ent}=missing")
                    continue
                if code != 200 or not isinstance(body, dict):
                    local_bad.append(f"{ent}=HTTP{code}")
                    continue
                state = str(body.get("state") or "")
                if state in ("unavailable", "unknown"):
                    local_bad.append(f"{ent}={state}")
            bad = local_bad
            base_ok = base
            break
        except Exception as exc:
            probe_errors.append(f"{base}: {exc}"[:80])
            continue

    if base_ok is None and probe_errors:
        # Tailscale/proxy с NEW часто таймаутится — доверяем LAN через home-ops
        hop_ok, hop_detail = home_ops_ha_ok()
        if hop_ok is True:
            return CheckResult(
                "ha_entities",
                True,
                f"probe skip ({probe_errors[0]}); fallback OK ({hop_detail})",
                skipped=False,
            )
        detail = "; ".join(probe_errors[:3])
        if hop_ok is False:
            detail = f"{detail}; {hop_detail}"
        return CheckResult("ha_entities", False, detail)

    if not bad:
        if st.get("ha_offline"):
            st["ha_offline"] = []
            save_state(st)
        return CheckResult("ha_entities", True, f"ok via {base_ok} n={len(entities)}")

    # TG не шлём отсюда (спам) — только state для утро/вечер digest
    labeled = []
    for item in bad[:8]:
        eid = item.split("=", 1)[0]
        labeled.append(f"{ENTITY_LABELS.get(eid, eid)} ({item})")
    st["ha_offline"] = labeled
    save_state(st)

    detail = "; ".join(bad[:6])
    if dry or no_fix:
        return CheckResult("ha_entities", False, detail)

    # мягкий heal: reload config entries через Flint healer (не жжём core каждый раз)
    if can_restart(st, "ha_entities_reload"):
        log("HA entities: trigger flint healer --force")
        try:
            subprocess.run(
                "ssh -i /root/.ssh/id_ed25519 -o BatchMode=yes -o IdentitiesOnly=yes "
                "-o StrictHostKeyChecking=no -p 6223 root@127.0.0.1 "
                "'/usr/sbin/empire-ha-healer --force 2>/dev/null | tail -3'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=90,
            )
            record_restart(st, "ha_entities_reload")
            # если home-ops говорит HA жив — не держим красным после soft heal
            hop_ok, hop_detail = home_ops_ha_ok()
            if hop_ok is True:
                return CheckResult(
                    "ha_entities",
                    True,
                    f"{detail}; healer triggered; {hop_detail}",
                    fixed=True,
                )
            return CheckResult("ha_entities", False, f"{detail}; healer triggered", fixed=True)
        except Exception as exc:
            return CheckResult("ha_entities", False, f"{detail}; {exc}"[:140])
    return CheckResult("ha_entities", False, f"{detail}; cooldown")


def ping_healthchecks(ok: bool) -> CheckResult:
    url = (os.getenv("EMPIRE_HA_HC_PING_URL") or "").strip()
    if not url:
        return CheckResult("ha_hc_ping", True, "skip: нет EMPIRE_HA_HC_PING_URL", skipped=True)
    try:
        import httpx

        target = url if ok else url.rstrip("/") + "/fail"
        r = httpx.get(target, timeout=10)
        return CheckResult("ha_hc_ping", r.status_code < 400, f"HTTP {r.status_code} ok={ok}")
    except Exception as exc:
        return CheckResult("ha_hc_ping", False, str(exc)[:120])


def run_watch(*, dry: bool = False, no_fix: bool = False) -> Report:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    st = load_state()
    report = Report()
    log(f"START dry={int(dry)} no_fix={int(no_fix)}")

    api = check_api(st, dry=dry, no_fix=no_fix)
    report.results.append(api)
    if api.fixed:
        report.actions.append(f"ha_api: {api.detail}")
    if not api.ok and not api.skipped:
        report.problems.append(f"ha_api: {api.detail}")

    ents = check_critical_entities(dry=dry, no_fix=no_fix, st=st)
    report.results.append(ents)
    if ents.fixed:
        report.actions.append(f"ha_entities: {ents.detail}")
    if not ents.ok and not ents.skipped:
        report.problems.append(f"ha_entities: {ents.detail}")

    bath = fix_stuck_bathroom_light(dry=dry, no_fix=no_fix, st=st)
    report.results.append(bath)
    if bath.fixed:
        report.actions.append(f"bath_light: {bath.detail}")
    if not bath.ok and not bath.skipped:
        report.problems.append(f"bath_light: {bath.detail}")

    contracts = check_room_contracts(dry=dry, no_fix=no_fix, st=st)
    report.results.append(contracts)
    if not contracts.ok and not contracts.skipped:
        report.problems.append(f"room_contracts: {contracts.detail}")

    hc = ping_healthchecks(ok=report.ok)
    report.results.append(hc)
    if not hc.ok and not hc.skipped:
        report.problems.append(f"ha_hc_ping: {hc.detail}")

    log(f"DONE problems={len(report.problems)} actions={len(report.actions)}")
    return report


def format_report(report: Report) -> str:
    lines = [
        "🩺 Empire HA Watcher",
        f"UTC {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    for r in report.results:
        icon = "✅" if r.ok else ("⏭" if r.skipped else "❌")
        lines.append(f"{icon} {r.name}: {r.detail}")
    if report.problems:
        lines.append("")
        lines.append("── Проблемы ──")
        for p in report.problems:
            lines.append(f"❌ {p}")
    if report.actions:
        lines.append("")
        lines.append("── Действия ──")
        for a in report.actions:
            lines.append(f"🛠 {a}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Empire HA watcher/healer")
    ap.add_argument("--check", action="store_true", help="только проверка")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-fix", action="store_true")
    args = ap.parse_args(argv)
    dry = args.dry or args.check or os.getenv("EMPIRE_HA_WATCH_DRY", "").lower() in (
        "1",
        "true",
        "yes",
    )
    no_fix = args.no_fix or args.check or os.getenv("EMPIRE_HA_WATCH_NO_FIX", "").lower() in (
        "1",
        "true",
        "yes",
    )
    report = run_watch(dry=dry, no_fix=no_fix)
    print(format_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
