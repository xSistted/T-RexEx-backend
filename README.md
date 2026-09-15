# T-RexX API

FastAPI backend with a layered structure that keeps HTTP, business logic, and data models separate.

## Project structure

```
T-RexEx-backend/
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

## Run locally (without Docker)

```powershell
uvicorn app.main:app --reload
```

- API root: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health: http://127.0.0.1:8000/api/v1/health

## Run with Docker

This repo's `docker-compose.yml` covers **backend development only**. Production is built and run by
the outer compose file that combines this service with the frontend — see [Production](#production).

### Development (auto-reload)

```bash
docker compose up --build
```

- API root: http://localhost:8000/
- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

Your local code is bind-mounted into the container, so editing anything under `app/` restarts
uvicorn automatically — no image rebuild needed. (`WATCHFILES_FORCE_POLLING=true` is set in
`docker-compose.yml` because file-system events don't propagate across bind mounts on
macOS/Windows, so `--reload` would never fire without polling.)

Other common commands:

```bash
docker compose up -d --build         # run in the background
docker compose logs -f backend       # follow logs
docker compose down                  # stop and remove containers
docker compose exec backend sh       # open a shell in the container
docker compose exec backend pytest   # run the tests
```

Settings come from `app/core/config.py` defaults, overridden by `.env` if you create one
(`cp .env.example .env`). The compose file treats `.env` as optional, so the stack runs without it.

> If you change `requirements.txt` or `requirements-dev.txt`, rebuild the image:
> `docker compose up --build --force-recreate`

### Production

Production isn't run from this repo's compose file, but the image is built here. The `Dockerfile`'s
`prod` target installs only `requirements.txt` (no test/lint tooling), runs as a non-root `appuser`,
and starts uvicorn without `--reload`.

The outer compose points at this directory:

```yaml
# outer docker-compose.yml, alongside the frontend service
services:
  backend:
    build:
      context: ./T-RexEx-backend
      target: prod
    expose:
      - "8000"          # internal only; the frontend's nginx proxies to it
```

Build targets in `Dockerfile`:

| Target | What it does |
| --- | --- |
| `dev` | uvicorn with `--reload`, installs `requirements-dev.txt`, port 8000 |
| `prod` | uvicorn without reload, runtime deps only, non-root, port 8000 |

## Adding a new feature (the pattern)

1. Add request/response models in `app/schemas/<feature>.py`.
2. Add business logic in `app/services/<feature>_service.py`.
3. Add a route module in `app/api/v1/routes/<feature>.py` that calls the service.
4. Register it in `app/api/v1/router.py` with `api_router.include_router(...)`.

`main.py` never changes — it only ever includes the single aggregated `api_router`.
