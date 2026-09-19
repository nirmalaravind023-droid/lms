# Python LMS Foundation

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django 6.0](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI configured](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows/ci.yml)

Python LMS Foundation is a Django-based learning-management-system foundation for organizations that need courses, assessments, learner progress, certificates, and internal messaging in one application.

> Project status: active foundation. The application is suitable for local development and evaluation; production deployment needs environment-specific hardening.

## Project status

The Django LMS is actively maintained as a foundation project. The server-rendered application and React calendar bundle are the supported implementation. The Vite frontend in `frontend/` and the Streamlit dashboard are experimental: the Vite interface is not served by Django, and the Streamlit dashboard currently uses sample data. Contributions are welcome, especially for the issues labelled `good first issue` or `help wanted`.

## Features

- Organizations, departments, and role-aware user accounts
- Email, username, or phone-number authentication
- Course, module, lesson, enrollment, and progress management
- Video, PDF, article, and external-link lessons, including subtitle tooling
- Quizzes, assignments, attempts, review, and scoring
- Certificates and completion records
- Course comments, notifications, and real-time direct messaging
- Calendar events and an interactive React calendar board
- Django analytics pages and a separate Streamlit analytics demo

## Technology

- Python, Django, Django Channels, Daphne
- SQLite for a simple local setup; PostgreSQL is supported through environment configuration
- Redis-compatible channel layer support
- Server-rendered Django templates with JavaScript and CSS assets
- React and esbuild for the integrated calendar bundle
- Streamlit, Plotly, and PyGWalker for the analytics demo
- Docker Compose for local multi-service development

## Architecture

The primary application is a Django monolith. Domain functionality lives in `apps/`; `lms_portal/` contains project configuration and entry points. Django serves templates and static assets. The calendar source is bundled from `frontend/src/calendar-board.jsx` to `static/js/react/calendar-board.js`.

```text
apps/                 Django domain apps
lms_portal/           Django settings, URL map, ASGI, and WSGI
templates/            Shared Django templates
static/               CSS and browser JavaScript
frontend/             Calendar bundle source and Vite prototype
streamlit_dashboard/  Separate analytics demo
docs/                 Project documentation and plans
```

See [architecture](docs/architecture.md), [project structure](docs/project-structure.md), and [development guidance](CONTRIBUTING.md).

For a concise request and data-flow overview, see [Architecture Overview](docs/architecture-overview.md).

## Supported environments

| Component | Supported or validated version |
| --- | --- |
| Python | 3.12 (CI and Docker image); 3.13 was used for the latest local validation |
| Django | 6.0.8 |
| Node.js | 20 in CI; Node 24.18.0 validated locally |
| npm | 11.16.0 validated locally |
| Database | SQLite for local development; PostgreSQL 16 in Docker Compose |
| Redis | Redis 7 in Docker Compose, when `REDIS_URL` is configured |
| Operating systems | Windows PowerShell is documented; the Docker image runs on Linux |

## Prerequisites

- Python 3.12
- Node.js and npm (to rebuild the calendar bundle)
- Docker and Docker Compose (optional)
- PostgreSQL and Redis (optional for local development; supported by Docker Compose)

## Local setup

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/` after the server starts.

The sample environment uses SQLite. To use PostgreSQL, set `DATABASE_ENGINE` to a non-`sqlite` value and supply the `POSTGRES_*` variables listed in `.env.example`.

See [environment configuration](docs/environment.md) for every variable and safe development defaults.

### Demo/sample data

A migrated database has no users or courses yet. There is no bundled fixture set; create a working account with the built-in management command instead:

```bash
python manage.py create_test_admin --email admin@example.com --password Admin@12345
```

This creates (or updates) a super-admin account you can use to sign in and create organizations, courses, and enrollments through the app itself. `--email`, `--password`, and `--username` are all optional and default to the values shown above.

## Frontend calendar bundle

The Django calendar page depends on the checked-in bundle at `static/js/react/calendar-board.js`. Rebuild it after changing `frontend/src/calendar-board.jsx`:

```bash
npm ci
npm run build:calendar
```

`frontend/` also contains an unintegrated Vite prototype. It is not the frontend served by Django today.

## Streamlit analytics demo

The Streamlit app currently displays sample analytics data. Run it separately:

```bash
streamlit run streamlit_dashboard/app.py
```

## Docker Compose

```bash
docker compose up --build
```

This starts the Django application, PostgreSQL, Redis, and Streamlit services. The Compose configuration is intended for local development and currently uses Django's development server.

## Validation and tests

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check
```

Critical Python static checks and calendar-source linting are configured with Ruff and ESLint. The existing codebase has broader style/import cleanup remaining, which is intentionally outside this repository-maintenance change:

```bash
pip install -r requirements-dev.txt
ruff check .
npm run lint:frontend
```

The current suite has seven known failures that predate this open-source cleanup. See [Known Issues](docs/known-issues.md) before treating a failure as a regression.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. To report a vulnerability privately, follow [SECURITY.md](SECURITY.md). The project is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Roadmap and documentation

- [Architecture](docs/architecture.md)
- [Backup and restore policy](docs/backup-and-restore.md)
- [Media storage policy](docs/media-storage-policy.md)
- [Project structure guide](docs/project-structure.md)
- [Current roadmap](docs/roadmap.md)
- [Known issues](docs/known-issues.md)
- [Troubleshooting](docs/troubleshooting.md)

## Screenshots

Screenshots and a demo recording are not yet available. Contributions that add anonymized, reproducible captures of the dashboard, course workspace, assessments, or calendar are welcome.

## License

MIT — see [LICENSE](LICENSE).
