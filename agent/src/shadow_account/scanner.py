"""Shadow Account — today signals scanner.

Deterministic, data-free MVP: for each rule in a profile, pick up to N
symbols from the market's liquid basket that are "in phase" with the
rule's holding cadence on the target date. No external price fetches.

Future work: swap the phase test for a real feature check (e.g. the
rule's entry condition evaluated on the most recent bar).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from src.shadow_account.backtester import _LIQUID_BASKETS, SUPPORTED_MARKETS
from src.shadow_account.models import ShadowProfile, ShadowRule


def scan_today_signals(
    profile: ShadowProfile,
    *,
    target_date: str | date | None = None,
    per_market: int = 3,
) -> list[dict[str, Any]]:
    """Return a list of {symbol, market, rule_id, reason} matches.

    Args:
        profile: ShadowProfile holding the rules.
        target_date: ISO "YYYY-MM-DD" string, date object, or None (today).
        per_market: Cap per market bucket.

    Returns:
        Possibly-empty list of matched candidates. Always research-only —
        callers should surface the disclaimer from the skill.
    """
    if target_date is None:
        d = date.today()
    elif isinstance(target_date, date):
        d = target_date
    else:
        d = datetime.strptime(str(target_date), "%Y-%m-%d").date()

    matches: list[dict[str, Any]] = []
    for rule in profile.rules:
        market = rule.entry_condition.get("market", "other")
        if market not in SUPPORTED_MARKETS:
            continue
        basket = _LIQUID_BASKETS.get(market, [])
        if not _date_in_phase(d, rule):
            continue
        lo, hi = rule.holding_days_range
        reason = f"Within {rule.rule_id} entry window (hold {lo}-{hi}d)"
        for symbol in basket[:per_market]:
            matches.append({
                "symbol": symbol,
                "market": market,
                "rule_id": rule.rule_id,
                "reason": reason,
            })
    return matches


def _date_in_phase(target: date, rule: ShadowRule) -> bool:
    """True when `target`'s ordinal mod `2 * hold_median` is inside the entry band.

    This keeps the scanner deterministic and reviewable without needing
    real-time market data.
    """
    lo, hi = rule.holding_days_range
    hold = max(1, int((lo + hi) / 2))
    period = max(2, 2 * hold)
    phase = target.toordinal() % period
    return phase < hold
