# Architecture overview

This page describes the active implementation in this repository. Treat it as the current source of truth when it conflicts with older planning documents.

The current system is a Django monolith. It is not a NestJS service, not a microservice system, and not backed by object storage by default.

```text
Browser
  │ HTTP / WebSocket
  ▼
Django: lms_portal
  ├── apps/accounts        authentication and user lifecycle
  ├── apps/organizations   companies and departments
  ├── apps/courses         courses, lessons, progress, calendar, uploads
  ├── apps/assessments     quizzes, assignments, attempts, scoring
  ├── apps/certificates    completion certificates
  ├── apps/messaging       conversations and Channels consumers
  ├── apps/analytics       server-rendered dashboards
  └── apps/common          shared models, search, pagination, utilities
  │
  ├── SQLite (local) or PostgreSQL
  ├── Redis channel layer (when REDIS_URL is configured)
  ├── templates/ and static/
  └── media/ local uploads

frontend/src/calendar-board.jsx ──esbuild──> static/js/react/calendar-board.js
streamlit_dashboard/app.py ──> standalone sample-data analytics interface
```

## Main flows

1. Browser requests are routed by `lms_portal/urls.py` to app views, which apply authentication and organization-aware access checks before reading or writing models.
2. Server-rendered templates load CSS and JavaScript from `static/`; the calendar template loads the compiled React calendar bundle.
3. Authenticated chat participants connect through ASGI to `apps.messaging` WebSocket consumers, which check conversation membership before joining a room.
4. Course uploads are stored beneath `MEDIA_ROOT`; optional subtitle and HLS helpers process lesson media.

The Vite frontend and Streamlit dashboard are not part of the primary Django request flow today.

## Current infrastructure boundaries

| Area | Active implementation |
| --- | --- |
| Backend | Django apps inside `apps/` |
| HTTP serving | Django views and templates |
| WebSockets | Django Channels chat consumer |
| Database | SQLite locally by default; PostgreSQL supported by settings and Docker Compose |
| Redis | Optional Channels layer when `REDIS_URL` is configured |
| Media | Local Django `MEDIA_ROOT`; production object storage is not implemented yet |
| Backups | Policy documented; automated backup job is not implemented yet |
| Frontend | Server-rendered templates, static JavaScript, and a bundled React calendar |
| Vite frontend | Prototype only; not served as the main Django frontend |
| Streamlit | Standalone analytics dashboard |
| Workers | No Celery app or worker process currently exists |
