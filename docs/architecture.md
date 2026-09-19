# LMS Architecture & Implementation Roadmap

User-facing note: many LMS screens now use the word `Section` even where backend architecture notes still use `Course`.

## Overview
A comprehensive Learning Management System with multi-tenant support, role-based access, course delivery, assessments, analytics, and real-time communication.

---

## 0. EXECUTIVE RECOMMENDATION

If you are building this LMS from scratch, the best path is:

1. Build **one web platform** with **three role-based portals**
   - `Super Admin / Company Admin`
   - `Learner`
   - `HR / Department Manager / Client Viewer`
2. Start with a **modular monolith**, not microservices
   - one backend app
   - one frontend app
   - one primary relational database
   - queue + object storage for heavy jobs
3. Use **TypeScript end-to-end**
   - frontend: React + TypeScript
   - backend: NestJS + TypeScript
   - shared DTO/types where useful
4. Use **PostgreSQL as the system of record**
   - relational data fits LMS requirements best
   - supports reporting, joins, auditing, and multi-tenant data well
5. Add advanced systems only when needed
   - start without Elasticsearch
   - start without Kubernetes
   - start without GraphQL unless your frontend really needs it

### Final Stack Choice

| Layer | Recommended Choice | Why |
|------|------|------|
| Frontend | React + TypeScript + Vite | Fast developer experience, strong ecosystem, good admin dashboard support |
| UI | Tailwind CSS + shadcn/ui | Fast internal-product UI development |
| State | Zustand + TanStack Query | Simpler than Redux for this use case |
| Backend | Node.js + NestJS + TypeScript | Clean modules, RBAC, validation, scaling path |
| API | REST first | Easier for LMS CRUD, reporting, admin tooling |
| Database | PostgreSQL | Best fit for tenants, users, enrollments, progress, quizzes, audit logs |
| Cache / Queue | Redis + BullMQ | Background jobs, cache, notifications |
| ORM | Prisma | Faster schema iteration and developer productivity |
| Storage | S3-compatible object storage | Videos, PDFs, certificates, thumbnails |
| Video | FFmpeg + HLS | Needed for subtitles, adaptive streaming, audio tracks |
| Realtime | Socket.io | Messaging, alerts, live progress updates |
| Search | PostgreSQL full-text first, OpenSearch later | Avoid early complexity |
| Analytics | PostgreSQL aggregates + Metabase | Faster to launch than a custom BI system |
| DevOps | Docker Compose first, Kubernetes later | Lower cost and complexity for v1 |

### What To Build In V1 vs Later

**Build in V1**
- company login and tenant isolation
- admin portal
- learner portal
- department allocation
- course/module/submodule builder
- articles, PDFs, videos
- mandatory reading with completion checkbox
- quizzes and assignments
- learner progress tracking
- certificates
- analytics dashboard
- calendar
- direct messaging

**Build in V2**
- auto subtitle generation
- automatic audio translation / dubbing
- advanced recommendation engine
- large-scale search cluster
- custom dashboard designer for every admin
- multi-region deployment

### Architecture Principles

- Keep tenant isolation explicit with `company_id` on every major business table.
- Separate `course structure` from `learner progress` from `analytics events`.
- Store raw events for auditability, then derive dashboard metrics from aggregates.
- Treat video processing and certificate generation as asynchronous jobs.
- Design every admin action to be auditable.

---

## 0.1 FEATURE-TO-MODULE MAPPING

| Business Need | Technical Module |
|------|------|
| Company-specific login | Auth + Tenant Context |
| Admin creates courses | Course Authoring |
| Course has modules and lessons | Course Structure |
| Video with subtitles like YouTube/Udemy | Media Delivery |
| Audio language switching | HLS multi-audio pipeline |
| Mandatory reading checkbox | Content Completion |
| Quiz by department like electrical/civil | Assessment + Department Allocation |
| Admin sees completion, watch time, score | Progress + Analytics |
| HR/admin messages learner | Messaging |
| Department color calendar | Scheduling |
| Certificate after module/course | Certificate Engine |
| Admin edits certificate anytime | Certificate Template Manager |
| Who did not start / did not complete / not evaluated | Reporting & Compliance |

---

## 0.2 ROLE-BASED WORKFLOW (ADMIN, HR/MANAGER, LEARNER)

### Primary Roles

| Role | Main Responsibility |
|------|------|
| Super Admin / Company Admin | Platform configuration, user management, course creation, analytics, certificates, compliance |
| HR / Department Manager | Department-level allocation, follow-up, learner monitoring, messaging, compliance review |
| Learner | Consume content, complete modules, take assessments, earn certificates |

### A. Learner Workflow (End-to-End)

