# Next-Gen LMS Stack Migration Plan

User-facing note: many LMS screens now use the word `Section` even where backend migration notes still use `Course`.

## Goal

Move the current LMS from the existing Django monolith toward this target stack:

- Frontend: React + TypeScript, Tailwind CSS, Video.js, `react-beautiful-dnd`, FullCalendar, `socket.io-client`
- Backend: Node.js + NestJS (preferred) or Express, REST/GraphQL, Socket.io, Bull + Redis
- Database: PostgreSQL + TimescaleDB, Redis
- Search: Elasticsearch
- Media: AWS S3 + CloudFront, FFmpeg or AWS MediaConvert, optional Mux
- Analytics: TimescaleDB continuous aggregates, Superset or custom React charts
- Deployment: Docker, Kubernetes/EKS, GitHub Actions, ElastiCache
- Monitoring: Prometheus + Grafana, Sentry
- Communication: SendGrid + Socket.io

This is not a one-file upgrade. It is a platform migration.

## Recommendation

Use **strangler migration**, not full rewrite in one step.

Why:

- the current LMS already has working course, quiz, calendar, messaging, analytics, and HR flows
- replacing everything at once will break user flows and slow delivery
- we can move module by module while keeping the current system live

## Recommended Architecture

### Frontend

Create a separate frontend app:

- `frontend/`
- React + TypeScript
- Tailwind CSS
- React Router
- TanStack Query for API state
- FullCalendar for calendar UI
- Video.js for lesson playback
- `@hello-pangea/dnd` recommended instead of `react-beautiful-dnd`

Note:

- `react-beautiful-dnd` is archived. For a production LMS, `@hello-pangea/dnd` is the safer drop-in path.

### Backend

Create a separate API service:

- `services/api/`
- NestJS
- REST first, GraphQL optional later
- Socket.io gateway for real-time messaging and notifications
- BullMQ + Redis for background jobs

Suggested NestJS modules:

- `auth`
- `users`
- `organizations`
- `courses`
- `modules`
- `lessons`
- `assessments`
- `calendar`
- `messaging`
- `notifications`
- `certificates`
- `analytics`
- `search`
- `media`

### Data

- PostgreSQL as primary database
- TimescaleDB extension for analytics/time-series tables
- Redis for:
  - cache
  - Socket.io adapter
  - queues
  - rate limiting
- Elasticsearch for global search

### Media

- upload raw files to S3
- distribute through CloudFront
- process video using:
  - FFmpeg worker
  - or AWS MediaConvert
- optional Mux for managed streaming and analytics

## How Current LMS Maps To New Services

### Courses

Current:

- Django models: `Course`, `Module`, `Lesson`, `Enrollment`, `LessonProgress`

New service:

- NestJS `courses` module
- PostgreSQL tables:
  - `courses`
  - `course_modules`
  - `course_lessons`
  - `course_assignments`
  - `enrollments`
  - `lesson_progress`

Frontend:

- React course library
- lesson reader/video page
- drag-drop builder for HR/admin

### Assessments

Current:

- Django quiz models and builder flow

New service:

- NestJS `assessments` module
- PostgreSQL tables:
  - `quizzes`
  - `quiz_questions`
  - `quiz_choices`
  - `quiz_assignments`
  - `quiz_attempts`
  - `quiz_answers`

Frontend:

- React quiz builder
- timed quiz runner
- HR grading and analytics view

### Calendar

Current:

- Django calendar board + holiday support

New service:

- NestJS `calendar` module
- FullCalendar frontend
- holiday ingestion job
- company calendar + learner calendar + department overlays

Frontend:

- FullCalendar month/week/day
- holiday calendar toggles
- learner task feed

### Messaging

Current:

- Django conversation/message models

New service:

- NestJS `messaging` module
- Socket.io real-time events
- Redis adapter for multi-instance delivery

Frontend:

- React inbox
- live thread updates
- unread counts

### Search

Current:

- DB-based unified search fallback

New service:

