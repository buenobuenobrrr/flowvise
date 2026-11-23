"""Pure unit tests for portfolio rebalance math (no HTTP)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

BACKEND = Path(__file__).resolve().parents[1]
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "flowvise_unit")
os.environ.setdefault("JWT_SECRET", "unit-test-secret")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("COOKIE_SECURE", "false")

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import server as _server  # noqa: E402,F401 — boot fully before routes (avoids core circular import)
from routes.portfolio import (  # noqa: E402
    PORTFOLIO_TARGETS,
    build_rebalance_response,
    _detect_holdings_from_accounts,
)


def test_empty_holdings():
    result = build_rebalance_response({}, "moderate")
    assert result["total_value"] == 0
    assert result["needs_rebalance"] is False
    assert result["moves"] == []


def test_moderate_drift_needs_rebalance():
    holdings = {
        "stocks": 9000,
        "bonds": 500,
        "cash": 500,
        "real_estate": 0,
        "alternative": 0,
    }
    result = build_rebalance_response(holdings, "moderate")
    assert result["total_value"] == 10000
    assert result["risk_tolerance"] == "moderate"
    assert result["target_allocation"] == PORTFOLIO_TARGETS["moderate"]
    assert result["needs_rebalance"] is True
    assert any(m["asset_class"] == "bonds" and m["action"] == "buy" for m in result["moves"])


def test_invalid_risk_defaults_moderate():
    result = build_rebalance_response({"stocks": 100, "cash": 0}, "yolo")
    assert result["risk_tolerance"] == "moderate"


def test_detect_holdings_maps_account_types():
    accounts = [
        {"account_id": "1", "name": "Check", "type": "checking", "balance": 1000},
        {"account_id": "2", "name": "Save", "type": "savings", "balance": 2000},
        {"account_id": "3", "name": "Broker", "type": "investment", "balance": 5000},
        {"account_id": "4", "name": "Card", "type": "credit", "balance": 200},
    ]
    holdings, counted = _detect_holdings_from_accounts(accounts)
    assert holdings["cash"] == 3000
    assert holdings["stocks"] == 5000
    assert len(counted) == 3