| Stage | Learner Experience | System / Admin Side Effect |
|------|------|------|
| 1. Account Access | Learner receives invite or account from company admin | User record created with `company_id`, `department_id`, role, and login method |
| 2. Login | Learner logs in using company portal / company code / email | Auth service validates tenant and role, creates session/JWT |
| 3. Dashboard | Learner sees assigned courses, due dates, progress %, unread messages, certificates | Dashboard API pulls enrollments, progress summaries, notifications |
| 4. Open Course | Learner opens one course and sees modules, lessons, status, prerequisites | System checks enrollment, publish state, prerequisite rules |
| 5. Consume Content | Learner watches video, reads article, downloads PDF, marks mandatory reading checkbox | Progress events are stored: started, paused, resumed, completed, time spent |
| 6. Media Controls | Learner changes subtitle language or audio language | Player loads HLS text tracks / audio tracks and logs preferences |
| 7. Module Completion | Learner finishes required lessons in a module | Module status changes from `not_started` to `in_progress` to `completed` |
| 8. Assessment | Learner takes quiz / assignment for the module | Attempt record created, timer tracked, answers saved, grading triggered |
| 9. Result | Learner sees score, pass/fail, feedback, retry rules | Auto-grade runs for objective questions, manual grading pending if subjective |
| 10. Course Completion | Learner completes all mandatory modules and assessments | Course completion logic runs and eligibility for certificate is checked |
| 11. Certificate | Learner downloads certificate if rules are satisfied | PDF/certificate job generated and stored in object storage |
| 12. Communication | Learner receives reminders or messages from HR/admin | Notifications stored, unread count updated, message thread preserved |

### Learner Screen Flow

`Login -> Dashboard -> Course List -> Course Detail -> Lesson Player/Reader -> Quiz/Assignment -> Result -> Certificate -> Messages -> Calendar`

### Learner Statuses

| Entity | Status Flow |
|------|------|
| Course Enrollment | `assigned -> started -> in_progress -> completed -> overdue -> archived` |
| Module | `not_started -> in_progress -> completed` |
| Lesson / Submodule | `locked -> available -> started -> completed` |
| Quiz Attempt | `not_started -> in_progress -> submitted -> graded -> passed/failed` |
| Certificate | `not_eligible -> eligible -> issued -> revoked -> reissued` |

---

### B. Admin Workflow (End-to-End)

| Stage | Admin Action | System Behavior |
|------|------|------|
| 1. Tenant Setup | Create company profile, branding, login rules, departments | Company, department, settings tables initialized |
| 2. User Management | Create/import admins, HR, learners, assign departments | User records created, invitations sent, audit log captured |
| 3. Course Authoring | Create course, modules, lessons, prerequisites, sequence | Course tree saved with draft/published versions |
| 4. Content Upload | Upload videos, PDFs, articles, mandatory reading materials | Files stored, video jobs queued, content metadata saved |
| 5. Assessment Setup | Build quizzes/assignments by category like civil/electrical | Assessment, question bank, rules, passing score stored |
| 6. Department Allocation | Assign course/assessment to departments, users, or batches | Enrollment and assignment records created |
| 7. Calendar Planning | Schedule due dates, quiz windows, assignment deadlines, color-code by department | Calendar events created and pushed to dashboards |
| 8. Monitoring | View completion %, avg time spent, quiz score, not started, not evaluated | Analytics queries aggregate progress and assessment data |
| 9. Intervention | Message learner or HR, reassign modules, unlock retries, extend deadlines | Notifications/events created and tracked |
| 10. Certificate Management | Design or modify certificate template, preview, issue or revoke | Template versions stored, issuance/revocation audited |
| 11. Reporting | Export learner/department compliance reports | CSV/PDF/report jobs generated |

### Admin Screen Flow

`Admin Login -> Dashboard -> Users/Departments -> Course Builder -> Assessment Builder -> Allocation -> Calendar -> Analytics -> Messages -> Certificates -> Reports`

### Admin Operational Workflow

1. Create company structure.
2. Add departments like Civil, Electrical, Mechanical.
3. Add users and map them to department and role.
4. Build course and split it into modules and submodules.
5. Attach content types:
   - video
   - article
   - PDF
   - mandatory reading
   - quiz
   - assignment
6. Publish course.
7. Allocate course to a department or selected learners.
8. Set due date and evaluation rules.
9. Track progress and intervene where learners are stuck.
10. Generate certificates and compliance reports.

---

### C. HR / Department Manager Workflow (End-to-End)

Assumption: HR/Manager is **not** a full platform admin. This role is limited to assigned departments or business units.

| Stage | HR / Manager Action | System Scope |
|------|------|------|
| 1. Login | HR logs in and sees only managed departments | RBAC + department scoping applied |
| 2. Department Dashboard | Review learners by status: not started, in progress, completed, not evaluated, overdue | Department aggregate API returns scoped metrics |
| 3. Assignment View | See which courses/quizzes are assigned to the team | Enrollment and course-assignment data filtered by department |
| 4. Learner Drilldown | Open one learner profile to inspect module completion, watch time, score, certificates | Detailed learner analytics displayed |
| 5. Follow-up | Send reminder or direct message to learner | Message stored and visible in admin audit context |
| 6. Escalation | Flag learner to admin / training team for intervention | Workflow flag/comment created |
| 7. Compliance Review | Check mandatory training completion by due date | Compliance engine returns due/overdue/non-compliant learners |
| 8. Report Export | Export department-wise performance and compliance | Department-scoped exports generated |

### HR / Manager Screen Flow

`Manager Login -> Department Dashboard -> Team Progress -> Learner Detail -> Messages -> Calendar -> Department Reports`

### HR / Manager KPIs

