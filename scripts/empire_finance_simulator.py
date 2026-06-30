#!/usr/bin/env python3
"""
Симулятор unit-экономики Empire (для проверки в другом ИИ или вручную).

  ./venv/bin/python scripts/empire_finance_simulator.py
  ./venv/bin/python scripts/empire_finance_simulator.py --cpl 900 --direct-budget 6000
  ./venv/bin/python scripts/empire_finance_simulator.py --voice-from 8 --voice-call-uplift 0.05
  ./venv/bin/python scripts/empire_finance_simulator.py --book-launch 50 --churn 0.12
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass
class Month:
    label: str
    pension: float
    gdepar: float
    expense: float

    @property
    def net(self) -> float:
        return self.pension + self.gdepar - self.expense


def simulate(
    *,
    book_launch_sales: int = 50,
    book_price: float = 299.0,
    book_net_pct: float = 0.88,
    pre_sales: int = 25,
    pre_price: float = 149.0,
    bridge_capital: float = 35_000.0,
    cpl: float = 400.0,
    direct_budget: float = 12000.0,
    cpa_price: float = 400.0,
    call_rate: float = 0.35,
    cpa_deposit_upfront: float = 0.6,
    stop_loss_cpl: float = 450.0,
    native_dec: float = 0.0,
    native_apr: float = 8000.0,
    premium_price: float = 2990.0,
    premium_start_month: int = 5,
    premium_new_per_month: float = 3.5,
    churn: float = 0.12,
    premium_target: int = 15,
    target_net: float = 100_000.0,
    voice_start_month: int = -1,
    voice_platform_monthly: float = 2500.0,
    voice_cost_per_billable: float = 15.0,
    voice_call_rate_uplift: float = 0.0,
) -> list[Month]:
    """Months 0..17 = Jun 26 .. Nov 27 (simplified)."""
    months: list[Month] = []
    cash = 0.0
    bridge_applied = False
    active_premium = 0.0
    total_premium_sold = 0.0

    labels = [
        "Июн 26", "Июл 26", "Авг 26", "Сен 26", "Окт 26", "Ноя 26",
        "Дек 26", "Янв 27", "Фев 27", "Мар 27", "Апр 27", "Май 27",
        "Июн 27", "Июл 27", "Авг 27", "Сен 27", "Окт 27", "Ноя 27",
    ]

    for i, label in enumerate(labels):
        pension = 0.0
        gdepar = 0.0
        expense = 5000.0

        if i == 2:
            pension += pre_sales * pre_price * book_net_pct
        if i == 3:
            pension += book_launch_sales * book_price * book_net_pct
            if not bridge_applied:
                cash += bridge_capital
                bridge_applied = True

        if i >= 4:
            pension += 3000.0 + min(max(i - 4, 0), 4) * 1000.0
        if i == 9:
            pension += native_apr
        if i >= 10:
            pension += 4000.0 + (i - 10) * 1500.0

        effective_cpl = cpl
        effective_budget = 0.0
        if 4 <= i <= 9:
            effective_budget = direct_budget
            if cpl > stop_loss_cpl:
                effective_budget = min(direct_budget, 6000.0)
                effective_cpl = max(cpl, stop_loss_cpl + 50)
            expense += effective_budget + (3000.0 if i >= 6 else 0.0)

        if i >= 4:
            leads = effective_budget / effective_cpl if effective_cpl else 0
            effective_call_rate = call_rate
            if voice_start_month >= 0 and i >= voice_start_month:
                effective_call_rate *= 1.0 + voice_call_rate_uplift
            billable = leads * effective_call_rate
            gdepar += billable * cpa_price * cpa_deposit_upfront
            if voice_start_month >= 0 and i >= voice_start_month:
                expense += voice_platform_monthly + billable * voice_cost_per_billable

        if i >= premium_start_month:
            if i == 4:
                pass
            else:
                active_premium = active_premium * (1 - churn) + premium_new_per_month
                total_premium_sold += premium_new_per_month
                gdepar += active_premium * premium_price

        if i == 3:
            expense = 5000.0

        m = Month(label, pension, gdepar, expense)
        months.append(m)
        cash += m.net

    return months


def main() -> int:
    p = argparse.ArgumentParser(description="Empire finance simulator")
    p.add_argument("--book-launch", type=int, default=50, help="PDF sales in Sep 26")
    p.add_argument("--cpl", type=float, default=400.0, help="Yandex Direct CPL ₽")
    p.add_argument("--direct-budget", type=float, default=12000.0)
    p.add_argument("--churn", type=float, default=0.12, help="Premium monthly churn 0..1")
    p.add_argument("--premium-new", type=float, default=3.5, help="New Premium sales/month from Feb")
    p.add_argument("--bridge", type=float, default=35000.0, help="Bridge capital R3")
    p.add_argument("--stop-loss-cpl", type=float, default=450.0)
    p.add_argument(
        "--voice-from",
        type=int,
        default=-1,
        help="Month index to enable voice bot (0=Jun26, 8=Feb27); -1=off",
    )
    p.add_argument("--voice-platform", type=float, default=2500.0, help="Voice platform ₽/mo")
    p.add_argument("--voice-per-call", type=float, default=15.0, help="Variable voice cost per billable call")
    p.add_argument(
        "--voice-call-uplift",
        type=float,
        default=0.0,
        help="Relative uplift to call_rate when voice on (e.g. 0.05 = +5%%)",
    )
    args = p.parse_args()

    months = simulate(
        book_launch_sales=args.book_launch,
        bridge_capital=args.bridge,
        cpl=args.cpl,
        direct_budget=args.direct_budget,
        churn=args.churn,
        premium_new_per_month=args.premium_new,
        stop_loss_cpl=args.stop_loss_cpl,
        voice_start_month=args.voice_from,
        voice_platform_monthly=args.voice_platform,
        voice_cost_per_billable=args.voice_per_call,
        voice_call_rate_uplift=args.voice_call_uplift,
    )

    print("=== Empire Finance Simulator (R3) ===")
    print(
        f"book_launch={args.book_launch}  bridge={args.bridge:.0f}  "
        f"cpl={args.cpl}  direct={args.direct_budget}  churn={args.churn:.0%}"
    )
    if args.voice_from >= 0:
        print(
            f"voice: from month[{args.voice_from}]  platform={args.voice_platform:.0f}  "
            f"per_call={args.voice_per_call}  call_uplift={args.voice_call_uplift:.0%}"
        )
    if args.cpl > args.stop_loss_cpl:
        print(f"⚠ CPL > stop-loss {args.stop_loss_cpl}: Direct budget capped to 6k (scenario B)")
    print()
    print(f"{'Месяц':<10} {'Пенсия':>8} {'ГдеПар':>8} {'Расход':>8} {'Net':>8} {'Σ':>10}")
    print("-" * 54)
    cum = 0.0
    hit = None
    for i, m in enumerate(months):
        if i == 3:
            cum += args.bridge
            print(f"{m.label:<10} {'— bridge':>8} {args.bridge:8.0f} {'':>8} {args.bridge:8.0f} {cum:10.0f}")
        cum += m.net
        flag = ""
        if m.net >= 100_000 and hit is None:
            hit = m.label
        print(f"{m.label:<10} {m.pension:8.0f} {m.gdepar:8.0f} {m.expense:8.0f} {m.net:8.0f} {cum:10.0f}")

    print()
    q4_net = sum(m.net for m in months[4:7])
    print(f"Q4 26 net (окт-дек): {q4_net:,.0f} ₽  {'⚠ разрыв' if q4_net < 0 else 'ok'}")
    print(f"Cash к ноя 27 (incl. bridge): {cum:,.0f} ₽")
    over = [m for m in months if m.net >= 100_000]
    if over:
        print(f"100k net/мес с: {over[0].label}")
    else:
        best = max(months, key=lambda x: x.net)
        print(f"100k не достигнут; лучший месяц {best.label}: net {best.net:,.0f} ₽")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
