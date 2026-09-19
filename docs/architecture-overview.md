# Architecture overview

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