- department completion rate
- average quiz score
- average time spent per module
- overdue mandatory modules
- not evaluated learners
- certificate completion count
- top blocked modules in the department

---

## 0.3 PERMISSION MATRIX

| Capability | Admin | HR / Manager | Learner |
|------|------|------|------|
| Create company / tenant | Yes | No | No |
| Create departments | Yes | Limited / Optional | No |
| Create users | Yes | Limited / Optional | No |
| Create course | Yes | Optional if allowed | No |
| Publish/unpublish course | Yes | No | No |
| Allocate course to department | Yes | Yes (scoped) | No |
| Upload content | Yes | Optional if allowed | No |
| Create assessment | Yes | Optional if allowed | No |
| Grade subjective answers | Yes | Yes (scoped) | No |
| View all analytics | Yes | No | No |
| View department analytics | Yes | Yes | No |
| View own analytics | Yes | Yes | Yes |
| Message learner | Yes | Yes | Yes |
| Edit certificate template | Yes | No | No |
| Issue / revoke certificate | Yes | Optional approval flow | No |
| Export reports | Yes | Yes (scoped) | Own only |

---

## 0.4 CROSS-ROLE BUSINESS WORKFLOW

### Workflow 1: Course Creation to Completion

1. Admin creates course.
2. Admin adds modules and lessons.
3. Admin uploads videos, articles, PDFs, and mandatory readings.
4. Admin adds quiz/assignment rules.
5. Admin publishes course.
6. Admin or HR assigns course to department or learners.
7. Learner receives notification and sees course in dashboard.
8. Learner completes lessons and assessments.
9. HR monitors progress and follows up with delayed learners.
10. System marks course complete when all mandatory rules are satisfied.
11. Certificate engine generates certificate.
12. Admin and HR see completion in analytics and compliance dashboards.

### Workflow 2: Mandatory Compliance Tracking

1. Admin marks course or module as mandatory for a department.
2. Due dates are pushed to department calendar.
3. Learners start course or remain in `not_started`.
4. System tracks time spent, quiz attempts, and completion.
5. HR dashboard highlights overdue or not evaluated learners.
6. HR sends reminders or escalates to admin.
7. Admin can extend due dates, unlock retries, or reassign content.
8. Final compliance report is exported for audit.

### Workflow 3: Assessment and Evaluation

1. Admin creates assessment by category such as Civil or Electrical.
2. Assessment is attached to module or course.
3. Learner submits answers.
4. Objective questions are auto-graded.
5. Subjective questions move to `pending_evaluation`.
6. Admin or manager grades manually.
7. Final score updates learner dashboard, course progress, and department analytics.

### Workflow 4: Certificate Lifecycle

1. Admin designs certificate template.
2. System checks completion and passing rules.
3. Certificate job generates file.
4. Learner downloads certificate.
5. Admin can later update template for future issuance.
6. Previously issued certificates remain versioned and auditable.
7. If needed, certificate can be revoked and reissued.

### Workflow 5: Communication Workflow

1. System detects trigger:
   - new assignment
   - overdue module
   - failed quiz
   - certificate issued
2. Notification is created.
3. Admin or HR sends direct message.
4. Learner replies in thread.
5. Message thread remains visible to authorized admin / HR for recordkeeping.

---

## 0.5 DEVELOPER IMPLEMENTATION VIEW OF THE WORKFLOW

### Core Backend Modules Needed

- `auth`
- `tenants`
- `users`
- `departments`
- `courses`
- `course-content`
- `media-processing`
- `enrollments`
- `progress`
- `assessments`
- `grading`
- `analytics`
- `certificates`
- `calendar`
- `notifications`
- `messaging`
- `audit-logs`

### Core Database Areas

| Domain | Main Tables |
|------|------|
| Tenant & Identity | `companies`, `departments`, `users`, `roles`, `user_department_map` |
| Learning Structure | `courses`, `modules`, `submodules`, `content_blocks`, `course_versions` |
| Assignment | `course_assignments`, `assessment_assignments`, `enrollments` |
| Learning Activity | `user_progress`, `activity_logs`, `content_events`, `video_watch_segments` |
| Assessments | `assessments`, `questions`, `question_options`, `quiz_attempts`, `quiz_answers`, `manual_reviews` |
| Communication | `message_threads`, `messages`, `notifications` |
| Planning | `calendar_events`, `deadlines` |
| Certification | `certificate_templates`, `certificate_template_versions`, `certificates` |
| Reporting | `analytics_events`, `daily_department_metrics`, `daily_course_metrics` |

### Frontend Portals

| Portal | Main Pages |
|------|------|
| Learner Portal | Dashboard, Course Player, Quiz, Calendar, Messages, Certificates, Profile |
| Admin Portal | Dashboard, User Management, Department Management, Course Builder, Quiz Builder, Analytics, Calendar, Messaging, Certificates, Reports |
| HR / Manager Portal | Department Dashboard, Team Progress, Learner Detail, Calendar, Messages, Reports |

### Event Triggers To Implement

- `USER_INVITED`
- `COURSE_ASSIGNED`
- `LESSON_STARTED`
- `LESSON_COMPLETED`
- `QUIZ_SUBMITTED`
- `QUIZ_GRADED`
- `COURSE_COMPLETED`
- `CERTIFICATE_ISSUED`
- `DEADLINE_MISSED`
- `MESSAGE_SENT`
- `REMINDER_TRIGGERED`

