"""CPA trial logic."""

from types import SimpleNamespace

from tools.cpa_trial import (
    CPA_CALL_MIN_BILLSEC,
    apply_call_credit,
    cpa_trial_eligible,
    phone_reveal_status,
    qualify_call,
)


def _spot(**kw):
    defaults = dict(
        phone="+79990001122",
        capacity_max=12,
        partner_tier="free",
        cpa_trial_calls_credited=0,
        cpa_deposit_balance=0,
        phone_blocked=0,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def test_trial_eligible_by_capacity():
    assert cpa_trial_eligible(_spot(capacity_max=10)) is True
    assert cpa_trial_eligible(_spot(capacity_max=4)) is False
    assert cpa_trial_eligible(_spot(capacity_max=4, partner_tier="cpa_top")) is True


def test_trial_three_calls_then_block():
    s = _spot()
    for _ in range(3):
        r = apply_call_credit(s, CPA_CALL_MIN_BILLSEC, disposition="ANSWERED")
        assert r["credited"] is True
        assert r["kind"] == "trial"
    assert s.phone_blocked == 1
    st = phone_reveal_status(s)
    assert st["allowed"] is False
    assert st["code"] == "trial_exhausted"


def test_short_billsec_not_credited():
    s = _spot()
    r = apply_call_credit(s, 40, disposition="ANSWERED")
    assert r["credited"] is False
    assert s.cpa_trial_calls_credited == 0


def test_ivr_duration_not_billsec():
    ok, reason = qualify_call(billsec=30, disposition="ANSWERED")
    assert ok is False
    assert reason == "too_short"


def test_not_answered_disposition():
    ok, reason = qualify_call(billsec=120, disposition="NO ANSWER")
    assert ok is False
    assert reason == "not_answered"


def test_deposit_balance_allows_reveal():
    s = _spot(phone_blocked=1, cpa_deposit_balance=2)
    st = phone_reveal_status(s)
    assert st["allowed"] is True
    assert st["code"] == "deposit"
