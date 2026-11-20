# Re:Build — Construction Material Reuse & Allocation Optimiser

A full-stack circular construction resource exchange demo. Frontend: React 19 + Vite + Tailwind CSS + Recharts + Leaflet. Backend: FastAPI + SQLAlchemy + SQLite + PuLP (CBC solver, with constrained deterministic fallback). JWT role-based authentication.

> **Demo data notice:** all seeded organisations, listings and demands are synthetic. Road-distance, freight, emissions, virgin-material replacement, money and virtual-water factors are illustrative assumptions, not quotes or audited lifecycle-assessment results. A material passport is a configurable rule-based screening record, not a lab certificate. Photos cannot chemically identify contamination, hazardous coatings or asbestos.

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # optional; set a unique SECRET_KEY for non-demo use
uvicorn app.main:app --reload --port 8000 --env-file .env
```

The API creates `reuse_optimizer.db`, seeds 18 synthetic listings and 12 demands on first launch, and serves uploads from `/uploads`. Interactive API docs: http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. For LLM extraction, set `AI_PROVIDER=openai`, `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in the backend environment. Without a key, deterministic extraction is used. Set `VITE_API_URL` to override the API base (default `http://localhost:8000/api`).

## Demo accounts

All passwords: `Demo@123`

| Role | Email |
|---|---|
| Supplier | `supplier1@demo.reuse` |
| Buyer | `buyer1@demo.reuse` |
| Admin | `admin@demo.reuse` |

Other seeded supplier accounts: `supplier2@demo.reuse` through `supplier5@demo.reuse`; buyers: `buyer2@demo.reuse` through `buyer4@demo.reuse`.

## Demo walkthrough

1. Sign in as a supplier. Browse seeded inventory or add a recovered concrete listing. The listing assistant uses the OpenAI API when `AI_PROVIDER=openai` and `OPENAI_API_KEY` is configured; otherwise it uses the deterministic parser. Review all fields before saving.
2. Sign in as a buyer and post a demand, e.g. concrete rubble for a recharge pit. Demands include location, minimum quality and deadline.
3. Sign in as admin. Open **Safety & audit** to inspect rule-based material passports. Contaminated, painted and treated stock is blocked; pre-2000 stock requires lab verification for farm/water uses.
4. Open **Optimiser**, change monsoon priority and run the solver. The setting changes the urgency bonus. The PuLP model maximises weighted feasible allocations under per-material stock and per-demand quantity constraints.
5. Inspect proposed matches and routes on **Network map**. Confirm an allocation to reserve stock, dispatch it to In Transit, then mark it Delivered.
6. **Impact** totals update only for Delivered allocations. Export the impact CSV.

## API overview

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET/POST/PUT/DELETE /api/materials`, `POST /api/uploads`
- `GET/POST /api/demands`
- `POST /api/ai/parse-material`
- `POST /api/optimise`, `GET /api/allocations`, `PATCH /api/allocations/{id}/status`
- `GET /api/dashboard`, `GET /api/audit`, `GET /api/impact/export.csv`

## Safety and allocation invariants

- Unsafe material flags and restricted intended uses are screened before an allocation variable is created.
- Pre-2000 building material used for farm/water applications needs a lab verification flag.
- Optimisation uses available stock (`quantity - reserved_quantity`); proposed matches do not reserve inventory.
- Confirmation reserves stock; delivery consumes the reservation and reduces total quantity. The API rejects invalid lifecycle transitions and attempts to reserve more than available stock.
- Impact metrics use delivered allocations only.

## Tests

```bash
cd backend
pytest -q
```

Tests cover core safety rules, unsafe candidate exclusion and optimiser supply/demand limits. For production, add database-level concurrency tests on PostgreSQL and use a migration system; SQLite is intended for this hackathon demo.

## Production hardening checklist

Replace the demo secret, add email verification/password reset, move uploads to object storage with malware scanning, add HTTPS and rate limits, use PostgreSQL + Alembic migrations, persist solver run snapshots, add stronger role/ownership policy, and validate safety against jurisdiction-specific engineering standards and independent lab reports.