---

## 1. TECH STACK BREAKDOWN (Developer POV)

### Frontend Layer
```
React 18 + TypeScript
├── State Management: Redux Toolkit or Zustand
├── UI Components: Tailwind CSS + Shadcn/ui
├── Video Player: Video.js (HLS support, subtitles, multi-audio)
├── Drag & Drop: dnd-kit (course builder, quiz builder)
├── Calendar: FullCalendar (department schedules, deadlines)
├── Forms: React Hook Form + Zod (validation)
├── Real-time: Socket.io-client
├── Charts: Recharts or Chart.js (analytics dashboard)
├── Testing: Jest + React Testing Library
└── Build: Vite (faster than CRA)
```

### Backend Layer
```
Node.js 20+ LTS + TypeScript
├── Framework: NestJS
│   ├── Advantage: Built-in dependency injection, modular architecture
│   ├── Modules: Auth, Users, Courses, Modules, Assessments, Analytics, Messaging
│   └── Pipes/Guards: JWT auth, role-based access control (RBAC)
├── Real-time: Socket.io (direct messaging, progress updates)
├── Task Queue: Bull + Redis (video transcoding, email, report generation)
├── Validation: class-validator + class-transformer
├── Logging: Winston
├── Testing: Jest + Supertest
└── API Documentation: Swagger/OpenAPI
```

### Database Layer
```
PostgreSQL 15+ (Primary)
├── TimescaleDB Extension (time-series analytics)
├── Partitioning: By company_id or date for logs
├── Key Tables:
│   ├── Users (learners, admins, hr)
│   ├── Companies (tenants)
│   ├── Courses, Modules, Submodules
│   ├── Module Content (articles, videos, readings)
│   ├── Assessments (quizzes, assignments)
│   ├── UserProgress (tracking, watch time, completion)
│   ├── Certificates
│   ├── Messages, MessageThreads
│   ├── Analytics Events
│   └── Indexes on: user_id, course_id, company_id, created_at
└── Migrations: TypeORM or Prisma (optional GraphQL support)

Redis (Cache + Queue)
├── Cache: User sessions, course metadata, hot data
├── Queue (Bull): Video processing, email, PDF generation
└── Real-time: Socket.io adapter (sticky sessions for scaling)
```

### Object Storage
```
Garage (Self-hosted S3 API)
├── Buckets:
│   ├── videos/raw (original uploads)
│   ├── videos/processed (HLS chunks)
│   ├── thumbnails
│   ├── certificates
│   ├── documents (articles, readings)
│   └── user-uploads (profile pics, etc)
├── CDN: CloudFront or CloudFlare (optional, depends on upload volume)
└── Fallback: Local filesystem for development
```

### Media Processing
```
FFmpeg (Video Transcoding)
├── Background Job (Bull Queue):
│   ├── Trigger: File uploaded to storage
│   ├── Process: MP4 → HLS (multiple bitrates: 480p, 720p, 1080p)
│   ├── Subtitles: Extract/convert to VTT format
│   ├── Audio: Multiple tracks (English, Spanish, etc)
│   └── Output: Stored in videos/processed bucket
├── Monitoring: Bull UI to track transcoding jobs
└── Error Handling: Retry logic, fallback quality
```

### Search Engine
```
Elasticsearch/OpenSearch
├── Indices:
│   ├── courses (course name, description)
│   ├── modules (module content)
│   ├── users (learner profiles)
│   └── documents (articles, readings)
├── Features: Full-text search, faceted filtering, autocomplete
└── Optional: Start without, add later if > 1000 courses
```

### Analytics & Reporting
```
TimescaleDB Continuous Aggregates
├── Hypertables:
│   ├── user_activity_logs
│   ├── module_watch_time
│   ├── quiz_attempts
│   └── certificate_issued
├── Pre-aggregated views: Hourly/daily summaries
└── Metabase (Dashboards)
    ├── Admin: Learner progress, quiz scores, time spent, completion rates
    ├── Department: Performance by dept, bottleneck analysis
    ├── Compliance: Certificate tracking, audit logs
    └── Custom: Drag-and-drop dashboard builder
```

### Communication
```
Real-time Messaging
├── Option 1: Socket.io (simpler for small-medium scale)
├── Option 2: Apache Kafka (if > 10K concurrent users)
└── Storage: PostgreSQL with indexing on (sender_id, receiver_id, created_at)

Email
├── Development: MailHog (local SMTP server)
├── Production: Unsend (open-source) or SendGrid
└── Templates: Handlebars for certificates, notifications
```

### Monitoring & Observability
```
Prometheus + Grafana
├── Metrics:
│   ├── API response times
│   ├── Database query performance
│   ├── Queue size (Bull)
│   ├── User sessions active
│   └── Error rates by endpoint
├── Alerts: Critical errors, high latency
└── Logs: Centralized logging (ELK or Loki)

Sentry (Error Tracking)
└── Frontend + Backend error monitoring
```

---

## 2. PHASED IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-3)
**Goal**: Set up infrastructure, auth, and basic admin/learner flows

