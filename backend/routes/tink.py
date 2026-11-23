"""Tink Open Banking integration — extracted from server.py.

Endpoints:
  POST /api/tink/link       — generate a Tink Link URL via delegated authorization
  POST /api/tink/callback   — exchange auth code for access token + import data
  POST /api/tink/refresh    — re-import accounts/transactions using stored token

Behavior is byte-identical to the original server.py implementation.
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from core import (
    audit_log,
    db,
    decrypt_sensitive,
    encrypt_sensitive,
    get_current_user,
    logger,
)

router = APIRouter()

TINK_BASE_URL = "https://api.tink.com"
TINK_CLIENT_ID = os.environ.get("TINK_CLIENT_ID")
TINK_CLIENT_SECRET = os.environ.get("TINK_CLIENT_SECRET")
TINK_DEFAULT_SCOPE = "accounts:read,balances:read,transactions:read,credentials:read,user:read"
TINK_SYNC_DELAY_SECONDS = 8
TINK_FETCH_RETRY_DELAY_SECONDS = 5


# ============== TINK API HELPERS ==============

async def _tink_get_client_token(scope: str) -> str:
    """Get a client access token from Tink."""
    async with httpx.AsyncClient() as c:
        resp = await c.post(f"{TINK_BASE_URL}/api/v1/oauth/token", data={
            "client_id": TINK_CLIENT_ID,
            "client_secret": TINK_CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": scope,
        })
    if resp.status_code != 200:
        logger.error(f"Tink client token error: {resp.status_code} {resp.text}")
        raise HTTPException(status_code=502, detail="Failed to authenticate with Tink")
    return resp.json()["access_token"]


async def _create_tink_user_remote(tink_external_id: str, token: str) -> httpx.Response:
    """POST to /api/v1/user/create with the given external id."""
    async with httpx.AsyncClient() as c:
        return await c.post(
            f"{TINK_BASE_URL}/api/v1/user/create",
            json={"external_user_id": tink_external_id, "market": "SE", "locale": "en_US"},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )


async def _tink_create_user(external_user_id: str) -> str:
    """Create a Tink user (or return existing). Returns tink_user_id.

    Tink remembers external_user_ids permanently — if we ever try to recreate
    one we already used, it returns 409. We use a versioned suffix to avoid
    collisions, with a single retry-on-409 fallback.
    """
    existing = await db.tink_users.find_one({"external_user_id": external_user_id}, {"_id": 0})
    if existing and existing.get("tink_user_id"):
        return existing["tink_user_id"]

    tink_external_id = (existing or {}).get("tink_external_id") or f"{external_user_id}-{uuid.uuid4().hex[:8]}"

    token = await _tink_get_client_token("user:create")
    resp = await _create_tink_user_remote(tink_external_id, token)

    # Retry once with a fresh suffix if the id is somehow already taken
    if resp.status_code == 409 or (resp.status_code in (400, 422) and "already_exists" in resp.text):
        tink_external_id = f"{external_user_id}-{uuid.uuid4().hex[:8]}"
        resp = await _create_tink_user_remote(tink_external_id, token)

    if resp.status_code not in (200, 201):
        logger.error(f"Tink create user error: {resp.status_code} {resp.text}")
        raise HTTPException(status_code=502, detail=f"Failed to create Tink user: {resp.text}")

    data = resp.json()
    tink_user_id = data.get("user_id", data.get("id", ""))

    await db.tink_users.update_one(
        {"external_user_id": external_user_id},
        {"$set": {
            "tink_user_id": tink_user_id,
            "tink_external_id": tink_external_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return tink_user_id


async def _tink_get_auth_code(tink_user_id: str, scope: str, id_hint: str) -> str:
    """Generate a delegated authorization code for Tink Link.

    Raises HTTPException(404, "tink_user_stale") when Tink no longer recognises
    the stored tink_user_id (sandbox purges users periodically).
    """
    token = await _tink_get_client_token("authorization:grant")
    async with httpx.AsyncClient() as c:
        resp = await c.post(
            f"{TINK_BASE_URL}/api/v1/oauth/authorization-grant/delegate",
            data={
                "user_id": tink_user_id,
                "id_hint": id_hint,
                "scope": scope,
                "actor_client_id": TINK_CLIENT_ID,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    if resp.status_code == 404 or "User ID does not exist" in resp.text:
        raise HTTPException(status_code=404, detail="tink_user_stale")
    if resp.status_code != 200:
        logger.error(f"Tink auth grant error: {resp.status_code} {resp.text}")
        raise HTTPException(status_code=502, detail=f"Failed to generate Tink authorization: {resp.text}")
    return resp.json()["code"]


async def _tink_get_auth_code_with_recovery(
    user_id: str, email: str, scope: str,
) -> str:
    """Wrap _tink_get_auth_code with one bounded retry that wipes a stale
    mapping and recreates the user."""
    tink_user_id = await _tink_create_user(user_id)
    try:
        return await _tink_get_auth_code(tink_user_id, scope, id_hint=email)
    except HTTPException as e:
        if e.status_code != 404 or e.detail != "tink_user_stale":
            raise
        logger.warning(f"Tink user {tink_user_id} is stale; recreating for {user_id}")
        await db.tink_users.delete_one({"external_user_id": user_id})
        try:
            tink_user_id = await _tink_create_user(user_id)
            return await _tink_get_auth_code(tink_user_id, scope, id_hint=email)
        except HTTPException as inner:
            if inner.status_code == 404 and inner.detail == "tink_user_stale":
                raise HTTPException(status_code=502, detail="Tink user recovery failed")
            raise


# ============== TINK PARSERS ==============

def _parse_tink_account(tacc: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a Tink account from v1 or v2 format into normalized doc."""
    if "balances" in tacc:
        booked = tacc.get("balances", {}).get("booked", {}).get("amount", {})
        val = booked.get("value", {})
        balance = float(val.get("unscaledValue", 0)) / (10 ** int(val.get("scale", 0))) if val.get("unscaledValue") else 0
    else:
        balance = tacc.get("balance", 0)
    return {
        "name": tacc.get("name", "Bank Account"),
        "institution": tacc.get("financialInstitutionId", tacc.get("bankId", "Tink Bank")),
        "type": tacc.get("type", "CHECKING").lower(),
        "balance": balance,
        "mask": (tacc.get("accountNumber", "") or "")[-4:] or "****",
        "tink_account_id": tacc.get("id"),
    }


