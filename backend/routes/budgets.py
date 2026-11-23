"""Budget alerts + recurring-transaction detection — extracted from server.py.

Endpoints:
  POST   /api/budgets                              — create a budget
  GET    /api/budgets                              — list budgets
  DELETE /api/budgets/{budget_id}                  — delete a budget
  GET    /api/budgets/alerts                       — current month threshold alerts
  GET    /api/budgets/smart-alerts                 — spending-spike + unusual-txn detection
  GET    /api/transactions/recurring               — auto-detect recurring patterns
  POST   /api/transactions/recurring/confirm       — confirm a pattern as subscription
  DELETE /api/transactions/recurring/{recurring_id} — dismiss/remove a recurring entry

Behavior is byte-identical to the original server.py implementation.
"""
import statistics
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core import db, get_current_user

router = APIRouter()

SPENDING_SPIKE_THRESHOLD = 1.25  # 25% increase triggers alert
UNUSUAL_TXN_STD_MULTIPLIER = 2  # transactions > mean + 2*std are flagged
RECURRING_MIN_TX = 4
RECURRING_MIN_GROUP = 2


# ============== MODELS ==============

class BudgetCreate(BaseModel):
    category: str
    limit: float
    period: str = "monthly"  # monthly, weekly


class BudgetUpdate(BaseModel):
    limit: Optional[float] = None
    period: Optional[str] = None


# ============== BUDGET CRUD ==============

