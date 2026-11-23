# FlowWise

AI-assisted personal finance (accounts, budgets, spending, portfolio, advisor).

**Stack:** React (CRA + CRACO, Tailwind) frontend · FastAPI + MongoDB backend.  
**Repo spelling:** `flowvise` · **Product name:** FlowWise.

## Prerequisites

- Node.js 18+ and Yarn 1.x
- Python 3.11+ (with `virtualenv` or `python3-venv`)
- MongoDB 7 (Docker Compose below, or a local/Atlas URI)

## 1. MongoDB

```bash
# Option A — Docker
docker compose up -d mongo

# Option B — already-running local mongod on 27017
# (nothing to do)
```

## 2. Backend

```bash
cd backend
virtualenv .venv && source .venv/bin/activate   # or: python -m venv .venv
pip install -r requirements.txt
cp .env.example .env
```

Generate secrets and fill `.env` (do **not** commit):

```bash
python - <<'PY'
from cryptography.fernet import Fernet
import secrets
print("JWT_SECRET=" + secrets.token_urlsafe(48))
print("ENCRYPTION_KEY=" + Fernet.generate_key().decode())
PY
```

Minimal local `.env`:

```
MONGO_URL=mongodb://127.0.0.1:27017
DB_NAME=flowvise
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
JWT_SECRET=<generated>
ENCRYPTION_KEY=<generated>
COOKIE_SECURE=false
RESEND_API_KEY=
SENDER_EMAIL=onboarding@resend.dev
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4o-mini
TINK_CLIENT_ID=
TINK_CLIENT_SECRET=
```

Leave Resend / Tink / OpenAI keys empty for local demo mode (emails log `demo_code`; bank linking uses the built-in demo institutions; AI advisor returns 503 until `OPENAI_API_KEY` is set).

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Health: `GET http://127.0.0.1:8000/api/health`

## 3. Frontend

```bash
cd frontend
cp .env.example .env
# REACT_APP_BACKEND_URL=http://127.0.0.1:8000
# WDS_SOCKET_PORT=0
yarn install
yarn start
```

App: `http://localhost:3000`

## MVP flows (local)

1. **Auth** — Register → use on-screen / API `demo_code` → verify → JWT session (Bearer + cookie).
2. **Dashboard** — spending summary + investment readiness + balances.
3. **Accounts** — Connect Bank → **Demo mode** (checking + savings + brokerage; Tink needs real keys).
4. **Spending** — charts + transactions from demo import or manual add.
5. **Budgets** — create category budgets and view alerts.
6. **Portfolio** — auto-detect holdings from demo accounts → drift vs risk tier.
7. **Simulator** — simple compound or Monte Carlo projections (no external keys).
8. **AI Advisor** — chat via OpenAI when `OPENAI_API_KEY` is set; otherwise 503 + UI message.

Password rules: ≥8 chars, upper, lower, digit, special.

## Tests

```bash
cd backend
source .venv/bin/activate
REACT_APP_BACKEND_URL=http://127.0.0.1:8000 pytest tests/test_mvp_auth_core_flows.py tests/test_portfolio_simulator_advisor.py -q
```

## What’s stubbed without paid keys

| Integration | Behavior without keys |
|-------------|------------------------|
| Resend email | Codes logged / returned as `demo_code` |
| Tink Open Banking | `/tink/link` → 503; use Demo bank connect |
| AI Advisor (`OPENAI_API_KEY`) | `/advisor/advice` → 503; UI shows unavailable banner |
| Google OAuth | Still points at Emergent auth host — use email/password locally |

## Config notes

- Copy `.env.example` → `.env` in `backend/` and `frontend/`. Never commit secrets.
- `COOKIE_SECURE=false` for local HTTP; set `true` behind HTTPS.
- `design_guidelines.json` describes the UI theme.
