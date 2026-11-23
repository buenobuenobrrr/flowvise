from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import time
from collections import defaultdict
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import bcrypt
import jwt
import statistics
import secrets
from cryptography.fernet import Fernet
import asyncio
import resend

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'financial-advisor-secret-key-2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 168  # 7 days

# Create the main app
app = FastAPI(title="FlowVise API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== SECURITY CONFIGURATION ==============

# Encryption key for sensitive data at rest (Tink tokens, etc.)
# In production, this MUST be stored in a secrets manager (AWS KMS, Vault)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    logger.warning("ENCRYPTION_KEY not set — using generated key. Set in .env for persistence!")
_fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

# Password policy
MIN_PASSWORD_LENGTH = 8
PASSWORD_REQUIREMENTS = {
    "min_length": 8,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digit": True,
    "require_special": True,
}

# Session security
SESSION_INACTIVE_TIMEOUT_MINUTES = 30
MAX_FAILED_LOGINS_LOCKOUT = 10
LOCKOUT_DURATION_MINUTES = 30


def encrypt_sensitive(value: str) -> str:
    """Encrypt a string value for storage at rest."""
    return _fernet.encrypt(value.encode()).decode()


def decrypt_sensitive(encrypted: str) -> str:
    """Decrypt a stored encrypted value."""
    try:
        return _fernet.decrypt(encrypted.encode()).decode()
    except Exception:
        return encrypted  # Return as-is if not encrypted (backward compat)


def validate_password_strength(password: str) -> str:
    """Validate password meets PSD2/OWASP requirements. Returns error message or empty string."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    if PASSWORD_REQUIREMENTS["require_uppercase"] and not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    if PASSWORD_REQUIREMENTS["require_lowercase"] and not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter"
    if PASSWORD_REQUIREMENTS["require_digit"] and not any(c.isdigit() for c in password):
        return "Password must contain at least one digit"
    if PASSWORD_REQUIREMENTS["require_special"] and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return "Password must contain at least one special character (!@#$%^&*...)"
    return ""


async def audit_log(user_id: str, action: str, details: Optional[Dict[str, Any]] = None, ip: str = "") -> None:
    """Write an immutable audit log entry."""
    entry = {
        "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "action": action,
        "details": details or {},
        "ip_address": ip,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await db.audit_logs.insert_one(entry)


# ============== EMAIL DISPATCH (RESEND) ==============

RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
else:
    logger.warning("RESEND_API_KEY not set — emails will be logged only (demo mode).")


def _verification_email_html(code: str, purpose: str) -> str:
    """Render a branded verification email."""
    title = "Verify your email" if purpose == "verify" else "Reset your password"
    intro = (
        "Welcome to FlowVise! Use the code below to verify your email address."
        if purpose == "verify"
        else "We received a request to reset your password. Use the code below to continue."
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0b0d10;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#e6e8eb;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0b0d10;padding:40px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#14171c;border:1px solid #232830;border-radius:14px;overflow:hidden;">
        <tr><td style="padding:32px 40px 8px;">
          <div style="font-size:13px;letter-spacing:2px;color:#7c8896;text-transform:uppercase;">FlowVise</div>
          <h1 style="margin:8px 0 0;font-size:22px;font-weight:600;color:#ffffff;">{title}</h1>
        </td></tr>
        <tr><td style="padding:16px 40px 8px;font-size:14px;line-height:1.6;color:#b3bcc7;">
          {intro}
        </td></tr>
        <tr><td align="center" style="padding:24px 40px;">
          <div style="display:inline-block;font-family:'SF Mono',Monaco,Consolas,monospace;font-size:34px;letter-spacing:10px;font-weight:600;color:#ffffff;background:#1a1f27;padding:18px 28px;border-radius:10px;border:1px solid #2a313b;">{code}</div>
        </td></tr>
        <tr><td style="padding:8px 40px 32px;font-size:12px;line-height:1.6;color:#7c8896;">
          This code expires in 10 minutes. If you didn't request this, you can safely ignore this email.
        </td></tr>
        <tr><td style="padding:16px 40px;border-top:1px solid #232830;font-size:11px;color:#5a6470;">
          FlowVise — your AI financial co-pilot. Educational tool only, not financial advice.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


async def send_verification_email(to_email: str, code: str, purpose: str = "verify") -> bool:
    """Dispatch a verification/reset email via Resend. Returns True on success, False on failure (logged)."""
    if not RESEND_API_KEY:
        logger.info(f"[EMAIL DEMO] {purpose} code for {to_email}: {code}")
        return False
    subject = "Your FlowVise verification code" if purpose == "verify" else "Reset your FlowVise password"
    params = {
        "from": f"FlowVise <{SENDER_EMAIL}>",
        "to": [to_email],
        "subject": subject,
        "html": _verification_email_html(code, purpose),
        "text": f"Your FlowVise {purpose} code is: {code}\n\nThis code expires in 10 minutes.",
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {to_email}: id={result.get('id') if isinstance(result, dict) else 'ok'}")
        return True
    except Exception as e:
        logger.error(f"Failed to send {purpose} email to {to_email}: {e}")
        return False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add OWASP-recommended security headers to all responses."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response


# Register security middleware (after class definition)
app.add_middleware(SecurityHeadersMiddleware)


# ============== RATE LIMITER ==============

class RateLimiter:
    """In-memory rate limiter tracking attempts per key (IP or email)."""

    def __init__(self):
        # key -> list of timestamps
        self._attempts: Dict[str, list] = defaultdict(list)

    def _cleanup(self, key: str, window: int):
        cutoff = time.time() - window
        self._attempts[key] = [t for t in self._attempts[key] if t > cutoff]

    def check(self, key: str, max_attempts: int, window: int):
        """Raise 429 if key exceeds max_attempts within window (seconds)."""
        self._cleanup(key, window)
        count = len(self._attempts[key])
        if count >= max_attempts:
            logger.warning(f"Rate limit hit: key={key}, attempts={count}/{max_attempts}")
            raise HTTPException(
                status_code=429,
                detail=f"Too many attempts. Please try again in {window // 60} minutes."
            )

    def record(self, key: str):
        self._attempts[key].append(time.time())


rate_limiter = RateLimiter()

# Rate limit settings
AUTH_RATE_WINDOW = 15 * 60  # 15 minutes
LOGIN_MAX_ATTEMPTS = 5
VERIFY_MAX_ATTEMPTS = 5
RESET_MAX_ATTEMPTS = 3


def _get_client_ip(request: Request) -> str:
    """Extract real client IP from proxy headers or connection."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"

# ============== MODELS ==============

class UserBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr
    name: str

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    user_id: str
    picture: Optional[str] = None
    created_at: datetime

class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    transaction_id: str = Field(default_factory=lambda: f"txn_{uuid.uuid4().hex[:12]}")
    user_id: str
    amount: float
    category: str
    description: str
    date: str
    type: str  # 'income' or 'expense'
    source: str = "manual"  # 'manual' or 'plaid'
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TransactionCreate(BaseModel):
    amount: float
    category: str
    description: str
    date: str
    type: str

class BankAccount(BaseModel):
    model_config = ConfigDict(extra="ignore")
    account_id: str = Field(default_factory=lambda: f"acc_{uuid.uuid4().hex[:12]}")
    user_id: str
    name: str
    institution: str
    type: str  # checking, savings, credit
    balance: float
    mask: str  # last 4 digits
    is_connected: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FinancialProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    profile_id: str = Field(default_factory=lambda: f"fp_{uuid.uuid4().hex[:12]}")
    user_id: str
    income: float = 0.0
    fixed_costs: float = 0.0
    safety_buffer: float = 500.0
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    subscriptions: Dict[str, float] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FinancialProfileUpdate(BaseModel):
    income: Optional[float] = None
    fixed_costs: Optional[float] = None
    safety_buffer: Optional[float] = None
    risk_tolerance: Optional[str] = None
    subscriptions: Optional[Dict[str, float]] = None

class AIAdviceRequest(BaseModel):
    question: Optional[str] = None
    context: Optional[str] = None

class Subscription(BaseModel):
    name: str
    amount: float
    category: str

# ============== HELPER FUNCTIONS ==============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def _extract_session_token(request: Request) -> str:
    """Extract session token from cookie or Authorization header."""
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


async def _validate_session(session_token: str) -> dict:
    """Check if token matches a stored Google OAuth session. Returns user or None."""
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session:
        return None
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_current_user(request: Request) -> dict:
    session_token = _extract_session_token(request)
    
    # Try stored session first (Google OAuth)
    user = await _validate_session(session_token)
    if user:
        return user
    
    # Fall back to JWT
    try:
        payload = decode_jwt_token(session_token)
        user = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def calculate_volatility_ratio(spending_amounts: List[float], safety_buffer: float) -> float:
    if len(spending_amounts) < 2 or safety_buffer == 0:
        return 0.0
    std_dev = statistics.stdev(spending_amounts)
    return round(std_dev / safety_buffer, 2)

def calculate_investment_readiness(
    income: float,
    average_spending: float,
    fixed_costs: float,
    safety_buffer: float,
    volatility_ratio: float
) -> dict:
    leftover = income - average_spending - fixed_costs
    safe_to_invest_raw = leftover - safety_buffer
    
    # Adjust for volatility
    volatility_penalty = volatility_ratio * 0.1 * safe_to_invest_raw
    safe_to_invest = max(0, safe_to_invest_raw - volatility_penalty)
    
    # Determine status (defaults for safety)
    status = "not_recommended"
    confidence = 0.4
    if safe_to_invest > income * 0.2:
        status = "excellent"
        confidence = 0.9
    elif safe_to_invest > income * 0.1:
        status = "good"
        confidence = 0.75
    elif safe_to_invest > 0:
        status = "moderate"
        confidence = 0.6
    else:
        status = "not_recommended"
        confidence = 0.4
    
    return {
        "leftover_after_expenses": round(leftover, 2),
        "safe_to_invest": round(safe_to_invest, 2),
        "status": status,
        "confidence_level": confidence,
        "volatility_impact": round(volatility_penalty, 2)
    }

def calculate_balance_readiness(total_balance: float, avg_spending: float,
                                subs_total: float, fixed_costs: float,
                                safety_buffer: float) -> dict:
    """Estimate investment readiness from bank balance when income is unknown."""
    three_months_expenses = (avg_spending + subs_total + fixed_costs) * 3
    available = total_balance - three_months_expenses - safety_buffer
    safe_to_invest = max(0, available)

    r_status = "not_recommended"
    r_confidence = 0.35

    if safe_to_invest > total_balance * 0.3:
        r_status, r_confidence = "good", 0.7
    elif safe_to_invest > 0:
        r_status, r_confidence = "moderate", 0.55

    return {
        "leftover_after_expenses": round(total_balance - three_months_expenses, 2),
        "safe_to_invest": round(safe_to_invest, 2),
        "status": r_status,
        "confidence_level": r_confidence,
        "volatility_impact": 0
    }


def aggregate_monthly_spending(transactions: list) -> dict:
    """Group expense transactions by YYYY-MM and return totals per month."""
    monthly = {}
    for txn in transactions:
        date = txn.get("date", "")
        if date:
            month = date[:7]
            monthly[month] = monthly.get(month, 0) + txn.get("amount", 0)
    return monthly


# ============== RISK ENGINE ==============

ESSENTIAL_CATEGORIES = {
    "Bills & Utilities", "Healthcare", "Transportation", "Education",
    "Rent", "Insurance", "Groceries"
}

RISK_AGGRESSION = {"conservative": 2.0, "moderate": 1.5, "aggressive": 0.8}
BASE_BUFFER_MONTHS = 3.0
COOLING_OFF_DAYS = 14
CONFIDENCE_DISPLAY_RATIO = 0.80


def calculate_svi(transactions: list) -> dict:
    """Spending Volatility Index = StdDev(variable expenses/month) / Mean(total expenses/month)."""
    if len(transactions) < 5:
        return {"svi": 0.0, "essential_monthly": 0, "variable_monthly": 0,
                "months_analyzed": 0, "variable_std": 0, "monthly_totals": {}}

    monthly_essential, monthly_variable, monthly_total = {}, {}, {}
    for txn in transactions:
        date = txn.get("date", "")
        if not date:
            continue
        month = date[:7]
        amount = txn.get("amount", 0)
        cat = txn.get("category", "Other")
        monthly_total[month] = monthly_total.get(month, 0) + amount
        if cat in ESSENTIAL_CATEGORIES:
            monthly_essential[month] = monthly_essential.get(month, 0) + amount
        else:
            monthly_variable[month] = monthly_variable.get(month, 0) + amount

    months = sorted(monthly_total.keys())
    if len(months) < 2:
        avg_e = statistics.mean(monthly_essential.values()) if monthly_essential else 0
        avg_v = statistics.mean(monthly_variable.values()) if monthly_variable else 0
        return {"svi": 0.0, "essential_monthly": round(avg_e, 2),
                "variable_monthly": round(avg_v, 2), "months_analyzed": len(months),
                "variable_std": 0, "monthly_totals": {m: round(monthly_total[m], 2) for m in months}}

    variable_amounts = [monthly_variable.get(m, 0) for m in months]
    total_amounts = [monthly_total.get(m, 0) for m in months]
    essential_amounts = [monthly_essential.get(m, 0) for m in months]

    avg_total = statistics.mean(total_amounts)
    var_std = statistics.stdev(variable_amounts) if len(variable_amounts) > 1 else 0
    svi = var_std / avg_total if avg_total > 0 else 0

    return {
        "svi": round(min(svi, 2.0), 3),
        "essential_monthly": round(statistics.mean(essential_amounts), 2),
        "variable_monthly": round(statistics.mean(variable_amounts), 2),
        "variable_std": round(var_std, 2),
        "months_analyzed": len(months),
        "monthly_totals": {m: round(monthly_total[m], 2) for m in months[-6:]},
    }


def calculate_elastic_buffer(essential: float, variable: float, svi: float, risk_tolerance: str) -> dict:
    """Buffer = (Essential + Variable) * (Base + SVI * Aggression) months."""
    aggression = RISK_AGGRESSION.get(risk_tolerance, 1.5)
    buffer_months = max(2.0, min(BASE_BUFFER_MONTHS + svi * aggression, 12.0))
    total_monthly = essential + variable
    return {
        "buffer_months": round(buffer_months, 1),
        "buffer_amount": round(total_monthly * buffer_months, 2),
        "base_months": BASE_BUFFER_MONTHS,
        "svi_adjustment": round(svi * aggression, 2),
    }


def detect_spending_spike(monthly_totals: dict) -> dict:
    """Detect 30%+ spending spike triggering a cooling-off freeze."""
    months = sorted(monthly_totals.keys())
    if len(months) < 3:
        return {"spike_detected": False, "cooling_off": False, "spike_pct": 0}
    recent = monthly_totals[months[-1]]
    prior = [monthly_totals[m] for m in months[-4:-1]] if len(months) >= 4 else [monthly_totals[m] for m in months[:-1]]
    avg_prior = statistics.mean(prior) if prior else 0
    if avg_prior == 0:
        return {"spike_detected": False, "cooling_off": False, "spike_pct": 0}
    spike_pct = ((recent - avg_prior) / avg_prior) * 100
    spike_detected = spike_pct > 30
    cooling_off = False
    if spike_detected:
        try:
            last_month = datetime.strptime(months[-1] + "-01", "%Y-%m-%d")
            days_since = (datetime.now(timezone.utc) - last_month.replace(tzinfo=timezone.utc)).days
            cooling_off = days_since < COOLING_OFF_DAYS + 30
        except ValueError:
            pass
    return {"spike_detected": spike_detected, "cooling_off": cooling_off,
            "spike_pct": round(spike_pct, 1), "recent_spend": round(recent, 2),
            "avg_prior_spend": round(avg_prior, 2)}


def calculate_smart_safe_to_invest(total_cash: float, elastic_buffer: float,
                                   earmarked_bills: float, spike_info: dict) -> dict:
    """Safe = Total Cash - Buffer - Bills. Display 80% (20% shadow buffer).
    Freeze if cooling-off active."""
    raw_safe = max(0, total_cash - elastic_buffer - earmarked_bills)
    if spike_info.get("cooling_off"):
        return {"raw_safe_to_invest": round(raw_safe, 2), "displayed_safe_to_invest": 0,
                "shadow_buffer_pct": CONFIDENCE_DISPLAY_RATIO, "frozen": True,
                "frozen_reason": f"Spending spike of {spike_info['spike_pct']}% detected — {COOLING_OFF_DAYS}-day cooling off."}
    displayed = raw_safe * CONFIDENCE_DISPLAY_RATIO
    return {"raw_safe_to_invest": round(raw_safe, 2), "displayed_safe_to_invest": round(displayed, 2),
            "shadow_buffer_pct": CONFIDENCE_DISPLAY_RATIO,
            "shadow_buffer_amount": round(raw_safe * (1 - CONFIDENCE_DISPLAY_RATIO), 2),
            "frozen": False, "frozen_reason": None}


async def _create_default_profile(user_id: str):
    """Create a default financial profile for a new user."""
    profile = {
        "profile_id": f"fp_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "income": 0.0,
        "fixed_costs": 0.0,
        "safety_buffer": 500.0,
        "risk_tolerance": "moderate",
        "subscriptions": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.financial_profiles.insert_one(profile)


async def _generate_verification_code(email: str, user_id: str) -> str:
    """Generate a 6-digit verification code, store it, dispatch email, and return it."""
    code = f"{secrets.randbelow(900000) + 100000}"
    await db.verification_codes.delete_many({"email": email})
    await db.verification_codes.insert_one({
        "email": email,
        "user_id": user_id,
        "code": code,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    await send_verification_email(email, code, purpose="verify")
    return code


async def _validate_timed_code(collection_name: str, email: str, code: str) -> dict:
    """Validate a timed code from the given collection. Returns the record or raises 400."""
    collection = db[collection_name]
    record = await collection.find_one({"email": email, "code": str(code)}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=400, detail=f"Invalid {'verification' if 'verification' in collection_name else 'reset'} code")
    expires = record.get("expires_at", "")
    if expires:
        exp_dt = datetime.fromisoformat(expires)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        if exp_dt < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Code expired. Please request a new one.")
    return record


def _set_session_cookie(response: JSONResponse, token: str) -> JSONResponse:
    """Set the httpOnly session cookie on a response."""
    response.set_cookie(
        key="session_token", value=token, httponly=True,
        secure=True, samesite="none", path="/", max_age=7 * 24 * 60 * 60
    )
    return response


async def _find_or_create_google_user(email: str, name: str, picture: str) -> str:
    """Find existing user or create a new one for Google OAuth. Returns user_id."""
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id, "email": email, "name": name,
            "picture": picture, "created_at": datetime.now(timezone.utc).isoformat()
        })
        await _create_default_profile(user_id)
    else:
        user_id = user["user_id"]
        await db.users.update_one(
            {"user_id": user_id}, {"$set": {"name": name, "picture": picture}}
        )
    return user_id


def _build_mock_accounts(user_id: str, institution_name: str) -> list:
    """Build mock bank accounts for Plaid demo."""
    return [
        {
            "account_id": f"acc_{uuid.uuid4().hex[:12]}",
            "user_id": user_id, "name": "Current Account",
            "institution": institution_name, "type": "checking",
            "balance": 5432.10, "mask": "1234", "is_connected": True,
            "source": "plaid",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "account_id": f"acc_{uuid.uuid4().hex[:12]}",
            "user_id": user_id, "name": "Savings Account",
            "institution": institution_name, "type": "savings",
            "balance": 12500.00, "mask": "5678", "is_connected": True,
            "source": "plaid",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]


MOCK_CATEGORIES = ["Food & Dining", "Shopping", "Transportation", "Entertainment", "Bills & Utilities"]


def _build_mock_transactions(user_id: str, account_ids: list = None, count: int = 10) -> list:
    """Build mock transactions for Plaid demo. Distributes them across the provided account_ids."""
    txns = []
    accs = account_ids or [None]
    for i in range(count):
        txns.append({
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "account_id": accs[i % len(accs)],
            "amount": round(20 + (i * 15) + (i % 3) * 25, 2),
            "category": MOCK_CATEGORIES[i % len(MOCK_CATEGORIES)],
            "description": f"Sample transaction {i + 1}",
            "date": (datetime.now(timezone.utc) - timedelta(days=i * 3)).strftime("%Y-%m-%d"),
            "type": "expense", "source": "plaid",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    return txns


def calculate_auto_income(income_transactions: list) -> dict:
    """Auto-detect monthly income from all positive bank inflows.
    Groups by month, averages, and identifies recurring sources."""
    if not income_transactions:
        return {"avg_monthly_income": 0, "months_analyzed": 0, "sources": [], "by_month": {}}

    monthly = {}
    source_totals = {}
    source_months = {}
    for txn in income_transactions:
        date = txn.get("date", "")
        if not date:
            continue
        month = date[:7]
        amount = txn.get("amount", 0)
        monthly[month] = monthly.get(month, 0) + amount
        desc = txn.get("description", "Unknown")
        source_totals[desc] = source_totals.get(desc, 0) + amount
        source_months.setdefault(desc, set()).add(month)

    months = sorted(monthly.keys())
    if not months:
        return {"avg_monthly_income": 0, "months_analyzed": 0, "sources": [], "by_month": {}}

    avg = statistics.mean(monthly.values())
    sources = []
    for desc, total in sorted(source_totals.items(), key=lambda x: -x[1]):
        month_count = len(source_months.get(desc, set()))
        sources.append({
            "description": desc,
            "total": round(total, 2),
            "monthly_avg": round(total / max(len(months), 1), 2),
            "months_seen": month_count,
            "recurring": month_count >= 2
        })

    return {
        "avg_monthly_income": round(avg, 2),
        "months_analyzed": len(months),
        "sources": sources[:15],
        "by_month": {m: round(monthly[m], 2) for m in months[-6:]},
    }


# ============== AUTH ENDPOINTS ==============

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Password strength validation (PSD2/OWASP requirement)
    pwd_error = validate_password_strength(user_data.password)
    if pwd_error:
        raise HTTPException(status_code=400, detail=pwd_error)

    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        if existing.get("email_verified"):
            raise HTTPException(status_code=400, detail="Email already registered")
        await db.users.delete_one({"email": user_data.email})
        await db.financial_profiles.delete_one({"user_id": existing["user_id"]})
        await db.verification_codes.delete_many({"email": user_data.email})
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user_doc = {
        "user_id": user_id, "email": user_data.email, "name": user_data.name,
        "password_hash": hash_password(user_data.password), "picture": None,
        "email_verified": False, "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    await _create_default_profile(user_id)
    code = await _generate_verification_code(user_data.email, user_id)
    await audit_log(user_id, "user_registered", {"email": user_data.email})
    
    return JSONResponse(content={
        "user_id": user_id, "email": user_data.email,
        "requires_verification": True,
        "message": "Verification code sent. Please check your email.",
        "demo_code": code
    })

@api_router.post("/auth/verify")
async def verify_email(request: Request):
    """Verify email with 6-digit code"""
    client_ip = _get_client_ip(request)
    body = await request.json()
    email = body.get("email")
    code = body.get("code")
    
    if not email or not code:
        raise HTTPException(status_code=400, detail="Email and code required")
    
    rate_key = f"verify:{client_ip}:{email}"
    rate_limiter.check(rate_key, VERIFY_MAX_ATTEMPTS, AUTH_RATE_WINDOW)
    rate_limiter.record(rate_key)
    
    record = await _validate_timed_code("verification_codes", email, code)
    
    await db.users.update_one({"user_id": record["user_id"]}, {"$set": {"email_verified": True}})
    await db.verification_codes.delete_many({"email": email})
    
    user = await db.users.find_one({"user_id": record["user_id"]}, {"_id": 0})
    token = create_jwt_token(user["user_id"], user["email"])
    
    response = JSONResponse(content={
        "access_token": token, "token_type": "bearer",
        "user": {"user_id": user["user_id"], "email": user["email"],
                 "name": user["name"], "picture": user.get("picture")}
    })
    return _set_session_cookie(response, token)

@api_router.post("/auth/resend-code")
async def resend_verification_code(request: Request):
    """Resend a verification code"""
    body = await request.json()
    email = body.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("email_verified"):
        raise HTTPException(status_code=400, detail="Email already verified")
    code = await _generate_verification_code(email, user["user_id"])
    return {"message": "New code sent", "demo_code": code}


@api_router.post("/auth/forgot-password")
async def forgot_password(request: Request):
    """Send a password reset code."""
    client_ip = _get_client_ip(request)
    body = await request.json()
    email = body.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    rate_key = f"forgot:{client_ip}"
    rate_limiter.check(rate_key, RESET_MAX_ATTEMPTS, AUTH_RATE_WINDOW)
    rate_limiter.record(rate_key)
    
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        return {"message": "If this email is registered, a reset code has been sent.", "demo_code": None}
    if not user.get("password_hash"):
        raise HTTPException(status_code=400, detail="This account uses Google login. Password reset is not available.")
    
    code = f"{secrets.randbelow(900000) + 100000}"
    await db.reset_codes.delete_many({"email": email})
    await db.reset_codes.insert_one({
        "email": email, "user_id": user["user_id"], "code": code,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    await send_verification_email(email, code, purpose="reset")
    return {"message": "If this email is registered, a reset code has been sent.", "demo_code": code}

@api_router.post("/auth/reset-password")
async def reset_password(request: Request):
    """Verify reset code and set new password."""
    client_ip = _get_client_ip(request)
    body = await request.json()
    email, code, new_password = body.get("email"), body.get("code"), body.get("new_password")
    
    if not email or not code or not new_password:
        raise HTTPException(status_code=400, detail="Email, code, and new password required")
    
    rate_key = f"reset:{client_ip}:{email}"
    rate_limiter.check(rate_key, VERIFY_MAX_ATTEMPTS, AUTH_RATE_WINDOW)
    rate_limiter.record(rate_key)
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    pwd_error = validate_password_strength(new_password)
    if pwd_error:
        raise HTTPException(status_code=400, detail=pwd_error)
    
    record = await _validate_timed_code("reset_codes", email, code)
    await db.users.update_one({"user_id": record["user_id"]}, {"$set": {"password_hash": hash_password(new_password)}})
    await db.reset_codes.delete_many({"email": email})
    await audit_log(record["user_id"], "password_reset", {"email": email}, client_ip)
    
    return {"message": "Password reset successful. You can now log in with your new password."}


@api_router.post("/auth/login")
async def login(user_data: UserLogin, request: Request):
    client_ip = _get_client_ip(request)
    rate_key = f"login:{client_ip}:{user_data.email}"
    rate_limiter.check(rate_key, LOGIN_MAX_ATTEMPTS, AUTH_RATE_WINDOW)
    rate_limiter.record(rate_key)

    user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if not user:
        await audit_log("unknown", "login_failed", {"email": user_data.email, "reason": "not_found"}, client_ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Account lockout check
    lockout = await db.account_lockouts.find_one({"email": user_data.email}, {"_id": 0})
    if lockout and lockout.get("locked_until"):
        locked_until = datetime.fromisoformat(lockout["locked_until"])
        if locked_until > datetime.now(timezone.utc):
            remaining = int((locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
            raise HTTPException(status_code=423, detail=f"Account locked. Try again in {remaining} minutes.")
        else:
            await db.account_lockouts.delete_one({"email": user_data.email})

    if not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Please login with Google")

    if not verify_password(user_data.password, user["password_hash"]):
        # Track failed attempts for lockout
        await db.account_lockouts.update_one(
            {"email": user_data.email},
            {"$inc": {"failed_attempts": 1}, "$set": {"last_attempt": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
        lockout_doc = await db.account_lockouts.find_one({"email": user_data.email}, {"_id": 0})
        if lockout_doc and lockout_doc.get("failed_attempts", 0) >= MAX_FAILED_LOGINS_LOCKOUT:
            locked_until = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)).isoformat()
            await db.account_lockouts.update_one(
                {"email": user_data.email},
                {"$set": {"locked_until": locked_until}}
            )
            await audit_log(user.get("user_id", ""), "account_locked", {"email": user_data.email}, client_ip)
            raise HTTPException(status_code=423, detail=f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes due to too many failed attempts.")

        await audit_log(user.get("user_id", ""), "login_failed", {"email": user_data.email, "reason": "wrong_password"}, client_ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Successful login — clear lockout
    await db.account_lockouts.delete_one({"email": user_data.email})

    # Check if email is verified
    if not user.get("email_verified", True):
        code = await _generate_verification_code(user_data.email, user["user_id"])
        return JSONResponse(status_code=403, content={
            "detail": "Email not verified", "requires_verification": True,
            "email": user_data.email, "demo_code": code
        })

    await audit_log(user["user_id"], "login_success", {"email": user_data.email}, client_ip)

    token = create_jwt_token(user["user_id"], user["email"])
    response = JSONResponse(content={
        "access_token": token, "token_type": "bearer",
        "user": {"user_id": user["user_id"], "email": user["email"],
                 "name": user["name"], "picture": user.get("picture")}
    })
    return _set_session_cookie(response, token)

@api_router.post("/auth/google/session")
async def process_google_session(request: Request):
    """Process Google OAuth session_id from Emergent Auth"""
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    async with httpx.AsyncClient() as http_client:
        resp = await http_client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    auth_data = resp.json()
    email, name, picture = auth_data["email"], auth_data["name"], auth_data.get("picture")
    session_token = auth_data["session_token"]
    
    user_id = await _find_or_create_google_user(email, name, picture)
    
    await db.user_sessions.insert_one({
        "user_id": user_id, "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    response = JSONResponse(content={
        "user": {"user_id": user_id, "email": email, "name": name, "picture": picture}
    })
    return _set_session_cookie(response, session_token)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        name=current_user["name"],
        picture=current_user.get("picture")
    )

@api_router.post("/auth/logout")
async def logout(request: Request):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie(
        key="session_token",
        path="/",
        secure=True,
        samesite="none"
    )
    return response

# ============== CUSTOM CATEGORIES ENDPOINTS ==============

DEFAULT_CATEGORIES = [
    "Food & Dining", "Shopping", "Transportation", "Entertainment",
    "Bills & Utilities", "Healthcare", "Personal Care", "Education", "Travel", "Other"
]


@api_router.get("/categories")
async def get_categories(current_user: dict = Depends(get_current_user)):
    """Get default + user custom categories."""
    doc = await db.custom_categories.find_one({"user_id": current_user["user_id"]}, {"_id": 0})
    custom = doc.get("categories", []) if doc else []
    return {"default": DEFAULT_CATEGORIES, "custom": custom, "all": DEFAULT_CATEGORIES + custom}


@api_router.post("/categories")
async def add_category(request: Request, current_user: dict = Depends(get_current_user)):
    """Add a custom category."""
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name required")
    if len(name) > 50:
        raise HTTPException(status_code=400, detail="Category name too long (max 50 chars)")

    doc = await db.custom_categories.find_one({"user_id": current_user["user_id"]}, {"_id": 0})
    existing = doc.get("categories", []) if doc else []

    # Check duplicates against defaults + custom
    all_lower = [c.lower() for c in DEFAULT_CATEGORIES + existing]
    if name.lower() in all_lower:
        raise HTTPException(status_code=400, detail="Category already exists")

    await db.custom_categories.update_one(
        {"user_id": current_user["user_id"]},
        {"$push": {"categories": name}},
        upsert=True
    )
    return {"message": "Category added", "name": name}


@api_router.delete("/categories/{name}")
async def delete_category(name: str, current_user: dict = Depends(get_current_user)):
    """Remove a custom category."""
    result = await db.custom_categories.update_one(
        {"user_id": current_user["user_id"]},
        {"$pull": {"categories": name}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category removed"}


# ============== TRANSACTION ENDPOINTS ==============

@api_router.post("/transactions", response_model=dict)
async def create_transaction(
    txn: TransactionCreate,
    current_user: dict = Depends(get_current_user)
):
    transaction = Transaction(
        user_id=current_user["user_id"],
        amount=txn.amount,
        category=txn.category,
        description=txn.description,
        date=txn.date,
        type=txn.type
    )
    
    doc = transaction.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.transactions.insert_one(doc)
    
    return {"transaction_id": transaction.transaction_id, "message": "Transaction created"}

@api_router.get("/transactions", response_model=List[dict])
async def get_transactions(
    current_user: dict = Depends(get_current_user),
    limit: int = 100
):
    transactions = await db.transactions.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("date", -1).to_list(limit)
    
    return transactions

@api_router.delete("/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    current_user: dict = Depends(get_current_user)
):
    result = await db.transactions.delete_one({
        "transaction_id": transaction_id,
        "user_id": current_user["user_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {"message": "Transaction deleted"}

# ============== TINK OPEN BANKING INTEGRATION ==============
# Routes extracted to routes/tink.py.

# ============== BANK ACCOUNT ENDPOINTS (Mock Plaid) ==============

@api_router.post("/plaid/link-token")
async def create_link_token(current_user: dict = Depends(get_current_user)):
    """Create a mock Plaid link token"""
    return {
        "link_token": f"link-sandbox-{uuid.uuid4().hex}",
        "expiration": (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
    }

@api_router.post("/plaid/exchange-token")
async def exchange_public_token(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Exchange public token and create mock bank accounts"""
    body = await request.json()
    institution_name = body.get("institution_name", "Demo Bank")
    user_id = current_user["user_id"]
    
    accounts = _build_mock_accounts(user_id, institution_name)
    for acc in accounts:
        await db.bank_accounts.insert_one({k: v for k, v in acc.items()})
    
    account_ids = [a["account_id"] for a in accounts]
    mock_transactions = _build_mock_transactions(user_id, account_ids=account_ids)
    if mock_transactions:
        await db.transactions.insert_many([{k: v for k, v in t.items()} for t in mock_transactions])
    
    return {"accounts": accounts, "transactions_imported": len(mock_transactions)}

async def _self_heal_empty_bank_state(user_id: str) -> Dict[str, Any]:
    """If user has 0 bank accounts, clear out any leftover transactions and reset
    the Tink connection state. Idempotent — safe to call on every /bank-accounts GET.

    Note: we PRESERVE the tink_users.tink_user_id mapping because Tink remembers
    external_user_ids permanently — recreating would 409. We only clear the
    access_token + credentials_id so the next /tink/link starts a fresh connect."""
    has_accounts = await db.bank_accounts.count_documents({"user_id": user_id})
    if has_accounts:
        return {"cleaned": False}
    txn_del = await db.transactions.delete_many({"user_id": user_id})
    tink_reset = await db.tink_users.update_one(
        {"external_user_id": user_id},
        {"$unset": {"access_token": "", "credentials_id": "", "connected_at": ""}}
    )
    if txn_del.deleted_count or tink_reset.modified_count:
        await audit_log(
            user_id, "self_heal_orphan_cleanup",
            {"transactions_removed": txn_del.deleted_count,
             "tink_connection_reset": tink_reset.modified_count}
        )
    return {"cleaned": True, "transactions_removed": txn_del.deleted_count,
            "tink_connection_reset": tink_reset.modified_count}


@api_router.get("/bank-accounts", response_model=List[dict])
async def get_bank_accounts(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    accounts = await db.bank_accounts.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    # Self-heal: if user has zero accounts, ensure no orphan transactions or
    # stale Tink mappings linger from a pre-cascade disconnect.
    if not accounts:
        await _self_heal_empty_bank_state(user_id)
    return accounts


async def _delete_account_transactions(user_id: str, account: Dict[str, Any]) -> int:
    """Delete all transactions linked to a bank account by either internal id or tink id."""
    or_clauses = [{"account_id": account["account_id"]}]
    if account.get("tink_account_id"):
        or_clauses.append({"tink_account_id": account["tink_account_id"]})
    res = await db.transactions.delete_many({"user_id": user_id, "$or": or_clauses})
    return res.deleted_count


async def _cleanup_orphans_for_source(user_id: str, source: str) -> int:
    """When the last account of a source is removed, wipe legacy orphan
    transactions (those with no account_id) of that source. Returns count removed."""
    remaining = await db.bank_accounts.count_documents({"user_id": user_id, "source": source})
    if remaining > 0:
        return 0
    res = await db.transactions.delete_many({
        "user_id": user_id, "source": source,
        "$or": [{"account_id": {"$exists": False}}, {"account_id": None}],
    })
    return res.deleted_count


async def _maybe_reset_tink_connection(user_id: str, source: str) -> None:
    """If the disconnected account was the user's last Tink one, $unset the
    connection fields while preserving the tink_user_id mapping (Tink remembers
    external_user_id permanently — re-creating would 409 on the next /tink/link)."""
    if source != "tink":
        return
    remaining_tink = await db.bank_accounts.count_documents({"user_id": user_id, "source": "tink"})
    if remaining_tink == 0:
        await db.tink_users.update_one(
            {"external_user_id": user_id},
            {"$unset": {"access_token": "", "credentials_id": "", "connected_at": ""}}
        )


@api_router.delete("/bank-accounts/{account_id}")
async def disconnect_bank_account(
    account_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]

    account = await db.bank_accounts.find_one(
        {"account_id": account_id, "user_id": user_id},
        {"_id": 0}
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    await db.bank_accounts.delete_one({"account_id": account_id, "user_id": user_id})

    # Remove this account's transactions, then any remaining orphans of this source.
    src = account.get("source", "plaid")
    direct_removed = await _delete_account_transactions(user_id, account)
    orphan_removed = await _cleanup_orphans_for_source(user_id, src)
    txn_result_count = direct_removed + orphan_removed

    await _maybe_reset_tink_connection(user_id, src)

    await audit_log(
        user_id, "bank_account_disconnected",
        {"account_id": account_id, "source": account.get("source"),
         "transactions_removed": txn_result_count},
    )

    return {
        "message": "Account disconnected",
        "transactions_removed": txn_result_count,
    }

# ============== FINANCIAL PROFILE ENDPOINTS ==============

@api_router.get("/financial-profile", response_model=dict)
async def get_financial_profile(current_user: dict = Depends(get_current_user)):
    profile = await db.financial_profiles.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not profile:
        # Create default profile
        profile = {
            "profile_id": f"fp_{uuid.uuid4().hex[:12]}",
            "user_id": current_user["user_id"],
            "income": 0.0,
            "fixed_costs": 0.0,
            "safety_buffer": 500.0,
            "risk_tolerance": "moderate",
            "subscriptions": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.financial_profiles.insert_one(profile)
    
    return profile

@api_router.put("/financial-profile", response_model=dict)
async def update_financial_profile(
    updates: FinancialProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.financial_profiles.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": update_data}
    )
    
    profile = await db.financial_profiles.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    return profile

@api_router.put("/subscriptions")
async def update_subscriptions(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    body = await request.json()
    subscriptions = body.get("subscriptions", {})
    
    await db.financial_profiles.update_one(
        {"user_id": current_user["user_id"]},
        {
            "$set": {
                "subscriptions": subscriptions,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Subscriptions updated"}

# ============== FINANCIAL ANALYSIS ENDPOINTS ==============

@api_router.get("/analysis/spending-summary")
async def get_spending_summary(current_user: dict = Depends(get_current_user)):
    """Get spending summary with categories"""
    # Self-heal stale data if user has no connected accounts
    await _self_heal_empty_bank_state(current_user["user_id"])

    transactions = await db.transactions.find(
        {"user_id": current_user["user_id"], "type": "expense"},
        {"_id": 0}
    ).to_list(1000)
    
    # Group by category
    category_totals = {}
    monthly_spending = {}
    
    for txn in transactions:
        cat = txn.get("category", "Other")
        amount = txn.get("amount", 0)
        date = txn.get("date", "")
        
        category_totals[cat] = category_totals.get(cat, 0) + amount
        
        if date:
            month = date[:7]  # YYYY-MM
            monthly_spending[month] = monthly_spending.get(month, 0) + amount
    
    # Calculate statistics
    spending_amounts = list(monthly_spending.values()) if monthly_spending else [0]
    avg_spending = statistics.mean(spending_amounts) if spending_amounts else 0
    std_dev = statistics.stdev(spending_amounts) if len(spending_amounts) > 1 else 0
    
    return {
        "by_category": category_totals,
        "by_month": monthly_spending,
        "total_spending": sum(category_totals.values()),
        "average_monthly_spending": round(avg_spending, 2),
        "spending_std_deviation": round(std_dev, 2),
        "transaction_count": len(transactions)
    }

@api_router.get("/analysis/income-breakdown")
async def get_income_breakdown(current_user: dict = Depends(get_current_user)):
    """Get auto-detected income from bank inflows + manual primary income."""
    profile = await db.financial_profiles.find_one(
        {"user_id": current_user["user_id"]}, {"_id": 0}
    )
    primary_income = (profile or {}).get("primary_income", 0)

    income_txns = await db.transactions.find(
        {"user_id": current_user["user_id"], "type": "income"}, {"_id": 0}
    ).to_list(2000)

    auto = calculate_auto_income(income_txns)

    return {
        "auto_detected": auto,
        "primary_income": primary_income,
        "total_monthly_income": round(auto["avg_monthly_income"] + primary_income, 2)
    }


@api_router.get("/analysis/investment-readiness")
async def get_investment_readiness(current_user: dict = Depends(get_current_user)):
    """Calculate investment readiness using the Spending Volatility Index risk engine."""
    # Self-heal stale data if user has no connected accounts
    await _self_heal_empty_bank_state(current_user["user_id"])

    profile = await db.financial_profiles.find_one(
        {"user_id": current_user["user_id"]}, {"_id": 0}
    )
    if not profile:
        profile = {"income": 0, "fixed_costs": 0, "safety_buffer": 500, "subscriptions": {}}

    accounts = await db.bank_accounts.find(
        {"user_id": current_user["user_id"]}, {"_id": 0}
    ).to_list(100)
    total_balance = sum(acc.get("balance", 0) for acc in accounts)

    transactions = await db.transactions.find(
        {"user_id": current_user["user_id"], "type": "expense"}, {"_id": 0}
    ).to_list(2000)

    # Auto-detect income from all positive inflows
    income_txns = await db.transactions.find(
        {"user_id": current_user["user_id"], "type": "income"}, {"_id": 0}
    ).to_list(2000)
    auto_income = calculate_auto_income(income_txns)
    auto_monthly = auto_income["avg_monthly_income"]

    primary_income = profile.get("primary_income", 0)
    manual_income = profile.get("income", 0)  # legacy field
    # Total income: auto-detected + primary (manual override takes priority over legacy)
    total_income = auto_monthly + primary_income + manual_income

    fixed_costs = profile.get("fixed_costs", 0)
    subs_total = sum(profile.get("subscriptions", {}).values())
    risk_tolerance = profile.get("risk_tolerance", "moderate")
    user_safety_buffer = profile.get("safety_buffer", 500)

    # 1. Calculate SVI
    svi_data = calculate_svi(transactions)
    svi = svi_data["svi"]

    # 2. Elastic Safety Buffer
    essential = svi_data["essential_monthly"]
    variable = svi_data["variable_monthly"]
    # If no categorized data yet, fall back to average spending
    if essential == 0 and variable == 0:
        monthly_spending = aggregate_monthly_spending(transactions)
        avg_spend = statistics.mean(monthly_spending.values()) if monthly_spending else 0
        essential = fixed_costs + subs_total
        variable = max(0, avg_spend - essential)

    elastic = calculate_elastic_buffer(essential, variable, svi, risk_tolerance)

    # Use the larger of elastic buffer or user-set buffer
    effective_buffer = max(elastic["buffer_amount"], user_safety_buffer)

    # 3. Spending Spike Detection
    spike_info = detect_spending_spike(svi_data.get("monthly_totals", {}))

    # 4. Earmarked bills = fixed_costs + subs (next month's known outflows)
    earmarked = fixed_costs + subs_total

    # 5. Calculate total available cash
    total_cash = total_income + total_balance

    # 6. Smart Safe to Invest
    safe = calculate_smart_safe_to_invest(total_cash, effective_buffer, earmarked, spike_info)

    # Legacy volatility ratio
    spending_amounts = list(aggregate_monthly_spending(transactions).values()) if transactions else [0]
    volatility_ratio = calculate_volatility_ratio(spending_amounts, user_safety_buffer)
    std_dev = statistics.stdev(spending_amounts) if len(spending_amounts) > 1 else 0

    # Status from safe-to-invest amount
    displayed = safe["displayed_safe_to_invest"]
    ref = total_income if total_income > 0 else total_balance
    status = "not_recommended"
    confidence = 0.4
    if safe["frozen"]:
        status, confidence = "frozen", 0.3
    elif displayed > ref * 0.2:
        status, confidence = "excellent", 0.9
    elif displayed > ref * 0.1:
        status, confidence = "good", 0.75
    elif displayed > 0:
        status, confidence = "moderate", 0.6

    return {
        "income": total_income,
        "income_breakdown": {
            "auto_detected": auto_monthly,
            "primary_income": primary_income,
            "manual_income": manual_income,
            "sources_count": len(auto_income.get("sources", [])),
        },
        "total_balance": round(total_balance, 2),
        "average_spending": round(essential + variable, 2),
        "subscriptions_total": round(subs_total, 2),
        "fixed_costs": fixed_costs,
        "svi": svi_data,
        "elastic_buffer": elastic,
        "effective_buffer": round(effective_buffer, 2),
        "spike_detection": spike_info,
        "safe_to_invest_engine": safe,
        "safe_to_invest": round(displayed, 2),
        "current_safety_buffer": round(effective_buffer, 2),
        "recommended_safety_buffer": round(elastic["buffer_amount"], 2),
        "volatility_ratio": volatility_ratio,
        "spending_std_deviation": round(std_dev, 2),
        "status": status,
        "confidence_level": confidence,
        "leftover_after_expenses": round(total_cash - earmarked - effective_buffer, 2),
        "volatility_impact": round(svi * elastic.get("svi_adjustment", 0), 2),
        "risk_tolerance": risk_tolerance,
        "needs_income_setup": False  # No longer a blocker — auto-detects income
    }

# ============== INVESTMENT OPTIONS ENDPOINTS ==============

# ============== INVESTMENT DATA HELPERS ==============

def _make_option(opt_type, desc, risk, ret, min_inv, url, summary, brokers):
    """Build a single investment option dict."""
    return {
        "type": opt_type, "description": desc,
        "risk_score": risk, "typical_return": ret,
        "min_investment": min_inv, "learn_more_url": url,
        "learn_more_summary": summary, "where_to_invest": brokers
    }

# Reusable broker references
_TR = {"name": "Trade Republic", "type": "broker", "url": "https://traderepublic.com"}
_DG = {"name": "Degiro", "type": "broker", "url": "https://www.degiro.com"}
_SC = {"name": "Scalable Capital", "type": "broker", "url": "https://www.scalable.capital"}
_IB = {"name": "Interactive Brokers", "type": "broker", "url": "https://www.interactivebrokers.eu"}
_XTB = {"name": "XTB", "type": "broker", "url": "https://www.xtb.com"}

def _br(base, note):
    return {**base, "note": note}

def _build_conservative_options():
    return [
        _make_option(
            "European Government Bonds",
            "Bonds issued by EU governments (German Bunds, French OATs, Dutch DSLs). Backed by sovereign credit, among the safest investments in Europe.",
            1, "2-3.5%", 100,
            "https://www.investopedia.com/terms/g/government-bond.asp",
            "Government bonds are debt securities issued by a government to fund spending. European bonds like German Bunds are considered extremely safe as they are backed by the issuing country's economy.",
            [_br(_TR, "Commission-free bonds, EU-regulated"), _br(_DG, "Low-cost European broker, wide bond selection"),
             {"name": "Your bank's investment desk", "type": "bank", "url": "", "note": "Most EU banks offer direct bond purchases"}]
        ),
        _make_option(
            "High-Yield Savings Accounts (EU)",
            "Savings accounts from European banks with competitive rates. Deposits up to EUR 100,000 are protected under the EU Deposit Guarantee Scheme.",
            1, "2.5-3.5%", 0,
            "https://www.investopedia.com/terms/h/high-yield-savings-account.asp",
            "High-yield savings offer higher interest than standard accounts while keeping your money liquid and insured. In the EU, deposits are protected up to EUR 100,000 per bank per depositor.",
            [{"name": "Raisin", "type": "platform", "url": "https://www.raisin.com", "note": "Compare savings rates across 400+ European banks"},
             {"name": "N26", "type": "bank", "url": "https://n26.com", "note": "Digital bank with competitive savings rates"},
             {"name": "Bunq", "type": "bank", "url": "https://www.bunq.com", "note": "Dutch digital bank offering savings accounts"}]
        ),
        _make_option(
            "EU Term Deposits",
            "Fixed-term deposits with guaranteed returns. Lock your money for 6-36 months at a fixed interest rate.",
            1, "2.5-4%", 500,
            "https://www.investopedia.com/terms/t/termdeposit.asp",
            "Term deposits lock your money for a set period in exchange for a guaranteed interest rate. Early withdrawal may incur penalties. Protected under EU Deposit Guarantee.",
            [{"name": "Raisin", "type": "platform", "url": "https://www.raisin.com", "note": "Access term deposits from banks across Europe"},
             {"name": "Your local bank", "type": "bank", "url": "", "note": "Most EU banks offer term deposits directly"}]
        ),
        _make_option(
            "Euro Money Market Funds",
            "Low-risk funds investing in short-term European debt instruments and interbank lending. Very liquid, very stable.",
            2, "3-3.5%", 100,
            "https://www.investopedia.com/terms/m/money-marketfund.asp",
            "Money market funds invest in short-term, high-quality debt instruments. They aim to maintain a stable value while providing returns slightly above savings accounts.",
            [_br(_TR, "Cash interest and money market fund access"), _br(_SC, "German robo-advisor with money market options"), _br(_DG, "Access to EUR money market ETFs")]
        ),
    ]

def _build_moderate_options():
    return [
        _make_option(
            "Euro Bond ETFs",
            "Diversified European bond funds (iShares Euro Aggregate Bond ETF, Vanguard EUR Eurozone Government Bond ETF). Spread risk across hundreds of bonds.",
            3, "3-5%", 50,
            "https://www.investopedia.com/terms/b/bond-etf.asp",
            "Bond ETFs hold a basket of bonds and trade on stock exchanges. They provide diversification, regular income, and more liquidity than individual bonds.",
            [_br(_TR, "Commission-free ETF savings plans"), _br(_SC, "Automated portfolio with bond allocation"), _br(_IB, "Wide ETF selection, advanced tools")]
        ),
        _make_option(
            "European Dividend ETFs",
            "ETFs focused on European companies paying regular dividends (SPDR Euro Dividend Aristocrats, iShares Euro Dividend UCITS).",
            4, "5-7%", 50,
            "https://www.investopedia.com/terms/d/dividendyield.asp",
            "Dividend ETFs invest in companies that regularly pay dividends. They provide both share price appreciation and regular income payments.",
            [_br(_TR, "Free ETF savings plans from EUR 1"), _br(_DG, "Low-cost access to European dividend ETFs"), _br(_XTB, "Commission-free ETF investing, EU-regulated")]
        ),
        _make_option(
            "Index Funds (UCITS)",
            "Passively managed funds that track a market index (e.g., Euro Stoxx 50, FTSE 100). Lower fees than actively managed funds, broad diversification.",
            4, "5-8%", 100,
            "https://www.investopedia.com/terms/i/indexfund.asp",
            "Index funds aim to replicate the performance of a market index by holding the same stocks in the same proportions. They offer low fees (typically 0.1-0.3% per year), automatic diversification, and historically outperform most actively managed funds over the long term.",
            [_br(_SC, "Robo-advisor with index fund portfolios"), {"name": "Vanguard Investor", "type": "broker", "url": "https://www.vanguardinvestor.co.uk", "note": "Pioneer of index investing, low-cost funds"},
             {"name": "Fidelity International", "type": "broker", "url": "https://www.fidelityinternational.com", "note": "Wide range of index funds across Europe"}]
        ),
        _make_option(
            "Target-Date / Lifecycle Funds",
            "Funds that automatically shift from stocks to bonds as your target retirement date approaches. Set it and forget it.",
            4, "5-7%", 500,
            "https://www.investopedia.com/terms/t/target-date_fund.asp",
            "Target-date funds automatically rebalance between stocks and bonds over time, becoming more conservative as the target date nears.",
            [_br(_SC, "Robo-advisor with auto-rebalancing portfolios"),
             {"name": "Vanguard Investor", "type": "broker", "url": "https://www.vanguardinvestor.co.uk", "note": "LifeStrategy funds available in EU/UK"},
             {"name": "Fidelity International", "type": "broker", "url": "https://www.fidelityinternational.com", "note": "Lifecycle funds across Europe"}]
        ),
        _make_option(
            "European REITs",
            "Real Estate Investment Trusts focused on European property (Vonovia, Unibail-Rodamco-Westfield). Own a piece of commercial real estate without buying property.",
            5, "6-9%", 100,
            "https://www.investopedia.com/terms/r/reit.asp",
            "REITs are companies that own or finance income-producing real estate. They must distribute at least 90% of taxable income as dividends.",
            [_br(_DG, "Access to European REIT stocks and ETFs"), _br(_IB, "Full access to EU stock exchanges"), _br(_TR, "Fractional shares of REITs available")]
        ),
    ]

def _build_aggressive_options():
    return [
        _make_option(
            "MSCI Europe / STOXX 600 ETFs",
            "Broad European market ETFs (iShares STOXX Europe 600, Amundi MSCI Europe). Invest across 600+ European companies in one trade.",
            6, "8-12%", 50,
            "https://www.investopedia.com/terms/e/etf.asp",
            "ETFs that track the entire European stock market provide broad diversification. The STOXX 600 covers 600 companies across 17 European countries.",
            [_br(_TR, "Commission-free ETF savings plans"), _br(_DG, "Core selection ETFs at low cost"), _br(_SC, "Flat-fee trading for unlimited ETF trades")]
        ),
        _make_option(
            "MSCI World / Global Index Funds",
            "Global diversification via index funds or ETFs (iShares Core MSCI World UCITS, Vanguard FTSE All-World). Invest in 1,500+ companies from 23 developed countries.",
            6, "9-13%", 50,
            "https://www.investopedia.com/terms/m/msci-acwi.asp",
            "MSCI World funds give exposure to the entire developed world economy. A one-fund solution for global diversification. Long-term average returns: 8-10% annually.",
            [_br(_TR, "Most popular EU ETF savings plan provider"), _br(_SC, "Robo-advisor or self-directed MSCI World investing"), _br(_IB, "Lowest FX costs for USD-denominated ETFs")]
        ),
        _make_option(
            "Emerging Markets ETFs",
            "ETFs investing in developing economies (iShares Core MSCI EM, Amundi MSCI Emerging Markets). Higher growth potential from China, India, Brazil.",
            7, "8-14%", 50,
            "https://www.investopedia.com/terms/e/emergingmarketfund.asp",
            "Emerging market ETFs invest in developing economies with higher growth potential. More volatile due to political instability and currency risk, but historically offer higher long-term returns.",
            [_br(_TR, "EM ETF savings plans available"), _br(_DG, "Wide selection of EM ETFs"), _br(_XTB, "Commission-free EM ETF investing")]
        ),
        _make_option(
            "European Sector ETFs (Tech, Green Energy)",
            "Concentrated bets on European technology, clean energy, or healthcare sectors. Higher risk, higher reward.",
            8, "10-20%", 50,
            "https://www.investopedia.com/terms/s/sector-etf.asp",
            "Sector ETFs focus on a single industry. They offer concentrated exposure which can amplify gains but also losses. Green energy ETFs have become popular as Europe pushes for climate neutrality by 2050.",
            [_br(_TR, "Sector ETFs and thematic investing"), _br(_SC, "Thematic portfolio options"), _br(_IB, "Widest selection of sector ETFs")]
        ),
        _make_option(
            "CFDs (Contracts for Difference)",
            "Speculative instruments that let you trade on price movements of stocks, indices, commodities, and forex without owning the underlying asset. Use leverage to amplify gains — and losses.",
            9, "Variable (high risk of loss)", 50,
            "https://www.investopedia.com/terms/c/contractfordifferences.asp",
            "CFDs are complex derivatives where you speculate on price movements. You can go long (bet prices rise) or short (bet prices fall). Leverage means you can control a large position with a small deposit, but losses can exceed your initial investment. ESMA regulations cap EU retail leverage at 30:1 for major forex, 20:1 for indices, 5:1 for shares. 74-89% of retail CFD accounts lose money.",
            [_br(_XTB, "EU-regulated CFD broker, educational resources"),
             {"name": "eToro", "type": "broker", "url": "https://www.etoro.com", "note": "Social trading platform with CFDs, EU-regulated"},
             {"name": "Plus500", "type": "broker", "url": "https://www.plus500.com", "note": "CFD-only broker, simple interface, EU-regulated"}]
        ),
    ]

def _build_bank_safe_options():
    return [
        {"type": "High-Yield Savings Account",
         "description": "EU Deposit Guarantee Scheme up to EUR 100,000. Ask your bank for their best savings rate.",
         "typical_apy": "2.5-3.5%",
         "learn_more_url": "https://www.investopedia.com/terms/h/high-yield-savings-account.asp",
         "learn_more_summary": "A savings account that pays a higher interest rate. In the EU, deposits up to EUR 100,000 are protected per depositor per bank.",
         "recommended_banks": ["N26", "Bunq", "Raisin (multi-bank)", "ING", "Revolut"]},
        {"type": "Term Deposits / Fixed Deposits",
         "description": "Lock money for 6-36 months at guaranteed rates. Covered by EU Deposit Guarantee Scheme.",
         "typical_apy": "2.5-4.0%",
         "learn_more_url": "https://www.investopedia.com/terms/t/termdeposit.asp",
         "learn_more_summary": "A fixed-term investment with a guaranteed interest rate. Penalties apply for early withdrawal. Fully protected under EU deposit insurance.",
         "recommended_banks": ["Raisin (compare 400+ banks)", "Your local bank"]},
        {"type": "Government Savings Bonds",
         "description": "Some EU countries offer direct savings bonds to citizens. Very safe, backed by the government.",
         "typical_apy": "2-3.5%",
         "learn_more_url": "https://www.investopedia.com/terms/s/savingsbond.asp",
         "learn_more_summary": "Government savings bonds are debt instruments issued directly to citizens. Virtually risk-free as they are backed by the full faith of the government.",
         "recommended_banks": ["Your country's treasury/government savings programme"]},
    ]

INVESTMENT_DISCLAIMER = (
    "IMPORTANT: All investment decisions are made at your own risk. Past performance does not guarantee future results. "
    "Consult a licensed financial advisor before making investment decisions. We are not brokers and do not execute trades on your behalf."
)

CFD_WARNING = (
    "CFDs are complex instruments and come with a high risk of losing money rapidly due to leverage. "
    "74-89% of retail investor accounts lose money when trading CFDs. You should consider whether you understand "
    "how CFDs work and whether you can afford to take the high risk of losing your money."
)

@api_router.get("/investments/options")
async def get_investment_options(current_user: dict = Depends(get_current_user)):
    """Get European investment options with educational links and broker recommendations."""
    return {
        "disclaimer": INVESTMENT_DISCLAIMER,
        "cfd_warning": CFD_WARNING,
        "region": "Europe",
        "options": {
            "conservative": {
                "title": "Conservative Portfolio",
                "risk_level": "Low",
                "risk_probability": 0.15,
                "expected_return": "2-4% annually",
                "options": _build_conservative_options()
            },
            "moderate": {
                "title": "Balanced Portfolio",
                "risk_level": "Medium",
                "risk_probability": 0.35,
                "expected_return": "5-8% annually",
                "options": _build_moderate_options()
            },
            "aggressive": {
                "title": "Growth Portfolio",
                "risk_level": "High",
                "risk_probability": 0.55,
                "expected_return": "8-15% annually",
                "options": _build_aggressive_options()
            }
        },
        "bank_safe_options": _build_bank_safe_options()
    }

# ============== AI ADVISOR ENDPOINTS ==============

_ADVISOR_SYSTEM_MESSAGE = """You are a professional financial advisor AI, similar to robo-advisors like Betterment. 
Your role is to provide personalized financial advice based on the user's financial situation.

IMPORTANT GUIDELINES:
1. Always start with a risk disclaimer
2. Provide specific, actionable advice based on their financial data
3. Recommend investment options across risk levels (conservative, moderate, aggressive)
4. Include probability of risk for each recommendation
5. Suggest optimization opportunities (subscriptions, spending categories)
6. Be empathetic but data-driven
7. Never guarantee returns
8. Remind users to consult licensed financial advisors for major decisions

Format your response with clear sections:
- Risk Disclaimer
- Financial Health Assessment
- Investment Recommendations (with risk probabilities)
- Optimization Opportunities
- Action Items"""


def _build_advisor_context(profile: dict, spending: dict, readiness: dict) -> str:
    """Build the financial context prompt for the AI advisor."""
    categories = "\n".join(
        [f"- {cat}: ${amt:,.2f}" for cat, amt in spending.get("by_category", {}).items()]
    )
    return f"""
User Financial Profile:
- Monthly Income: ${profile.get('income', 0):,.2f}
- Fixed Costs: ${profile.get('fixed_costs', 0):,.2f}
- Safety Buffer: ${profile.get('safety_buffer', 500):,.2f}
- Risk Tolerance: {profile.get('risk_tolerance', 'moderate')}

Spending Analysis:
- Average Monthly Spending: ${spending.get('average_monthly_spending', 0):,.2f}
- Spending Volatility (Std Dev): ${spending.get('spending_std_deviation', 0):,.2f}
- Total Recent Spending: ${spending.get('total_spending', 0):,.2f}

Investment Readiness:
- Safe to Invest Amount: ${readiness.get('safe_to_invest', 0):,.2f}
- Status: {readiness.get('status', 'unknown')}
- Confidence Level: {readiness.get('confidence_level', 0):.0%}
- Volatility Ratio: {readiness.get('volatility_ratio', 0)}

Spending by Category:
{categories}
"""

@api_router.post("/advisor/advice")
async def get_ai_advice(
    advice_request: AIAdviceRequest,
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered financial advice"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    # Get user's financial data
    profile = await db.financial_profiles.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    readiness = await get_investment_readiness(current_user)
    spending = await get_spending_summary(current_user)
    
    # Prepare context
    financial_context = _build_advisor_context(profile, spending, readiness)
    
    system_message = _ADVISOR_SYSTEM_MESSAGE

    api_key = os.environ.get('EMERGENT_LLM_KEY')
    
    chat = LlmChat(
        api_key=api_key,
        session_id=f"advisor_{current_user['user_id']}_{uuid.uuid4().hex[:8]}",
        system_message=system_message
    ).with_model("openai", "gpt-4o-mini")
    
    user_question = advice_request.question or "Please analyze my financial situation and provide personalized investment advice."
    
    full_message = f"{financial_context}\n\nUser Question: {user_question}"
    
    if advice_request.context:
        full_message += f"\n\nAdditional Context: {advice_request.context}"
    
    user_message = UserMessage(text=full_message)
    
    try:
        response = await chat.send_message(user_message)
        
        # Store advice in history
        advice_doc = {
            "advice_id": f"adv_{uuid.uuid4().hex[:12]}",
            "user_id": current_user["user_id"],
            "question": advice_request.question,
            "response": response,
            "financial_snapshot": {
                "income": profile.get('income', 0),
                "safe_to_invest": readiness.get('safe_to_invest', 0),
                "status": readiness.get('status', 'unknown')
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.advice_history.insert_one(advice_doc)
        
        return {
            "advice": response,
            "disclaimer": "IMPORTANT: This advice is generated by AI and is for informational purposes only. All investments carry risk and you may lose money. Past performance does not guarantee future results. Always consult with a licensed financial advisor before making investment decisions. Investing according to this advice is at your own risk.",
            "confidence_level": readiness.get('confidence_level', 0.5),
            "financial_snapshot": advice_doc["financial_snapshot"]
        }
    except Exception as e:
        logger.error(f"AI advice error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate advice")

@api_router.get("/advisor/history")
async def get_advice_history(current_user: dict = Depends(get_current_user)):
    """Get user's advice history"""
    history = await db.advice_history.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return history

# ============== BUDGETS + RECURRING TXN DETECTION ==============
# Routes extracted to routes/budgets.py.
# Re-import the recurring helpers so that other endpoints (analysis/auto-detect)
# can still use them without duplicating logic.
from routes.budgets import (  # noqa: E402
    _group_transactions_by_pattern,
    _parse_dates,
    _detect_frequency,
)

# ============== PORTFOLIO REBALANCING ==============
# Routes extracted to routes/portfolio.py. The router is included at the bottom
# of this module after all dependencies (`get_current_user`, `db`) are defined.

# ============== PORTFOLIO SIMULATION ==============
# Routes extracted to routes/simulator.py.

# ============== GDPR ENDPOINTS ==============
# Routes extracted to routes/gdpr.py.


# ============== AUTO-DETECT INCOME & SUBSCRIPTIONS ==============

@api_router.get("/analysis/auto-detect")
async def auto_detect_patterns(current_user: dict = Depends(get_current_user)):
    """Auto-detect recurring income deposits and subscription outflows from transaction patterns."""
    user_id = current_user["user_id"]

    # Get ALL transactions (income + expense)
    all_txns = await db.transactions.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("date", 1).to_list(5000)

    if len(all_txns) < 3:
        return {"detected_income": [], "detected_subscriptions": [], "message": "Need more transactions to detect patterns"}

    income_txns = [t for t in all_txns if t.get("type") == "income"]
    expense_txns = [t for t in all_txns if t.get("type") == "expense"]

    def _detect_recurring(txns):
        groups = _group_transactions_by_pattern(txns)
        results = []
        for group in groups.values():
            if len(group) < 2:
                continue
            dates = _parse_dates(group)
            result = _detect_frequency(dates)
            if not result:
                continue
            frequency, avg_interval = result
            amounts = [t.get("amount", 0) for t in group]
            latest = group[-1]
            avg_amount = round(statistics.mean(amounts), 2)
            results.append({
                "description": latest.get("description", ""),
                "category": latest.get("category", "Other"),
                "average_amount": avg_amount,
                "frequency": frequency,
                "occurrences": len(group),
                "last_date": latest.get("date", ""),
                "avg_interval_days": round(avg_interval, 1)
            })
        results.sort(key=lambda x: x["average_amount"], reverse=True)
        return results

    detected_income = _detect_recurring(income_txns)
    detected_subs = _detect_recurring(expense_txns)

    # Estimate total monthly income from detected patterns
    estimated_monthly_income = 0.0
    for inc in detected_income:
        if inc["frequency"] == "monthly":
            estimated_monthly_income += inc["average_amount"]
        elif inc["frequency"] == "weekly":
            estimated_monthly_income += inc["average_amount"] * 4.33

    # Estimate total monthly subscriptions
    estimated_monthly_subs = 0.0
    subs_map = {}
    for sub in detected_subs:
        monthly = sub["average_amount"] if sub["frequency"] == "monthly" else sub["average_amount"] * 4.33
        estimated_monthly_subs += monthly
        subs_map[sub["description"] or sub["category"]] = round(monthly, 2)

    return {
        "detected_income": detected_income,
        "detected_subscriptions": detected_subs,
        "estimated_monthly_income": round(estimated_monthly_income, 2),
        "estimated_monthly_subscriptions": round(estimated_monthly_subs, 2),
        "suggested_subscriptions_map": subs_map
    }


@api_router.post("/analysis/auto-detect/apply")
async def apply_auto_detected(request: Request, current_user: dict = Depends(get_current_user)):
    """Apply auto-detected income/subscriptions to financial profile."""
    body = await request.json()
    income = body.get("income")
    subscriptions = body.get("subscriptions")
    fixed_costs = body.get("fixed_costs")

    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if income is not None:
        update_data["income"] = income
    if subscriptions is not None:
        update_data["subscriptions"] = subscriptions
    if fixed_costs is not None:
        update_data["fixed_costs"] = fixed_costs

    await db.financial_profiles.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": update_data}
    )

    profile = await db.financial_profiles.find_one(
        {"user_id": current_user["user_id"]}, {"_id": 0}
    )
    return profile


# ============== ROOT ENDPOINT ==============

@api_router.get("/")
async def root():
    return {"message": "FlowVise API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include the router in the main app
app.include_router(api_router)

# ============== ROUTE MODULES (extracted) ==============
# Imported AFTER all shared deps (db, get_current_user, audit_log, ...) are
# defined above so that core.py's re-exports resolve cleanly.
from routes import portfolio as _portfolio_routes  # noqa: E402
from routes import simulator as _simulator_routes  # noqa: E402
from routes import tink as _tink_routes  # noqa: E402
from routes import gdpr as _gdpr_routes  # noqa: E402
from routes import budgets as _budgets_routes  # noqa: E402

app.include_router(_portfolio_routes.router, prefix="/api")
app.include_router(_simulator_routes.router, prefix="/api")
app.include_router(_tink_routes.router, prefix="/api")
app.include_router(_gdpr_routes.router, prefix="/api")
app.include_router(_budgets_routes.router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
