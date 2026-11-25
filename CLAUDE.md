# FlowWise handoff for Claude Code

Checked 25 November 2026 (Europe/Warsaw) against public repo [buenobuenobrrr/flowvise](https://github.com/buenobuenobrrr/flowvise) (`main` at `640e81c7cb36707a15675d04cdac46ec025752ae`), its open pull requests, and `README.md`. Product direction is from the Cursor project preferences. Older project notes that still say “create a private GitHub repo” are out of date: this public repo is the code.

Repo folder spelling is `flowvise`. Product name is **FlowWise**.

## What to do next

1. Clone `main` and run the app locally (commands below). Email and password work against a local API and Mongo. Leave [PR #3](https://github.com/buenobuenobrrr/flowvise/pull/3) (`cursor/monarch-style-ui-7d0c`) untouched: another worker owns that branch. Do not push to it, edit it, or merge it.
2. Continue the product on a new branch from `main`. Poland is the operating business: cash flow across banks, a conservative safe-to-invest figure labeled as a rule of thumb, and investing help aimed at IKE, IKZE, and emergency cash in złoty. Keep the name, look, layout, and copy original enough that FlowWise is not a clone of Monarch Money or Rocket Money. Borrowing those products’ ideas is fine.
3. Treat https://flowwise.apps.grok.bot as a frontend-only preview. It has no API, so sign-in there does not work. Real use is local until a hosted API and Mongo exist.
4. When a host is ready, set secrets in Cursor’s secure form. Never paste secret values into chat or commit them.

IKE and IKZE do not appear in the repo. Settings has an emergency-fund amount field; there is no separate “emergency cash in złoty” feature. PLN is one currency in the picker. The UI uses a saved choice, otherwise the browser locale, otherwise EUR.

## Product

FlowWise is an AI-assisted personal finance app for someone operating in Poland.

- Cash flow across banks (accounts, spending, budgets).
- Safe-to-invest is a labeled rule of thumb. It is not regulated advice and not a stock tip. On `main` the API already computes a figure and the UI calls it “Safe to Invest”, without that rule-of-thumb label. The calculation in `backend/server.py` (`calculate_smart_safe_to_invest`) is: cash minus the elastic buffer minus earmarked bills, then 80% of that remainder on screen (20% held back). A spending-spike cooling-off period shows 0. Keep that meaning, and label it as a rule of thumb.
- Investing help should point at IKE, IKZE, and emergency cash kept in złoty. Those products are the goal; they are not built yet.
- Screens already on `main`: auth, dashboard, bank accounts, spending, budgets and alerts, investments, portfolio, portfolio simulator, AI advisor, settings, plus GDPR routes.

Features beyond this inventory need Bruno’s OK. The app is not a licensed advisory product.

## Stack and how to run locally

From `README.md` on `main`:

- Frontend: React 19, Create React App + CRACO, React Router 7, Tailwind, shadcn/Radix, React Hook Form + Zod, Axios, Recharts, Sonner. Yarn 1.x. Node.js 18+.
- Backend: FastAPI + Uvicorn, Motor/MongoDB, JWT, Fernet for sensitive fields. Python 3.11+.
- MongoDB 7 via Docker Compose (`docker-compose.yml` publishes `27017`).

```bash
docker compose up -d mongo

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill MONGO_URL=mongodb://127.0.0.1:27017, DB_NAME=flowvise,
# CORS_ORIGINS for localhost:3000, and locally generated JWT_SECRET
# and ENCRYPTION_KEY. COOKIE_SECURE=false on local HTTP.
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Health: `GET http://127.0.0.1:8000/api/health`

```bash
cd frontend
cp .env.example .env
# REACT_APP_BACKEND_URL=http://127.0.0.1:8000
yarn install
yarn start
```

App: `http://localhost:3000`

Local path in the README: register, verify email, dashboard, demo bank connect (checking, savings, brokerage), spending, budgets, portfolio drift, simulator, AI advisor when a key is set. Password rule on register: at least 8 characters with upper, lower, digit, and special.

Tests (API must be up):

```bash
cd backend && source .venv/bin/activate
REACT_APP_BACKEND_URL=http://127.0.0.1:8000 pytest tests/test_mvp_auth_core_flows.py tests/test_portfolio_simulator_advisor.py -q
```

Routers mounted in `backend/server.py`: auth, categories, transactions, Plaid-style link endpoints, bank accounts, financial profile, analysis, investments, advisor, plus `portfolio`, `simulator`, `tink`, `gdpr`, and `budgets`. There is no `tank` route in this tree.

## What is merged vs PR #3

`main` history:

| Commit | What landed |
| --- | --- |
| `3f3bc11` | Initial commit |
| `e2855ae` | Cleaned Emergent export |
| `93c73ab` | PR #1, merged 23 Nov 2026, 13:54 Europe/Warsaw. Local stack and MVP auth through budgets. |
| `640e81c` | PR #2, merged 23 Nov 2026, 15:37 Europe/Warsaw. Portfolio demo holdings, simulator, OpenAI-backed AI advisor. |

Open pull requests: only [#3](https://github.com/buenobuenobrrr/flowvise/pull/3), “Restyle FlowWise with an original light ledger look”, head `cursor/monarch-style-ui-7d0c` at `4cecc23ccab73312a1118d432bb3df62e57ed5cd`. Opened 23 Nov 2026, 23:32 Europe/Warsaw. Updated 24 Nov 2026, 00:34 Europe/Warsaw. Not merged. 6 commits, 63 files, +1089 / −641. Base is current `main`.

PR #3’s stated visual system (not on `main`): cool mist page, white sheets, hairline borders, copper for primary actions, cyan only for positive amounts, Fraunces for titles and figures, Outfit for UI, top bar instead of the left rail, light mode default. `main` still has the earlier theme.

The same PR also replaces Emergent Google sign-in with Google and Apple ID-token routes (`/api/auth/google`, `/api/auth/apple`, `/api/auth/providers`). Those routes answer 503 until `GOOGLE_CLIENT_ID` and `APPLE_CLIENT_ID` are set. That code is only on the PR branch. On `main`, “Continue with Google” still sends the browser to Emergent’s auth host, and `POST /api/auth/google/session` still calls Emergent’s demo backend.

## Live site

https://flowwise.apps.grok.bot is frontend-only. There is no API behind it, so sign-in there does not work. Use the local API on port 8000.

## Blockers

Names only. Put values in Cursor’s secure form. Never paste them into chat, issues, or git.

| Need | Name on `main` | What happens while it is empty |
| --- | --- | --- |
| Hosted API and Mongo | `MONGO_URL`, `DB_NAME` | Only local Docker / a URI you run yourself. The public site has no API. |
| Email | `RESEND_API_KEY`, `SENDER_EMAIL` | Verification is not sent through Resend. The API returns the code for local use. |
| Open banking | `TINK_CLIENT_ID`, `TINK_CLIENT_SECRET` | Tink link returns 503. Use the built-in demo bank connect. |
| AI advisor | `OPENAI_API_KEY` (optional `OPENAI_BASE_URL`, `OPENAI_MODEL`, default model `gpt-4o-mini`) | `/api/advisor/advice` returns 503. |
| Google and Apple | `GOOGLE_CLIENT_ID`, `APPLE_CLIENT_ID` | Not in `main`’s `.env.example`. PR #3 adds them and reads them on the API. Provision both through Cursor’s secure form. Email and password do not need them. |

Also required locally, and never committed: `JWT_SECRET`, `ENCRYPTION_KEY`. Generate them on the machine. `COOKIE_SECURE=false` for local HTTP.

Frontend env on `main`: `REACT_APP_BACKEND_URL`, `WDS_SOCKET_PORT`, `ENABLE_HEALTH_CHECK`.