1. **Project Setup**
   - [ ] Initialize NestJS project with TypeScript
   - [ ] Set up PostgreSQL & Prisma/TypeORM
   - [ ] Create Docker Compose for local dev (PostgreSQL, Redis, Garage, Metabase)
   - [ ] Initialize React + Vite frontend
   - [ ] Set up Git repo structure (monorepo or separate repos)

2. **Authentication & Authorization**
   - [ ] User registration (admin, learner, hr)
   - [ ] JWT auth with refresh tokens
   - [ ] Multi-tenancy (company_id in JWT)
   - [ ] Role-based access control (RBAC) middleware
   - [ ] Password reset & email verification

3. **Basic Admin Dashboard**
   - [ ] Admin login
   - [ ] User management (CRUD for learners)
   - [ ] Department management
   - [ ] Basic navigation UI

4. **Basic Learner Portal**
   - [ ] Learner login
   - [ ] View enrolled courses
   - [ ] Basic progress tracking UI

5. **Database Schema v1**
   - [ ] Users, Companies, Departments, Roles
   - [ ] Courses, Modules, Submodules (basic structure)
   - [ ] UserEnrollment, UserProgress
   - [ ] Create indexes on company_id, user_id, course_id

---

### Phase 2: Course Delivery (Weeks 4-6)
**Goal**: Content creation and learner progress tracking

1. **Course Builder (Admin)**
   - [ ] Drag-and-drop course structure editor (dnd-kit)
   - [ ] Add modules and submodules
   - [ ] Set prerequisites and sequencing
   - [ ] Publish/draft states

2. **Content Types**
   - [ ] Video module (upload MP4, store in Garage)
   - [ ] Article module (rich text editor - use Slate/TipTap)
   - [ ] PDF/document uploads
   - [ ] Mandatory readings (checkbox completion)
   - [ ] Resource links

3. **Video Processing Pipeline**
   - [ ] API endpoint: `/upload/video` (authenticated, file size limits)
   - [ ] Bull job: Transcode to HLS with FFmpeg (background)
   - [ ] Generate thumbnail (first frame of video)
   - [ ] Add subtitle support (SRT upload or auto-generate with OpenAI Whisper)
   - [ ] Multi-language audio (upload tracks, store separately)

4. **Learner Content Consumption**
   - [ ] Video player (Video.js with HLS support)
   - [ ] Subtitle selection dropdown
   - [ ] Audio track selection
   - [ ] Mark as complete checkbox
   - [ ] Progress tracking (start time, end time, watch duration)

5. **Progress Tracking**
   - [ ] Log user interactions: started, completed, time_spent
   - [ ] Calculate avg_time_spent per module
   - [ ] Completion percentage per course
   - [ ] Status: not_started, in_progress, completed

---

### Phase 3: Assessments (Weeks 7-9)
**Goal**: Quiz and assignment creation, grading, analytics

1. **Quiz Builder (Admin)**
   - [ ] Drag-and-drop question builder (dnd-kit)
   - [ ] Question types: Multiple choice, true/false, short answer, essay
   - [ ] Question bank with categories
   - [ ] Set passing score, time limits
   - [ ] Link quizzes to modules (mandatory or optional)

2. **Quiz Engine (Learner)**
   - [ ] Take quiz with timer
   - [ ] Question navigation (previous/next)
   - [ ] Save draft answers
   - [ ] Submit for grading
   - [ ] View results (score, feedback per question)

3. **Grading**
   - [ ] Auto-grade objective questions (MCQ, T/F)
   - [ ] Manual grading UI for essay questions (admin)
   - [ ] Bulk grading with rubrics
   - [ ] Feedback comments per question

4. **Analytics**
   - [ ] Quiz averages by question
   - [ ] Learner performance distribution (pass/fail)
   - [ ] Time-to-complete metrics
   - [ ] Common mistake patterns

5. **Department Categorization**
   - [ ] Tag assessments by department (Electrical, Civil, etc)
   - [ ] Admin allocates specific assessments to departments
   - [ ] Department heads can view only their assessments

---

### Phase 4: Analytics & Reporting (Weeks 10-12)
**Goal**: Executive dashboards, compliance tracking

1. **Admin Analytics Dashboard**
   - [ ] Total learners, enrolled, in-progress, completed
   - [ ] Avg quiz scores by course
   - [ ] Avg time spent per module
   - [ ] Completion rates (overall & by course)
   - [ ] Learner status breakdown (not_started, in_progress, not_completed, not_evaluated)
   - [ ] Time-series charts (weekly enrollment, course completions)

2. **Department Analytics**
   - [ ] Performance by department (avg scores, completion %)
   - [ ] Bottleneck analysis (modules with low completion)
   - [ ] Learner counts per department
   - [ ] Certification status per department

3. **Metabase Integration**
   - [ ] Pre-built dashboards via Metabase UI
   - [ ] Custom report builder (admin drag-and-drop)
   - [ ] Scheduled email reports
   - [ ] Export to CSV/PDF

4. **Database Optimization**
   - [ ] TimescaleDB hypertables for events log
   - [ ] Create continuous aggregates (hourly/daily summaries)
   - [ ] Materialized views for common reports
   - [ ] Partitioning by company_id or date