@router.post("/budgets")
async def create_budget(
    budget: BudgetCreate, current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    budget_doc = {
        "budget_id": f"bud_{uuid.uuid4().hex[:12]}",
        "user_id": current_user["user_id"],
        "category": budget.category,
        "limit": budget.limit,
        "period": budget.period,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.budgets.insert_one({k: v for k, v in budget_doc.items()})
    return budget_doc


@router.get("/budgets")
async def get_budgets(current_user: dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return await db.budgets.find(
        {"user_id": current_user["user_id"]}, {"_id": 0},
    ).to_list(100)


@router.delete("/budgets/{budget_id}")
async def delete_budget(
    budget_id: str, current_user: dict = Depends(get_current_user),
) -> Dict[str, str]:
    result = await db.budgets.delete_one({
        "budget_id": budget_id, "user_id": current_user["user_id"],
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"message": "Budget deleted"}


# ============== BUDGET ALERTS ==============

def _classify_alert_status(pct: float) -> str:
    if pct >= 100:
        return "exceeded"
    if pct >= 80:
        return "warning"
    if pct >= 50:
        return "caution"
    return "safe"


@router.get("/budgets/alerts")
async def get_budget_alerts(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Generate threshold alerts for all budgets."""
    user_id = current_user["user_id"]
    budgets = await db.budgets.find({"user_id": user_id}, {"_id": 0}).to_list(100)

    now = datetime.now(timezone.utc)
    month_start = now.strftime("%Y-%m-01")
    transactions = await db.transactions.find(
        {"user_id": user_id, "type": "expense", "date": {"$gte": month_start}},
        {"_id": 0},
    ).to_list(1000)

    cat_spend: Dict[str, float] = {}
    for txn in transactions:
        cat = txn.get("category", "Other")
        cat_spend[cat] = cat_spend.get(cat, 0) + txn.get("amount", 0)

    alerts = []
    for b in budgets:
        spent = cat_spend.get(b["category"], 0)
        pct = (spent / b["limit"] * 100) if b["limit"] > 0 else 0
        alerts.append({
            "budget_id": b["budget_id"],
            "category": b["category"],
            "limit": b["limit"],
            "spent": round(spent, 2),
            "percentage": round(pct, 1),
            "remaining": round(max(0, b["limit"] - spent), 2),
            "status": _classify_alert_status(pct),
        })

    return {"alerts": alerts, "month": now.strftime("%Y-%m")}


# ============== SMART ALERTS ==============

def _detect_spending_spikes(monthly_cat: Dict[str, float]) -> List[Dict[str, Any]]:
    """Detect month-over-month spending spikes per category."""
    months = sorted({k.split("|")[0] for k in monthly_cat})
    if len(months) < 2:
        return []

    current_month, prev_month = months[-1], months[-2]
    cats = {k.split("|")[1] for k in monthly_cat}
    alerts = []
    for cat in cats:
        curr = monthly_cat.get(f"{current_month}|{cat}", 0)
        prev = monthly_cat.get(f"{prev_month}|{cat}", 0)
        if prev > 0 and curr > prev * SPENDING_SPIKE_THRESHOLD:
            pct_increase = ((curr - prev) / prev) * 100
            alerts.append({
                "type": "spending_spike",
                "category": cat,
                "current_amount": round(curr, 2),
                "previous_amount": round(prev, 2),
                "increase_pct": round(pct_increase, 1),
                "message": f"Your {cat} spending is {pct_increase:.0f}% higher than last month",
            })
    return alerts


def _detect_unusual_transactions(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flag recent transactions that exceed mean + 2*std."""
    amounts = [t.get("amount", 0) for t in transactions]
    if len(amounts) <= 5:
        return []

    avg = statistics.mean(amounts)
    std = statistics.stdev(amounts)
    threshold = avg + UNUSUAL_TXN_STD_MULTIPLIER * std
    recent_cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    alerts = []
    for txn in transactions:
        if txn.get("date", "") >= recent_cutoff and txn.get("amount", 0) > threshold:
            alerts.append({
                "type": "unusual_transaction",
                "category": txn.get("category", "Other"),
                "amount": txn.get("amount"),
                "description": txn.get("description"),
                "date": txn.get("date"),
                "message": (
                    f"Unusually large transaction: {txn.get('description')} "
                    f"for EUR {txn.get('amount'):.2f}"
                ),
            })
    return alerts


def _aggregate_monthly_category(transactions: List[Dict[str, Any]]) -> Dict[str, float]:
    """Group expense amounts by 'YYYY-MM|category' key for spike detection."""
    monthly_cat: Dict[str, float] = {}
    for txn in transactions:
        date = txn.get("date", "")
        if not date:
            continue
        key = f"{date[:7]}|{txn.get('category', 'Other')}"
        monthly_cat[key] = monthly_cat.get(key, 0) + txn.get("amount", 0)
    return monthly_cat


@router.get("/budgets/smart-alerts")
async def get_smart_alerts(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """AI-powered spending pattern alerts."""
    transactions = await db.transactions.find(
        {"user_id": current_user["user_id"], "type": "expense"}, {"_id": 0},
    ).to_list(1000)

    if len(transactions) < 3:
        return {"alerts": [], "message": "Need more transactions for smart alerts"}

    monthly_cat = _aggregate_monthly_category(transactions)
    alerts = _detect_spending_spikes(monthly_cat)
    alerts.extend(_detect_unusual_transactions(transactions))
    return {"alerts": alerts}


# ============== RECURRING TRANSACTION DETECTION ==============

def _group_transactions_by_pattern(
    transactions: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Group transactions by rounded amount + description + category."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for txn in transactions:
        amt = txn.get("amount", 0)
        desc = txn.get("description", "").lower().strip()
        cat = txn.get("category", "Other")
        rounded = round(amt * 2) / 2
        key = f"{rounded}|{desc[:20]}|{cat}"
        groups.setdefault(key, []).append(txn)
    return groups


def _detect_frequency(dates: List[datetime]) -> Optional[tuple]:
    """Analyze date intervals and return (frequency, avg_interval) or None."""
    if len(dates) < 2:
        return None
    dates.sort()
    intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    if not intervals:
        return None
    avg = statistics.mean(intervals)
    if 25 <= avg <= 35:
        return "monthly", avg
    if 5 <= avg <= 9:
        return "weekly", avg
    return None


def _parse_dates(group: List[Dict[str, Any]]) -> List[datetime]:
    """Extract and parse dates from a transaction group."""
    dates = []
    for txn in group:
        try:
            dates.append(datetime.strptime(txn["date"], "%Y-%m-%d"))
        except (ValueError, KeyError):
            continue
    return dates


async def _build_recurring_entry(
    group: List[Dict[str, Any]], user_id: str, frequency: str, avg_interval: float,
) -> Dict[str, Any]:
    """Convert a confirmed recurring group into a response entry."""
    amounts = [t.get("amount", 0) for t in group]
    latest = group[-1]
    avg_amount = round(statistics.mean(amounts), 2)

    existing = await db.recurring_transactions.find_one(
        {
            "user_id": user_id,
            "description": latest.get("description", ""),
            "amount": avg_amount,
        },
        {"_id": 0},
    )

    return {
        "pattern_id": f"pat_{uuid.uuid4().hex[:8]}",
        "description": latest.get("description", ""),
        "category": latest.get("category", "Other"),
        "average_amount": avg_amount,
        "frequency": frequency,
        "occurrences": len(group),
        "last_date": latest.get("date", ""),
        "avg_interval_days": round(avg_interval, 1),
        "confirmed": existing is not None,
        "confirmed_id": existing.get("recurring_id") if existing else None,
    }


@router.get("/transactions/recurring")
async def detect_recurring_transactions(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Auto-detect recurring transactions based on amount and date patterns."""
    user_id = current_user["user_id"]
    transactions = await db.transactions.find(
        {"user_id": user_id, "type": "expense"}, {"_id": 0},
    ).sort("date", 1).to_list(2000)

    if len(transactions) < RECURRING_MIN_TX:
        return {"recurring": [], "message": "Need more transactions to detect patterns"}

    recurring = []
    for group in _group_transactions_by_pattern(transactions).values():
        if len(group) < RECURRING_MIN_GROUP:
            continue
        result = _detect_frequency(_parse_dates(group))
        if not result:
            continue
        frequency, avg_interval = result
        recurring.append(await _build_recurring_entry(group, user_id, frequency, avg_interval))

    recurring.sort(key=lambda x: x["occurrences"], reverse=True)
    return {"recurring": recurring}


@router.post("/transactions/recurring/confirm")
async def confirm_recurring(
    request: Request, current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Confirm a detected pattern as a subscription/recurring expense."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or missing JSON body")
    doc = {
        "recurring_id": f"rec_{uuid.uuid4().hex[:12]}",
        "user_id": current_user["user_id"],
        "description": body.get("description", ""),
        "category": body.get("category", ""),
        "amount": body.get("amount", 0),
        "frequency": body.get("frequency", "monthly"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.recurring_transactions.insert_one({k: v for k, v in doc.items()})
    return doc


@router.delete("/transactions/recurring/{recurring_id}")
async def dismiss_recurring(
    recurring_id: str, current_user: dict = Depends(get_current_user),
) -> Dict[str, str]:
    result = await db.recurring_transactions.delete_one({
        "recurring_id": recurring_id, "user_id": current_user["user_id"],
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Dismissed"}
