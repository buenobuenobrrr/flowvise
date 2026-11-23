"""GDPR data export & account deletion routes — extracted from server.py.

Endpoints:
  GET    /api/user/export    — return all user data as JSON (right-to-portability)
  DELETE /api/user/account   — permanently erase the account + all data

Behavior is byte-identical to the original server.py implementation.
"""
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from core import audit_log, db, get_current_user

router = APIRouter()


@router.get("/user/export")
async def export_user_data(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """GDPR: Export all user data as JSON."""
    user_id = current_user["user_id"]
    await audit_log(user_id, "data_export", {"type": "gdpr_full_export"})

    profile = await db.financial_profiles.find_one({"user_id": user_id}, {"_id": 0})
    transactions = await db.transactions.find({"user_id": user_id}, {"_id": 0}).to_list(10000)
    accounts = await db.bank_accounts.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    budgets = await db.budgets.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    advice_history = await db.advice_history.find({"user_id": user_id}, {"_id": 0}).to_list(500)
    recurring = await db.recurring_transactions.find({"user_id": user_id}, {"_id": 0}).to_list(100)

    # Sanitize user data (exclude password_hash)
    user_data = {k: v for k, v in current_user.items() if k != "password_hash"}

    return {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "user": user_data,
        "financial_profile": profile,
        "bank_accounts": accounts,
        "transactions": transactions,
        "budgets": budgets,
        "advice_history": advice_history,
        "recurring_transactions": recurring,
    }


# Collections to wipe on account deletion. Listed by `match key` so verification/
# reset codes (matched on email) and session-style collections (matched on user_id)
# can share the same routine without special-casing.
_DELETE_COLLECTIONS_BY_USER_ID = (
    "financial_profiles", "transactions", "bank_accounts", "budgets",
    "advice_history", "recurring_transactions", "user_sessions",
)
_DELETE_COLLECTIONS_BY_EMAIL = (
    "verification_codes", "reset_codes",
)


async def _purge_user_data(user_id: str, email: str) -> None:
    """Delete every record linked to this user across the known collections."""
    await db.users.delete_one({"user_id": user_id})
    for coll in _DELETE_COLLECTIONS_BY_USER_ID:
        await db[coll].delete_many({"user_id": user_id})
    for coll in _DELETE_COLLECTIONS_BY_EMAIL:
        await db[coll].delete_many({"email": email})


@router.delete("/user/account")
async def delete_user_account(
    request: Request, current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    """GDPR: Delete user account and all associated data."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or missing JSON body")
    if body.get("confirm") != "DELETE":
        raise HTTPException(
            status_code=400,
            detail='Send {"confirm": "DELETE"} to confirm account deletion.',
        )

    user_id = current_user["user_id"]
    email = current_user["email"]

    await audit_log(user_id, "account_deletion", {"email": email})
    await _purge_user_data(user_id, email)

    response = JSONResponse(content={"message": "Account and all data permanently deleted."})
    response.delete_cookie(key="session_token", path="/", secure=True, samesite="none")
    return response
