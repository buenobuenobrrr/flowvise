"""Portfolio rebalancing routes — extracted from server.py.

Endpoints:
  POST /api/portfolio/rebalance       — manual € holdings → drift + suggested moves
  GET  /api/portfolio/auto-detect     — pull holdings from connected bank accounts

Behavior is byte-identical to the original server.py implementation.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request

from core import db, get_current_user

router = APIRouter()

# Target allocations by risk tolerance (stocks, bonds, cash, real_estate, alternative)
# All presets sum to 100. Keep values in `int` percentage points for easy drift math.
PORTFOLIO_TARGETS: Dict[str, Dict[str, int]] = {
    "conservative": {"stocks": 30, "bonds": 50, "cash": 15, "real_estate": 5, "alternative": 0},
    "moderate":     {"stocks": 60, "bonds": 25, "cash": 5,  "real_estate": 7, "alternative": 3},
    "aggressive":   {"stocks": 80, "bonds": 5,  "cash": 2,  "real_estate": 8, "alternative": 5},
}

# Heuristic mapping from bank account type -> asset class (used for auto-detect).
# Retirement/IRA accounts are mapped to `stocks` as a simplifying default — the
# long time-horizon of retirement capital makes this a reasonable starting point,
# but users with a bond-heavy IRA should treat it as a ceiling, not a prescription.
ACCOUNT_TYPE_TO_ASSET: Dict[str, Optional[str]] = {
    "checking": "cash", "current": "cash", "savings": "cash",
    "investment": "stocks", "brokerage": "stocks", "securities": "stocks",
    "retirement": "stocks", "ira": "stocks", "pension": "bonds",
    "loan": None, "credit": None,
}

# Drift thresholds
DRIFT_THRESHOLD_PCT = 5.0  # Trigger rebalance if any class drifts >= 5 ppt
# Moves smaller than this fraction of the portfolio are treated as noise and hidden
# from the UI so users aren't asked to move €2 on a €400 portfolio.
REBALANCE_NOISE_FRACTION = 0.005  # 0.5% of total


def _normalize_holdings(holdings: Dict[str, float]) -> Dict[str, float]:
    """Ensure every target asset class has a non-negative float entry."""
    return {
        k: max(0.0, float(holdings.get(k, 0) or 0))
        for k in PORTFOLIO_TARGETS["moderate"]  # canonical key set
    }


def _resolve_risk_tier(risk_tolerance: Optional[str]) -> str:
    """Coerce any input to a valid preset key; default to moderate."""
    risk = (risk_tolerance or "moderate").lower()
    return risk if risk in PORTFOLIO_TARGETS else "moderate"


def _empty_response(risk: str) -> Dict[str, Any]:
    target_pct = PORTFOLIO_TARGETS[risk]
    return {
        "total_value": 0.0,
        "risk_tolerance": risk,
        "current_allocation": {k: 0 for k in target_pct},
        "target_allocation": target_pct,
        "drift": {k: -target_pct[k] for k in target_pct},
        "moves": [],
        "needs_rebalance": False,
        "max_drift_pct": 0.0,
        "summary": "Add holdings to see rebalance recommendations.",
    }


def _compute_moves(
    holdings: Dict[str, float], total: float, target_pct: Dict[str, int],
    current_pct: Dict[str, float],
) -> list:
    """Produce a list of {asset_class, current_*, target_*, delta, action}, biggest first."""
    moves = []
    for k in target_pct:
        target_value = total * target_pct[k] / 100
        delta = round(target_value - holdings[k], 2)
        if abs(delta) >= total * REBALANCE_NOISE_FRACTION:
            moves.append({
                "asset_class": k,
                "current_value": round(holdings[k], 2),
                "current_pct": current_pct[k],
                "target_pct": target_pct[k],
                "target_value": round(target_value, 2),
                "delta": delta,
                "action": "buy" if delta > 0 else "sell",
            })
    moves.sort(key=lambda m: -abs(m["delta"]))
    return moves


def _build_summary(needs_rebalance: bool, drift: Dict[str, float]) -> str:
    if not needs_rebalance:
        return "Your portfolio is well-balanced. No rebalancing needed right now."
    worst = max(drift.items(), key=lambda kv: abs(kv[1]))
    direction = "overweight" if worst[1] > 0 else "underweight"
    return (
        f"Your portfolio drifted {abs(worst[1]):.1f}% — "
        f"{worst[0].replace('_', ' ')} is {direction}. Suggested moves below."
    )


def build_rebalance_response(
    holdings: Dict[str, float], risk_tolerance: str,
) -> Dict[str, Any]:
    """Compute current vs target allocation, drift, and recommended moves."""
    risk = _resolve_risk_tier(risk_tolerance)
    target_pct = PORTFOLIO_TARGETS[risk]
    holdings = _normalize_holdings(holdings)
    total = sum(holdings.values())

    if total <= 0:
        return _empty_response(risk)

    current_pct = {k: round(v / total * 100, 2) for k, v in holdings.items()}
    drift = {k: round(current_pct[k] - target_pct[k], 2) for k in target_pct}
    max_drift = max(abs(d) for d in drift.values())
    needs_rebalance = max_drift >= DRIFT_THRESHOLD_PCT

    return {
        "total_value": round(total, 2),
        "risk_tolerance": risk,
        "current_allocation": current_pct,
        "target_allocation": target_pct,
        "drift": drift,
        "moves": _compute_moves(holdings, total, target_pct, current_pct),
        "needs_rebalance": needs_rebalance,
        "max_drift_pct": round(max_drift, 2),
        "summary": _build_summary(needs_rebalance, drift),
    }


async def _user_risk_or(default: str, user_id: str) -> str:
    profile = await db.financial_profiles.find_one(
        {"user_id": user_id}, {"_id": 0, "risk_tolerance": 1}
    )
    return (profile or {}).get("risk_tolerance", default)


@router.post("/portfolio/rebalance")
async def portfolio_rebalance(
    request: Request, current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Compute rebalancing recommendations given user-supplied holdings (€ per class).
    Body: {holdings: {stocks, bonds, cash, real_estate, alternative}, risk_tolerance?}"""
    body = await request.json()
    holdings = body.get("holdings") or {}
    risk = body.get("risk_tolerance") or await _user_risk_or("moderate", current_user["user_id"])
    return build_rebalance_response(holdings, risk)


