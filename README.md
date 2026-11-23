# FlowWise

Personal finance app (bank linking, budgets, portfolio tools, AI advisor).

**Stack:** React (CRA + CRACO, Tailwind) frontend · FastAPI + MongoDB backend.

## Prerequisites

- Node.js 18+ and Yarn 1.x
- Python 3.11+
- MongoDB (local or Atlas)

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill in values (names only in the example)
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

API base: `http://localhost:8000` (routes under `/api`).

## Frontend

```bash
cd frontend
cp .env.example .env
# Set REACT_APP_BACKEND_URL=http://localhost:8000
yarn install
yarn start
```

App: `http://localhost:3000`.

## Config

Copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` → `frontend/.env`.  
Do not commit real `.env` files.

`design_guidelines.json` at the repo root describes the UI theme.

## Tests

```bash
cd backend
pytest tests/
```

Root `backend_test.py` and `tests/` are additional/legacy helpers from the Emergent export.