---

### Phase 5: Certificates & Compliance (Weeks 13-14)
**Goal**: Certificate generation, customization, audit trails

1. **Certificate Template Builder (Admin)**
   - [ ] Drag-and-drop certificate designer
   - [ ] Add company logo, text fields (learner name, course, date)
   - [ ] Save multiple templates
   - [ ] Preview before issuing

2. **Certificate Generation**
   - [ ] Trigger on module/course completion
   - [ ] Generate PDF (use PDFKit or Playwright)
   - [ ] Store in Garage object storage
   - [ ] Email to learner

3. **Certificate Management**
   - [ ] View issued certificates per learner
   - [ ] Revoke certificates (mark as invalid)
   - [ ] Re-issue after re-completion
   - [ ] Audit log (who issued, when, to whom)

4. **Compliance Tracking**
   - [ ] Mandatory course completion per department
   - [ ] Certification expiry (if applicable)
   - [ ] Non-compliant learners report
   - [ ] Audit trail for all actions

---

### Phase 6: Communication & Scheduling (Weeks 15-16)
**Goal**: Real-time messaging, calendar, notifications

1. **Direct Messaging**
   - [ ] Socket.io implementation
   - [ ] Admin ↔ Learner direct messages
   - [ ] HR ↔ Learner (performance concerns)
   - [ ] Message persistence (PostgreSQL)
   - [ ] Unread message count
   - [ ] Online status indicator

2. **Notifications**
   - [ ] Course enrollment notification
   - [ ] Quiz available / due reminder
   - [ ] Certificate issued
   - [ ] Message received
   - [ ] Admin mentions learner

3. **Calendar**
   - [ ] FullCalendar integration
   - [ ] Department-based color coding
   - [ ] Quiz due dates
   - [ ] Assignment deadlines
   - [ ] Required module dates
   - [ ] iCal export for learners

4. **Email Notifications**
   - [ ] Unsend template setup
   - [ ] Event-driven emails (course assignment, certificate, etc)
   - [ ] Bulk email via Bull queue
   - [ ] Unsubscribe handling

---

### Phase 7: Advanced Features (Weeks 17-20)
**Goal**: Search, multi-language, monitoring, optimization

1. **Full-Text Search**
   - [ ] Elasticsearch cluster setup
   - [ ] Index courses, modules, articles, users
   - [ ] Faceted search UI (filters: department, level, etc)
   - [ ] Autocomplete suggestions
   - [ ] Search analytics (common queries)

2. **Multi-Language Support (Audio)**
   - [ ] Support for multiple audio tracks per video
   - [ ] Language selection dropdown
   - [ ] Subtitle language selection
   - [ ] i18n for UI (React-i18next)
   - [ ] RTL support (if Arabic/Persian required)

3. **Performance & Monitoring**
   - [ ] Set up Prometheus metrics collection
   - [ ] Grafana dashboards (API latency, DB queries, queue size)
   - [ ] APM instrumentation (optional: DataDog or Sentry)
   - [ ] Load testing (k6 or Apache JMeter)
   - [ ] Database indexing optimization

4. **Caching Strategy**
   - [ ] Redis cache for courses, modules (invalidate on edit)
   - [ ] Session store in Redis
   - [ ] Cache video metadata
   - [ ] Cache quiz questions (invalidate on update)
   - [ ] Implement cache-busting strategy

5. **Security Hardening**
   - [ ] Rate limiting (express-rate-limit or NestJS built-in)
   - [ ] CORS configuration
   - [ ] Helmet (security headers)
   - [ ] Input validation & sanitization
   - [ ] SQL injection prevention (Prisma/TypeORM safe by default)
   - [ ] CSRF protection (if applicable)
   - [ ] Audit logging for all admin actions

---

## 3. KEY DATABASE SCHEMA OUTLINE

