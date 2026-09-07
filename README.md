# T-RexX API

FastAPI backend with a layered structure that keeps HTTP, business logic, and data models separate.

## Project structure

```
T-RexX/
├── app/
│   ├── main.py                     # App factory + entrypoint (create_app, app)
│   ├── core/
│   │   └── config.py               # Settings loaded from env / .env
│   ├── api/
│   │   └── v1/
│   │       ├── router.py           # Aggregates all v1 route modules
│   │       └── routes/
│   │           ├── health.py       # /health
│   │           └── items.py        # /items CRUD (thin HTTP layer)
│   ├── schemas/
│   │   └── item.py                 # Pydantic request/response models
│   └── services/
│       └── item_service.py         # Business logic (no HTTP knowledge)
├── tests/
│   └── test_items.py
├── requirements.txt                # Runtime dependencies
├── requirements-dev.txt            # + test/lint tooling
├── .env.example                    # Copy to .env
└── .gitignore
```

### The layers, and why they're split

| Layer | Folder | Responsibility |
|-------|--------|----------------|
| **Route** | `api/v1/routes/` | Parse the request, call a service, shape the HTTP response. No business logic. |
| **Service** | `services/` | The actual work / domain rules. Pure Python — easy to unit test, framework-agnostic. |
| **Schema** | `schemas/` | Pydantic models validating what comes in and what goes out. |
| **Core** | `core/` | Cross-cutting config and (later) security, logging, DB session. |

Routes depend on services; services depend on schemas. Nothing depends on `main.py`.
This makes each piece independently testable and lets you swap the in-memory store in
`item_service.py` for a real database without touching a single route.

## Setup

The virtual environment lives in `.venv/`.

```powershell
# Activate (PowerShell)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements-dev.txt
```

> On Git Bash / WSL use `source .venv/Scripts/activate` instead.

## Run

```powershell
uvicorn app.main:app --reload
```

- API root: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health: http://127.0.0.1:8000/api/v1/health

## Adding a new feature (the pattern)

1. Add request/response models in `app/schemas/<feature>.py`.
2. Add business logic in `app/services/<feature>_service.py`.
3. Add a route module in `app/api/v1/routes/<feature>.py` that calls the service.
4. Register it in `app/api/v1/router.py` with `api_router.include_router(...)`.

`main.py` never changes — it only ever includes the single aggregated `api_router`.
