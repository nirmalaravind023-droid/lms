# Python LMS Foundation

This repository contains a Python-first Learning Management System foundation built with:

- Django + PostgreSQL for the core web platform
- Django Channels for real-time chat
- `python-ffmpeg-video-streaming` + `webvtt-py` for HLS-ready video processing hooks
- HTML5 drag-and-drop patterns for course/module ordering
- Custom Django quiz engine for assessments
- Streamlit + Plotly + PyGWalker entry points for analytics

## Included Modules

- Multi-tenant organizations and departments
- Custom user model with admin, HR/manager, and learner roles
- Course, module, lesson, enrollment, and progress tracking
- Quiz categories, question bank, attempts, and grading workflow
- Certificate templates and issuance records
- Direct message conversations with Channels-based WebSockets
- Admin and department dashboards

## Quick Start

1. Create a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env`.
4. Run PostgreSQL and Redis locally or via `docker-compose`.
5. Run migrations and create a superuser.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## SQLite Smoke Test

If you want to boot the project before PostgreSQL is ready, set `DATABASE_ENGINE=sqlite` in `.env` and run:

```bash
python manage.py migrate
python manage.py runserver
```

This is useful for local validation, while PostgreSQL remains the recommended production database.

## Streamlit Analytics

The Streamlit dashboard lives at `streamlit_dashboard/app.py`.

## Important Note

This is a strong project foundation with the core domain, routing, templates, services, and app boundaries in place. Production hardening, migrations, polished UI, and end-to-end workflows should be extended iteratively.