```sql
-- Multi-tenant setup
CREATE TABLE companies (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  domain VARCHAR(255) UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users (learners, admins, HR)
CREATE TABLE users (
  id UUID PRIMARY KEY,
  company_id UUID NOT NULL REFERENCES companies(id),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255),
  first_name VARCHAR(255),
  last_name VARCHAR(255),
  role ENUM('admin', 'learner', 'hr') NOT NULL,
  department_id UUID,
  status ENUM('active', 'inactive', 'suspended'),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX idx_company_email (company_id, email),
  INDEX idx_role (role)
);

-- Courses
CREATE TABLE courses (
  id UUID PRIMARY KEY,
  company_id UUID NOT NULL REFERENCES companies(id),
  title VARCHAR(255) NOT NULL,
  description TEXT,
  created_by UUID REFERENCES users(id),
  is_published BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX idx_company_id (company_id)
);

-- Modules (chapters in a course)
CREATE TABLE modules (
  id UUID PRIMARY KEY,
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  order_index INT NOT NULL,
  is_mandatory BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX idx_course_id (course_id)
);

-- Submodules (lessons within a module)
CREATE TABLE submodules (
  id UUID PRIMARY KEY,
  module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  content_type ENUM('video', 'article', 'pdf', 'reading'),
  order_index INT NOT NULL,
  content_url VARCHAR(2048),
  is_mandatory BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX idx_module_id (module_id)
);

-- User Progress (tracks completion & watch time)
CREATE TABLE user_progress (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  submodule_id UUID NOT NULL REFERENCES submodules(id),
  status ENUM('not_started', 'in_progress', 'completed'),
  watch_start_time TIMESTAMPTZ,
  watch_end_time TIMESTAMPTZ,
  total_watch_duration INT, -- in seconds
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, submodule_id),
  INDEX idx_user_id (user_id),
  INDEX idx_completed_at (completed_at)
);

-- Assessments (quizzes, assignments)
CREATE TABLE assessments (
  id UUID PRIMARY KEY,
  course_id UUID NOT NULL REFERENCES courses(id),
  module_id UUID REFERENCES modules(id),
  title VARCHAR(255) NOT NULL,
  type ENUM('quiz', 'assignment'),
  passing_score INT DEFAULT 70,
  time_limit_minutes INT,
  is_mandatory BOOLEAN DEFAULT FALSE,
  department_id UUID, -- for department-specific assessments
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX idx_course_id (course_id)
);

-- Quiz Attempts
CREATE TABLE quiz_attempts (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  assessment_id UUID NOT NULL REFERENCES assessments(id),
  score INT,
  passed BOOLEAN,
  started_at TIMESTAMPTZ,
  submitted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX idx_user_id (user_id),
  INDEX idx_submitted_at (submitted_at)
);

-- Certificates
CREATE TABLE certificates (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  course_id UUID NOT NULL REFERENCES courses(id),
  template_id UUID,
  issued_at TIMESTAMPTZ DEFAULT NOW(),
  pdf_url VARCHAR(2048),
  is_revoked BOOLEAN DEFAULT FALSE,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX idx_user_id (user_id)
);

-- Direct Messages
CREATE TABLE messages (
  id UUID PRIMARY KEY,
  sender_id UUID NOT NULL REFERENCES users(id),
  receiver_id UUID NOT NULL REFERENCES users(id),
  content TEXT NOT NULL,
  is_read BOOLEAN DEFAULT FALSE,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX idx_receiver_id (receiver_id),
  INDEX idx_conversation (sender_id, receiver_id, created_at)
);

-- Activity Logs (for analytics & audit)
CREATE TABLE activity_logs (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  action VARCHAR(100) NOT NULL,
  resource_type VARCHAR(100), -- 'course', 'module', 'quiz', etc
  resource_id UUID,
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX idx_user_id (user_id),
  INDEX idx_created_at (created_at),
  INDEX idx_resource (resource_type, resource_id)
);
```

---

## 4. API STRUCTURE (NestJS)

```
src/
├── auth/
│   ├── auth.controller.ts (login, register, refresh-token)
│   ├── auth.service.ts (JWT logic)
│   ├── jwt.strategy.ts
│   └── auth.guard.ts (JWT validation)
├── users/
│   ├── users.controller.ts (CRUD users, profile)
│   ├── users.service.ts
│   └── users.module.ts
├── courses/
│   ├── courses.controller.ts (GET list, GET detail, POST create, PUT update)
│   ├── courses.service.ts
│   ├── modules.controller.ts
│   ├── submodules.controller.ts
│   └── courses.module.ts
├── content/
│   ├── upload.controller.ts (POST /upload/video, /upload/document)
│   ├── upload.service.ts (handle multipart, store in Garage)
│   ├── video.service.ts (transcode job dispatcher)
│   └── content.module.ts
├── progress/
│   ├── progress.controller.ts (GET user progress, POST mark-complete)
│   ├── progress.service.ts
│   └── progress.module.ts
├── assessments/
│   ├── assessments.controller.ts (CRUD quizzes)
│   ├── quiz-attempts.controller.ts (GET attempts, POST submit)
│   ├── grading.service.ts (auto-grade, store scores)
│   └── assessments.module.ts
├── certificates/
│   ├── certificates.controller.ts (GET issued, POST generate)
│   ├── certificates.service.ts (generate PDF, store)
│   └── certificates.module.ts
├── messaging/
│   ├── messages.controller.ts (GET conversation, POST send)
│   ├── messages.gateway.ts (WebSocket + Socket.io)
│   ├── messages.service.ts
│   └── messaging.module.ts
├── analytics/
│   ├── analytics.controller.ts (GET dashboards, learner stats)
│   ├── analytics.service.ts (query aggregates from TimescaleDB)
│   └── analytics.module.ts
├── admin/
│   ├── admin.controller.ts (dashboard)
│   ├── department.controller.ts (CRUD departments, manage allocations)
│   └── admin.module.ts
├── queue/
│   ├── video-transcoding.processor.ts (Bull job consumer)
│   ├── email.processor.ts (send emails)
│   ├── certificate.processor.ts (PDF generation)
│   └── queue.module.ts
└── config/
    ├── database.config.ts
    ├── s3.config.ts (Garage)
    └── redis.config.ts
```

---

## 5. REACT FRONTEND STRUCTURE

