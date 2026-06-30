"""CPA trial: 3 free calls (top only) → phone_blocked; deposit balance; billsec rule."""

from __future__ import annotations

CPA_CALL_MIN_BILLSEC = 90
CPA_TRIAL_FREE_CALLS = 3
CPA_TRIAL_MIN_CAPACITY = 8
CPA_MINI_DEPOSIT_RUB = 1500
CPA_MINI_PACK_CALLS = 3
CPA_STANDARD_DEPOSIT_RUB = 4000
CPA_STANDARD_PACK_CALLS = 10

_ANSWERED_DISPOSITIONS = frozenset(
    {"ANSWERED", "NORMAL_CLEARING", "answered", "normal_clearing"}
)


def cpa_trial_eligible(spot) -> bool:
    """Free 3-call trial only for larger venues."""
    tier = (getattr(spot, "partner_tier", None) or "free").lower()
    if tier in ("cpa_top", "premium"):
        return True
    cap = getattr(spot, "capacity_max", None)
    try:
        return cap is not None and int(cap) >= CPA_TRIAL_MIN_CAPACITY
    except (TypeError, ValueError):
        return False


def phone_blocked(spot) -> bool:
    return bool(getattr(spot, "phone_blocked", 0))


def deposit_balance(spot) -> int:
    try:
        return max(0, int(getattr(spot, "cpa_deposit_balance", 0) or 0))
    except (TypeError, ValueError):
        return 0


def trial_calls_credited(spot) -> int:
    try:
        return max(0, int(getattr(spot, "cpa_trial_calls_credited", 0) or 0))
    except (TypeError, ValueError):
        return 0


def phone_reveal_status(spot) -> dict:
    """Whether UI may reveal phone; separate from lead logging."""
    if not (getattr(spot, "phone", None) or "").strip():
        return {"allowed": False, "code": "no_phone", "message": "Телефон не указан"}

    bal = deposit_balance(spot)
    if bal > 0:
        return {"allowed": True, "code": "deposit", "deposit_balance": bal}

    if cpa_trial_eligible(spot):
        credited = trial_calls_credited(spot)
        if credited < CPA_TRIAL_FREE_CALLS:
            return {
                "allowed": True,
                "code": "trial",
                "trial_remaining": CPA_TRIAL_FREE_CALLS - credited,
            }
        if phone_blocked(spot):
            return {
                "allowed": False,
                "code": "trial_exhausted",
                "message": "Триал исчерпан. Пакет 10 звонков — 4 000 ₽.",
                "pay_url": "/partners#cpa",
            }

    if phone_blocked(spot):
        return {
            "allowed": False,
            "code": "blocked",
            "message": "Для этой бани нужен пакет звонков. От 1 500 ₽.",
            "pay_url": "/partners#cpa",
        }

    return {"allowed": True, "code": "free"}


def qualify_call(*, billsec: int, disposition: str | None) -> tuple[bool, str]:
    """billsec = разговор после ответа (не IVR hold). disposition from calltracking."""
    disp = (disposition or "ANSWERED").strip()
    if disp.upper() not in {d.upper() for d in _ANSWERED_DISPOSITIONS}:
        return False, "not_answered"
    if billsec < CPA_CALL_MIN_BILLSEC:
        return False, "too_short"
    return True, "ok"


def apply_call_credit(
    spot,
    billsec: int,
    *,
    disposition: str | None = "ANSWERED",
) -> dict:
    """After calltracking webhook; mutates spot in memory (caller commits)."""
    ok, reason = qualify_call(billsec=billsec, disposition=disposition)
    if not ok:
        return {
            "credited": False,
            "reason": reason,
            "min_billsec": CPA_CALL_MIN_BILLSEC,
            "billsec": billsec,
        }

    bal = deposit_balance(spot)
    if bal > 0:
        spot.cpa_deposit_balance = bal - 1
        if spot.cpa_deposit_balance <= 0:
            spot.phone_blocked = 1
        return {"credited": True, "kind": "deposit", "balance_left": spot.cpa_deposit_balance}

    if cpa_trial_eligible(spot):
        credited = trial_calls_credited(spot)
        if credited < CPA_TRIAL_FREE_CALLS:
            spot.cpa_trial_calls_credited = credited + 1
            if spot.cpa_trial_calls_credited >= CPA_TRIAL_FREE_CALLS:
                spot.phone_blocked = 1
            return {
                "credited": True,
                "kind": "trial",
                "trial_used": spot.cpa_trial_calls_credited,
                "phone_blocked": bool(spot.phone_blocked),
            }
        spot.phone_blocked = 1
        return {"credited": False, "reason": "trial_exhausted"}

    return {"credited": False, "reason": "not_on_cpa_program"}


# Back-compat alias
CPA_CALL_MIN_SECONDS = CPA_CALL_MIN_BILLSEC
