# Contributing to NexusIQ

Thanks for your interest in improving NexusIQ. This guide covers local setup,
the test workflow, and the conventions the project follows.

## Prerequisites

- **Python 3.13+** (the backend uses `argon2-cffi` and features removed-in-3.13
  stdlib is deliberately avoided)
- **Node.js 20+** and npm
- **PostgreSQL** reachable on `localhost:5433` (see `docs/SETUP.md`)

## Getting started

```bash
# 1. Backend env
cp backend/.env.example backend/.env        # then fill in the values you need

# 2. Frontend env
cp frontend/.env.local.example frontend/.env.local

# 3. Start the full stack (Postgres + backend :8001 + frontend :3000)
./scripts/dev.sh
./scripts/status.sh    # health check
./scripts/stop.sh      # stop
```

Full environment setup, including how the helper scripts manage Postgres, is in
[`docs/SETUP.md`](docs/SETUP.md). Architecture is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Running the checks

```bash
# Backend tests (pytest)
cd backend && .venv/bin/pytest -q

# Frontend type-check + production build
cd frontend && npx tsc --noEmit && npm run build
```

A change to product code is not "done" until the relevant tests pass **and** the
behaviour has been exercised in the running app.

## Code style

- **Python**: linted with [ruff](https://docs.astral.sh/ruff/) (config in
  `backend/ruff.toml`). Install the pre-commit hooks below so lint + secret
  scanning run automatically.
- **TypeScript/React**: keep changes consistent with the surrounding code; run
  `npx tsc --noEmit` before pushing.
- **Comments/code identifiers**: English. **User-facing UI strings**: Azerbaijani,
  and must be added to all four languages (AZ/EN/RU/TR) in `frontend/src/lib/i18n.tsx`.
- No dead code. Remove what you replace.

### Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

This wires up trailing-whitespace/EOF fixers, `gitleaks` (secret scanning), and
`ruff` on staged backend files.

## Commit & PR conventions

- Commit messages follow a `type(scope): summary` shape, e.g.
  `fix(security): …`, `feat(auth): …`, `docs: …`. Summaries in the repo are
  written in Azerbaijani; keep that consistent.
- Branch off `main` (`feat/…`, `fix/…`). Open one focused pull request per change
  and fill in the PR template.
- **Never commit secrets.** `.env` files are git-ignored; only `*.env.example`
  templates are tracked.

## Reporting bugs & vulnerabilities

- Functional bugs → open an issue using the bug template.
- Security vulnerabilities → **do not** open a public issue; follow
  [`SECURITY.md`](SECURITY.md).