def _detect_holdings_from_accounts(accounts: list) -> tuple:
    """Map raw bank accounts → {asset_class: total_balance} + per-account audit list."""
    holdings = {"stocks": 0.0, "bonds": 0.0, "cash": 0.0, "real_estate": 0.0, "alternative": 0.0}
    counted = []
    for acc in accounts:
        asset = ACCOUNT_TYPE_TO_ASSET.get((acc.get("type") or "").lower())
        if not asset:
            continue
        bal = float(acc.get("balance", 0) or 0)
        if bal <= 0:
            continue
        holdings[asset] += bal
        counted.append({
            "account_id": acc.get("account_id"),
            "name": acc.get("name"),
            "type": acc.get("type"),
            "balance": bal,
            "asset_class": asset,
        })
    return holdings, counted


@router.get("/portfolio/auto-detect")
async def portfolio_auto_detect(
    current_user: dict = Depends(get_current_user),
    risk_tolerance: Optional[str] = None,
) -> Dict[str, Any]:
    """Auto-detect rough portfolio holdings from connected bank accounts.
    Optional ?risk_tolerance=conservative|moderate|aggressive overrides the saved profile.
    Returns the same shape as POST /portfolio/rebalance plus a `detected_holdings` map."""
    user_id = current_user["user_id"]
    accounts = await db.bank_accounts.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    holdings, counted = _detect_holdings_from_accounts(accounts)

    risk = risk_tolerance or await _user_risk_or("moderate", user_id)
    response = build_rebalance_response(holdings, risk)
    response["detected_holdings"] = {k: round(v, 2) for k, v in holdings.items()}
    response["counted_accounts"] = counted
    response["accounts_seen"] = len(accounts)
    response["accounts_used"] = len(counted)
    return response