def _parse_tink_transaction(ttxn: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a Tink transaction from v1 or v2 format into normalized doc."""
    if "descriptions" in ttxn:
        amt = ttxn.get("amount", {}).get("value", {})
        raw = float(amt.get("unscaledValue", 0)) / (10 ** int(amt.get("scale", 0))) if amt.get("unscaledValue") else 0
        desc = ttxn.get("descriptions", {}).get("display", ttxn.get("descriptions", {}).get("original", "Transaction"))
        date = ttxn.get("dates", {}).get("booked", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        cat = ttxn.get("categories", {}).get("pfm", {}).get("name", "Other")
        tink_acc_id = ttxn.get("accountId") or ttxn.get("account_id")
    else:
        raw = ttxn.get("amount", 0)
        desc = ttxn.get("description", "Transaction")
        date = ttxn.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        if isinstance(date, (int, float)):
            date = datetime.fromtimestamp(date / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        cat = ttxn.get("categoryType", ttxn.get("category", "Other"))
        tink_acc_id = ttxn.get("accountId") or ttxn.get("account_id") or ttxn.get("accountID")
    return {
        "raw_amount": raw, "description": desc, "date": date, "category": cat,
        "id": ttxn.get("id"), "tink_account_id": tink_acc_id,
    }


# ============== TINK FETCHERS ==============

async def _fetch_tink_accounts(token: str, retries: int = 3) -> List[Dict[str, Any]]:
    """Fetch accounts from Tink, trying v2 then v1, with retries."""
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(retries):
        async with httpx.AsyncClient() as c:
            resp = await c.get(f"{TINK_BASE_URL}/data/v2/accounts", headers=headers)
        if resp.status_code == 200:
            accs = resp.json().get("accounts", [])
            if accs:
                return accs
        async with httpx.AsyncClient() as c:
            v1 = await c.get(f"{TINK_BASE_URL}/api/v1/accounts/list", headers=headers)
        if v1.status_code == 200:
            accs = v1.json().get("accounts", [])
            if accs:
                return accs
        await asyncio.sleep(TINK_FETCH_RETRY_DELAY_SECONDS)
    return []


async def _fetch_tink_transactions(token: str, retries: int = 3) -> List[Dict[str, Any]]:
    """Fetch transactions from Tink, trying v2 then v1, with retries."""
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(retries):
        async with httpx.AsyncClient() as c:
            resp = await c.get(
                f"{TINK_BASE_URL}/data/v2/transactions",
                params={"pageSize": 100}, headers=headers,
            )
        if resp.status_code == 200:
            txns = resp.json().get("transactions", [])
            if txns:
                return txns
        async with httpx.AsyncClient() as c:
            v1 = await c.get(
                f"{TINK_BASE_URL}/api/v1/search",
                params={"limit": 100}, headers=headers,
            )
        if v1.status_code == 200:
            data = v1.json()
            txns = data.get("results", data.get("transactions", []))
            if txns:
                return txns
        await asyncio.sleep(TINK_FETCH_RETRY_DELAY_SECONDS)
    return []


# ============== IMPORT ==============

async def _import_tink_accounts(user_id: str, tink_accounts: List[Dict[str, Any]]) -> Dict[str, str]:
    """Upsert accounts, return {tink_account_id: internal_account_id} mapping."""
    tink_to_internal: Dict[str, str] = {}
    for tacc in tink_accounts:
        parsed = _parse_tink_account(tacc)
        internal_id = f"tink_{parsed['tink_account_id'] or uuid.uuid4().hex[:12]}"
        doc = {
            "account_id": internal_id,
            "user_id": user_id,
            **parsed,
            "is_connected": True, "source": "tink",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.bank_accounts.update_one(
            {"tink_account_id": parsed["tink_account_id"], "user_id": user_id},
            {"$set": doc}, upsert=True,
        )
        if parsed["tink_account_id"]:
            tink_to_internal[parsed["tink_account_id"]] = internal_id
    return tink_to_internal


async def _import_tink_transactions(
    user_id: str,
    tink_txns: List[Dict[str, Any]],
    tink_to_internal: Dict[str, str],
) -> int:
    """Upsert transactions linked to the right internal account_id. Returns count."""
    imported = 0
    for ttxn in tink_txns:
        parsed = _parse_tink_transaction(ttxn)
        is_expense = parsed["raw_amount"] < 0
        internal_acc_id = tink_to_internal.get(parsed.get("tink_account_id"))
        doc = {
            "transaction_id": f"tink_{parsed['id'] or uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "account_id": internal_acc_id,
            "tink_account_id": parsed.get("tink_account_id"),
            "amount": abs(parsed["raw_amount"]),
            "category": parsed["category"],
            "description": parsed["description"],
            "date": parsed["date"],
            "type": "expense" if is_expense else "income",
            "source": "tink", "tink_transaction_id": parsed["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.transactions.update_one(
            {"tink_transaction_id": parsed["id"], "user_id": user_id},
            {"$set": doc}, upsert=True,
        )
        imported += 1
    return imported


async def import_tink_data(user_id: str, token: str) -> Dict[str, Any]:
    """Fetch and store Tink accounts + transactions. Returns import counts."""
    await asyncio.sleep(TINK_SYNC_DELAY_SECONDS)
    tink_accounts = await _fetch_tink_accounts(token)
    tink_txns = await _fetch_tink_transactions(token)

    tink_to_internal = await _import_tink_accounts(user_id, tink_accounts)
    transactions_imported = await _import_tink_transactions(user_id, tink_txns, tink_to_internal)

    return {
        "accounts_imported": len(tink_accounts),
        "transactions_imported": transactions_imported,
        "syncing": not tink_accounts and not tink_txns,
    }


# ============== ROUTES ==============

@router.post("/tink/link")
async def create_tink_link(
    request: Request, current_user: dict = Depends(get_current_user),
) -> Dict[str, str]:
    """Generate a Tink Link URL using the delegated-authorization flow so the
    returned access token actually has accounts/balances/transactions scopes."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or missing JSON body")
    redirect_uri = body.get("redirect_uri")

    if not redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri required")
    if not TINK_CLIENT_ID or not TINK_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Tink not configured")

    auth_code = await _tink_get_auth_code_with_recovery(
        current_user["user_id"],
        current_user.get("email", "user"),
        TINK_DEFAULT_SCOPE,
    )

    params = {
        "client_id": TINK_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "market": "SE",
        "locale": "en_US",
        "authorization_code": auth_code,
        "scope": TINK_DEFAULT_SCOPE,
        "test": "true",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return {"url": f"https://link.tink.com/1.0/transactions/connect-accounts?{query}"}


async def _exchange_tink_code(code: str) -> str:
    """Exchange a Tink authorization code for a user access token."""
    async with httpx.AsyncClient() as c:
        token_resp = await c.post(
            f"{TINK_BASE_URL}/api/v1/oauth/token",
            data={
                "client_id": TINK_CLIENT_ID,
                "client_secret": TINK_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
            },
        )
    if token_resp.status_code != 200:
        logger.error(f"Tink token exchange error: {token_resp.status_code} {token_resp.text}")
        raise HTTPException(status_code=502, detail="Failed to exchange Tink authorization code")
    return token_resp.json()["access_token"]


@router.post("/tink/callback")
async def tink_callback(
    request: Request, current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Exchange Tink auth code for token, then import accounts + transactions."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or missing JSON body")
    code = body.get("code")
    credentials_id = body.get("credentials_id")

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")

    user_id = current_user["user_id"]
    user_access_token = await _exchange_tink_code(code)

    await db.tink_users.update_one(
        {"external_user_id": user_id},
        {"$set": {
            "access_token": encrypt_sensitive(user_access_token),
            "credentials_id": credentials_id,
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )

    result = await import_tink_data(user_id, user_access_token)
    await audit_log(user_id, "tink_bank_connected", {"accounts": result.get("accounts_imported", 0)})
    msg = (
        f"Connected! Imported {result['accounts_imported']} accounts and "
        f"{result['transactions_imported']} transactions."
        if not result["syncing"]
        else "Bank connected! Data is still syncing — click 'Refresh' in a few seconds."
    )
    return {**result, "message": msg}


@router.post("/tink/refresh")
async def tink_refresh_data(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Re-fetch accounts and transactions using stored Tink token."""
    user_id = current_user["user_id"]
    mapping: Optional[Dict[str, Any]] = await db.tink_users.find_one(
        {"external_user_id": user_id}, {"_id": 0},
    )
    if not mapping or not mapping.get("access_token"):
        raise HTTPException(status_code=400, detail="No Tink connection found. Connect a bank first.")

    result = await import_tink_data(user_id, decrypt_sensitive(mapping["access_token"]))
    return {
        **result,
        "message": (
            f"Refreshed: {result['accounts_imported']} accounts, "
            f"{result['transactions_imported']} transactions."
        ),
    }