```
frontend/
├── src/
│   ├── pages/
│   │   ├── auth/ (Login, Register, ForgotPassword)
│   │   ├── admin/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── UserManagement.tsx
│   │   │   ├── CourseBuilder.tsx
│   │   │   ├── QuizBuilder.tsx
│   │   │   ├── Analytics.tsx
│   │   │   ├── CertificateManager.tsx
│   │   │   ├── DepartmentManager.tsx
│   │   │   ├── Calendar.tsx
│   │   │   └── Messaging.tsx
│   │   └── learner/
│   │       ├── Dashboard.tsx (enrolled courses)
│   │       ├── CoursePlayer.tsx (video player)
│   │       ├── QuizTaker.tsx
│   │       ├── Progress.tsx
│   │       ├── Certificates.tsx
│   │       └── Messaging.tsx
│   ├── components/
│   │   ├── VideoPlayer.tsx (Video.js wrapper)
│   │   ├── DragDropBuilder.tsx (dnd-kit wrapper)
│   │   ├── Calendar.tsx (FullCalendar wrapper)
│   │   ├── RoleGate.tsx (access control)
│   │   └── ...
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useProgress.ts
│   │   ├── useWebSocket.ts
│   │   └── ...
│   ├── services/
│   │   ├── api.ts (axios instance with interceptors)
│   │   ├── courseService.ts
│   │   ├── progressService.ts
│   │   └── ...
│   ├── store/ (Redux or Zustand)
│   │   ├── authSlice.ts
│   │   ├── courseSlice.ts
│   │   └── ...
│   └── App.tsx
├── vite.config.ts
└── tailwind.config.js
```

---

## 6. IMPLEMENTATION CHECKLIST

### Pre-Development
- [ ] Set up monorepo (npm workspaces or Lerna)
- [ ] Create GitHub org + repos
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Create development environment script (Docker Compose)

### Phase 1 Checklist
- [ ] NestJS project initialized
- [ ] PostgreSQL + Prisma schema defined
- [ ] Basic RBAC implementation
- [ ] User CRUD endpoints
- [ ] Frontend auth pages
- [ ] Docker Compose with all services

### Phase 2 Checklist
- [ ] Course CRUD endpoints
- [ ] Module/submodule hierarchy
- [ ] File upload to Garage
- [ ] Video transcoding pipeline (Bull job)
- [ ] Video player with HLS support
- [ ] Progress tracking database records

### Phase 3 Checklist
- [ ] Quiz builder API
- [ ] Quiz attempt submission + auto-grading
- [ ] Manual grading UI
- [ ] Analytics queries for quiz data

### Phase 4 Checklist
- [ ] TimescaleDB aggregates created
- [ ] Metabase dashboards configured
- [ ] Admin dashboard built
- [ ] Department-level reports

### Phase 5 Checklist
- [ ] Certificate template builder
- [ ] PDF generation working
- [ ] Bull job for certificate issuance
- [ ] Email sending verified

### Phase 6 Checklist
- [ ] Socket.io server configured
- [ ] Direct messaging UI
- [ ] FullCalendar integrated
- [ ] Notifications system

### Phase 7 Checklist
- [ ] Elasticsearch indices created
- [ ] Search API endpoints
- [ ] Search UI with filters
- [ ] Performance tests passing
- [ ] Monitoring dashboards live

---

## 7. DEPLOYMENT & SCALING

### Local Development
```bash
docker-compose up
# Includes: PostgreSQL, Redis, Garage, Metabase, MailHog
```

### Self-Hosted Production
```
Docker Compose (single server) → Docker Swarm (multiple servers) → Kubernetes (enterprise)
├── NestJS (port 3000)
├── PostgreSQL (persistent volume)
├── Redis (persistent volume)
├── Garage (persistent volume)
├── Nginx (reverse proxy, SSL)
├── Prometheus + Grafana
└── Backup strategy (automated snapshots)
```

### Cloud Deployment (AWS/GCP/Azure)
- Kubernetes EKS for orchestration
- RDS for PostgreSQL
- ElastiCache for Redis
- S3 + CloudFront for Garage replacement
- CloudWatch/DataDog for monitoring

---

## 8. TEAM STRUCTURE & RESPONSIBILITIES

```
Team (assuming 5-8 developers)
├── Backend Lead (2 devs) - NestJS, video processing, database
├── Frontend Lead (2 devs) - React, video player, course builder UI
├── DevOps (1 dev) - Docker, Kubernetes, CI/CD, monitoring
├── QA (1 dev) - automated tests, performance testing
└── Product Owner (1 person) - requirements, prioritization
```

---

## 9. RISK MITIGATION

| Risk | Mitigation |
|------|-----------|
| Video transcoding slow | Use AWS MediaConvert instead of FFmpeg (if budget allows) |
| Database performance degradation | Implement query optimization, caching, read replicas |
| Real-time messaging scalability | Plan for Redis Pub/Sub distribution if > 10K users |
| Storage costs (videos) | Implement tiered storage (delete old videos after retention) |
| Security breach | Implement audit logging, encrypt sensitive data, regular security audits |

---

## 10. SUCCESS METRICS

- **Performance**: API latency < 200ms, video startup < 3s
- **Adoption**: 80%+ of learners complete first course within 30 days
- **Retention**: 60%+ monthly active users
- **Analytics**: Average time-to-completion < 2 weeks per course
- **Support**: < 5% learner support tickets related to functionality
