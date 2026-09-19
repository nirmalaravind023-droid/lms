# Troubleshooting

## Django cannot import a dependency

Activate the repository virtual environment and reinstall dependencies:

```bash
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

## Migrations or database errors

Confirm the intended `DATABASE_ENGINE` in `.env`. For SQLite, run `python manage.py migrate`. For PostgreSQL, ensure the `POSTGRES_*` values match the running service before migrating.

## Static calendar is stale

After modifying `frontend/src/calendar-board.jsx`, run `npm ci` and `npm run build:calendar`. The output is `static/js/react/calendar-board.js`.

## Docker cannot connect to a service

Use `docker compose config` to inspect the resolved configuration, then verify that ports 8000, 8501, 5432, and 6379 are available. The Compose setup is for development and bind-mounts the repository.

## Full tests fail

Consult [known-issues.md](known-issues.md). Seven existing failures are documented there; do not mask them by deleting tests or migrations.