- NestJS `search` module
- Elasticsearch index documents for:
  - users
  - courses
  - modules
  - lessons
  - quizzes
  - conversations
  - messages
  - certificates
  - calendar items

Index shape:

```json
{
  "id": "course:123",
  "company_id": "uuid",
  "category": "course",
  "title": "Python Basics",
  "subtitle": "IT Department",
  "body": "Course description text",
  "meta": "Published",
  "url": "/courses/python-basics"
}
```

### Analytics

Current:

- dashboard metrics from relational tables

New service:

- operational data in Postgres
- time-series events in TimescaleDB
- continuous aggregates for:
  - lesson activity by day
  - quiz attempts by day
  - suspicious events by day
  - reading speed trends
  - completion trends by department

Frontend:

- custom React charts or Superset embed

## Migration Phases

### Phase 1: Foundation

- create `frontend/` React app
- create `services/api/` NestJS app
- move auth to JWT/session API
- move PostgreSQL as shared source of truth
- add Redis
- keep Django running during transition

### Phase 2: Search + Shell

- expose global search API from NestJS
- create Elasticsearch indexers
- move top search bar to React shell
- keep old pages embedded or linked

### Phase 3: Messaging + Notifications

- move inbox and live chat to Socket.io
- Redis adapter for real-time scale
- SendGrid email notifications

### Phase 4: Calendar

- replace current heavy calendar with FullCalendar
- holiday calendars as overlays
- company + learner task visibility

### Phase 5: Courses + Media

- move course library and lesson player
- S3 + CloudFront
- video processing job queue
- Video.js player with progress tracking

### Phase 6: Assessments

- move quiz builder and learner attempt flow
- grading workers
- analytics events into TimescaleDB

### Phase 7: Analytics + Reporting

- continuous aggregates
- Superset or custom dashboards

### Phase 8: Cutover

- route all UI to React
- Django retired after parity

## API Style

Recommendation:

- REST first
- GraphQL only for analytics/reporting explorer use cases later

Why:

- easier migration from current Django views
- easier testing
- simpler permission boundaries

## Suggested Monorepo Layout

```text
frontend/
services/
  api/
  worker/
packages/
  ui/
  types/
  config/
infra/
  docker/
  k8s/
  terraform/
```

## Infrastructure

### Docker

Containers:

- `frontend`
- `api`
- `worker`
- `postgres`
- `redis`
- `elasticsearch`
- optional `superset`

### Kubernetes / AWS

- EKS
- RDS PostgreSQL
- ElastiCache Redis
- OpenSearch or Elasticsearch managed service
- S3 + CloudFront
- MediaConvert or ECS worker for FFmpeg

## CI/CD

GitHub Actions pipelines:

- lint
- test
- build frontend
- build api
- build worker
- Docker image publish
- deploy to EKS

## Monitoring

- Prometheus for service metrics
- Grafana dashboards
- Sentry for frontend + backend errors

Track:

- API latency
- websocket connection count
- queue lag
- failed jobs
- video processing time
- Elasticsearch query latency

## What We Can Actually Build Next

If we start now, the most realistic order is:

1. React frontend shell
2. NestJS API skeleton
3. unified search in Elasticsearch
4. FullCalendar replacement for current heavy calendar
5. Socket.io messaging

## Best Immediate Next Task

The current LMS already shows a heavy calendar bundle and growing UI complexity.

So the best first implementation step is:

**build a new React + FullCalendar calendar module and connect it to a lightweight API**

That gives immediate value:

- faster UI
- cleaner month/week/day views
- holiday overlays
- easier future migration

## Honest Note

I have not migrated the whole LMS to this stack in this turn.

What I did here is define the correct migration target and the safest implementation order for this codebase.

If you want, next I can start the actual implementation with one of these:

1. scaffold `frontend/` React + TypeScript + Tailwind app
2. scaffold `services/api/` NestJS app
3. replace the current calendar with FullCalendar first
4. add Elasticsearch indexing for the new global search
