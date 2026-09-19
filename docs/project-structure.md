# LMS Project Structure & File Guide

This document provides a complete overview of all project files and folders, their purposes, and responsibilities. Use this for generating additional code and understanding project architecture.

User-facing note: many LMS screens now use the word `Section` even where the backend model and route names still use `Course`.

---

## Recent Change Log

This section tracks the biggest updates made after the original structure guide was written.

### 2026-04-03

- Updated learner quiz experience in `apps/assessments/` with:
  - instruction modal and reliable start flow
  - autosave indicator
  - section-by-section question progression
  - timer-based auto-submit to results
  - learner assessment states for open, resume, retry, locked, and latest result
  - simplified learner assessment hub cards with real attempt status
- Added assessment templates in `apps/assessments/templates/assessments/`
- Added shared assessment partial:
  - `apps/assessments/templates/assessments/includes/quiz_question_card.html`
- Updated notifications in `apps/courses/` with type-specific badges, actions, icons, and colors
- Updated sidebar active navigation visibility in:
  - `templates/base.html`
  - `static/css/shell.css`
- Simplified learner assessment list UI by removing the extra filter rail from the assessment page

---

## 🌳 COMPLETE PROJECT TREE

```
LMS/ (Root Directory)
│
├── 📄 Configuration Files
│   ├── manage.py                              # Django CLI for commands
│   ├── requirements.txt                       # Python dependencies
│   ├── package.json                           # NPM/JavaScript dependencies
│   ├── docker-compose.yml                     # Docker orchestration
│   ├── Dockerfile                             # Container image definition
│   └── db.sqlite3                             # SQLite test database
│
├── 📖 Documentation
│   ├── README.md                              # Project overview & quick start
│   ├── docs/project-structure.md              # This file (complete guide)
│   ├── docs/architecture.md                   # Architecture vision & roadmap
│   ├── docs/migration-plan.md                 # Future migration plan
│   ├── docs/learning/zero-to-lms.md           # Developer learning guide
│   └── docs/learning/zero-to-lms-python.md    # Python-specific learning
│
├── 📁 apps/                                   # Core Django Applications (8 apps)
│   ├── __init__.py
│   │
│   ├── 👤 accounts/                          # User Authentication & Authorization
│   │   ├── __init__.py
│   │   ├── admin.py                          # Admin configuration
│   │   ├── apps.py                           # App config
│   │   ├── models.py                         # Custom User model, roles
│   │   ├── views.py                          # Login, registration, profile views
│   │   ├── urls.py                           # Auth routes
│   │   ├── forms.py                          # Registration & profile forms
│   │   ├── services.py                       # User service logic
│   │   ├── backends.py                       # Custom auth backends
│   │   ├── tests.py                          # Auth unit tests
│   │   ├── migrations/                       # Database migrations
│   │   ├── management/                       # Management commands
│   │   ├── templates/                        # Account templates
│   │   └── __pycache__/                      # Compiled Python cache
│   │
│   ├── 🏢 organizations/                     # Multi-Tenant Organization Support
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                         # Organization, Department models
│   │   ├── services.py                       # Org management logic
│   │   ├── migrations/
│   │   ├── __pycache__/
│   │   └── (no views, urls, or forms)        # Backend-only app
│   │
│   ├── 📚 courses/                           # Course Management & Content (Core)
│   │   ├── __init__.py
│   │   ├── admin.py                          # Course admin interface
│   │   ├── apps.py
│   │   ├── models.py                         # Course, Module, Lesson, Progress
│   │   ├── views.py                          # Course detail, lesson playback
│   │   ├── urls.py                           # Course routing
│   │   ├── forms.py                          # Course/lesson/module forms
│   │   ├── services.py                       # Enrollment, progress tracking
│   │   ├── video.py                          # Video processing helpers
│   │   ├── subtitles.py                      # Subtitle/caption handling
│   │   ├── tests.py
│   │   ├── migrations/                       # 8+ database migrations
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── generate_lesson_subtitles.py  # Auto-gen subtitles
│   │   ├── templates/courses/                # Course HTML templates
│   │   │   ├── course_list.html
│   │   │   ├── course_detail.html
│   │   │   ├── course_form.html
│   │   │   ├── course_builder.html           # Drag-drop module ordering
│   │   │   ├── lesson_detail.html            # Video/article player
│   │   │   ├── lesson_form.html
│   │   │   ├── calendar_board.html           # Event scheduling
│   │   │   ├── comment_thread.html
│   │   │   ├── notification_list.html
│   │   │   └── ...
│   │   ├── __pycache__/
│   │   └── (Largest app - 2000+ lines of logic)
│   │
│   ├── ✅ assessments/                       # Quiz & Assessment Engine
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                         # Quiz, Question, Attempt models
│   │   ├── views.py                          # Quiz display, grading
│   │   ├── urls.py
│   │   ├── forms.py                          # Quiz creation forms
│   │   ├── services.py                       # Grading logic
│   │   ├── tests.py
│   │   ├── migrations/
│   │   ├── __pycache__/
│   │   └── (no templates)
│   │
│   ├── 🏆 certificates/                      # Certificate Issuance & Tracking
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                         # Certificate, CertificateTemplate
│   │   ├── views.py                          # Certificate list, download
│   │   ├── urls.py
│   │   ├── services.py                       # Certificate generation
│   │   ├── migrations/
│   │   ├── templates/certificates/
│   │   │   └── certificate_list.html
│   │   ├── __pycache__/
│   │   └── (no forms)
│   │
│   ├── 💬 messaging/                         # Real-Time Chat & Messaging
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                         # Conversation, Message models
│   │   ├── views.py                          # Conversation list/detail
│   │   ├── urls.py                           # HTTP endpoints
│   │   ├── forms.py                          # Message forms
│   │   ├── consumers.py                      # WebSocket consumers
│   │   ├── routing.py                        # WebSocket URL routing
│   │   ├── migrations/
│   │   ├── templates/messaging/
│   │   │   ├── conversation_list.html
│   │   │   ├── conversation_detail.html
│   │   │   └── conversation_create.html
│   │   ├── __pycache__/
│   │   └── (Channels integration for real-time)
│   │
│   ├── 📊 analytics/                         # Learning Analytics & Dashboards
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── views.py                          # Dashboard views with metrics
│   │   ├── urls.py
│   │   ├── services.py                       # Analytics computation
│   │   ├── tests.py
│   │   ├── templates/                        # Analytics dashboards
│   │   ├── __pycache__/
│   │   └── (no models or forms)
│   │
│   └── 🔧 common/                            # Shared Utilities & Base Classes
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py                         # BaseModel, TimeStamped mixin
│       ├── views.py                          # Base view mixins
│       ├── services.py                       # Shared service functions
│       ├── context_processors.py             # Template context injection
│       ├── pagination.py                     # Pagination abstraction
│       ├── search.py                         # Cross-app search
│       ├── holidays.py                       # Holiday definitions
│       ├── tests.py                          # Test utilities & factories
│       ├── migrations/
│       ├── __pycache__/
│       └── (no urls or forms)
│
├── 📁 lms_portal/                            # Django Project Core Config
│   ├── __init__.py
│   ├── settings.py                           # Main Django settings
│   │                                         # - Database config
│   │                                         # - Installed apps
│   │                                         # - Middleware
│   │                                         # - Auth backends
│   │                                         # - Redis/Channels
│   ├── urls.py                               # Root URL dispatcher
│   ├── asgi.py                               # ASGI config (Channels)
│   ├── wsgi.py                               # WSGI config (Deployment)
│   └── __pycache__/
│
├── 📁 frontend/                              # React + TypeScript (Vite)
│   ├── package.json                          # Frontend dependencies
│   ├── vite.config.ts                        # Vite config
│   ├── tsconfig.json                         # TypeScript config
│   ├── tailwind.config.js                    # Tailwind CSS config
│   ├── postcss.config.js                     # PostCSS plugins
│   ├── index.html                            # HTML entry point
│   ├── build.mjs                             # Custom build script
│   │
│   └── src/                                  # React source files
│       ├── main.tsx                          # React entry point
│       ├── App.tsx                           # Root component
│       ├── styles.css                        # Global styles
│       ├── calendar-board.jsx                # Calendar component
│       │
│       ├── lib/                              # Utility libraries
│       │   ├── api.ts                        # API client
│       │   └── socket.ts                     # WebSocket client
│       │
│       └── pages/                            # Page components
│           ├── CalendarWorkspacePage.tsx     # Calendar management
│           └── SearchWorkspacePage.tsx       # Global search
│
├── 📁 templates/                             # Server-Rendered HTML Templates
│   ├── base.html                             # Base layout template
│   ├── registration/
│   │   └── login.html                        # Login page
│   └── includes/
│       └── pagination.html                   # Pagination component
│
├── 📁 static/                                # Compiled Static Assets
│   ├── css/
│   │   ├── app.css                           # Main styles
│   │   ├── authoring.css                     # Content creation styles
│   │   ├── courses.css                       # Course-specific styles
│   │   ├── dashboard.css                     # Dashboard styles
│   │   ├── shell.css                         # Layout styles
│   │   └── (other .css files)
│   │
│   └── js/
│       ├── shell.js                          # Navigation & layout
│       ├── lesson_player.js                  # Video player
│       ├── lesson_reading.js                 # Article utilities
│       ├── quiz_builder.js                   # Quiz authoring
│       ├── quiz_experience.js                # Quiz taking
│       ├── course_builder.js                 # Course structure
│       ├── chat.js                           # Messaging UI
│       ├── date_holidays.js                  # Holiday calendar
│       ├── authoring.js                      # Generic authoring
│       └── react/
│           └── calendar-board.js             # Compiled React
│
├── 📁 media/                                 # User-Uploaded Content
│   └── lessons/
│       ├── articles/                         # Lesson cover images
│       │   ├── ai-chip-...webp
│       │   ├── Ch1-title1.jpg
│       │   └── (50+ article images)
│       │
│       ├── media/                            # Video & document files
│       │   ├── *.mp4                         # Video files (100+ mb)
│       │   ├── *.pdf                         # PDF handbooks
│       │   └── (40+ media files)
│       │
│       └── subtitles/                        # Captions & subtitles
│           ├── *.vtt                         # WebVTT format
│           ├── *.srt                         # SRT format
│           └── (30+ subtitle files)
│
├── 📁 services/api/                          # Separate API Service
│   └── package.json                          # API service config
│
├── 📁 streamlit_dashboard/                   # Analytics Dashboard
│   ├── app.py                                # Streamlit app
│   └── __pycache__/                          # Compiled cache
│
├── 📁 node_modules/                          # NPM Dependencies
│   ├── react/                                # React library
│   ├── react-dom/                            # React DOM
│   ├── esbuild/                              # JS bundler
│   ├── @esbuild/win32-x64/
│   └── (other packages)
│
└── 📁 __pycache__/                           # Python Cache
    └── (Compiled Python bytecode)
```

---

## ROOT LEVEL FILES

### Configuration & Project Files

| File | Purpose |
|------|---------|
| `manage.py` | Django management script. Run migrations, start server, create superuser (`python manage.py runserver`) |
| `requirements.txt` | Python dependencies (Django 6.0, Channels 4.3, psycopg, ffmpeg, webvtt, streamlit, plotly) |
| `package.json` | NPM root config for React/frontend builds and dependencies |
| `docker-compose.yml` | Docker orchestration file for PostgreSQL, Redis, and Django services |
| `Dockerfile` | Container image definition for Django LMS app |
| `db.sqlite3` | SQLite database file (used for local testing) |

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Main project overview, quick start, and module documentation |
| `docs/architecture.md` | Long-term architecture vision and feature planning |
| `docs/migration-plan.md` | Future tech stack modernization roadmap |
| `docs/learning/zero-to-lms.md` | Learning path for new developers on the LMS |
| `docs/learning/zero-to-lms-python.md` | Python-specific learning resources for the project |

---

## `/apps/` - Core Django Applications

The `apps/` directory contains 8 Django apps, each handling a specific domain. Each app follows Django's MVT (Model-View-Template) pattern.

### App Naming Pattern

Each app has this standard structure:
```
app_name/
  ├── admin.py              # Django admin configuration
  ├── apps.py               # App configuration
  ├── models.py             # Database models (if needed)
  ├── views.py              # Request handlers
  ├── urls.py               # URL routing
  ├── forms.py              # Django forms (if needed)
  ├── services.py           # Business logic layer
  ├── tests.py              # Unit tests
  ├── migrations/            # Database migration files
  ├── templates/             # HTML templates
  ├── management/commands/   # Custom Django commands
  └── __pycache__/           # Compiled Python cache

```

---

## APPS DETAILED BREAKDOWN

### 1. `/apps/accounts/` - User Authentication & Authorization

**Purpose:** Handle user registration, login, profiles, and role-based access.

| File | Purpose |
|------|---------|
| `models.py` | Custom User model with role support (Admin, HR/Manager, Learner) |
| `views.py` | Login, logout, registration, profile management views |
| `forms.py` | User registration and profile forms |
| `backends.py` | Custom authentication backends (email/username/phone login) |
| `services.py` | User service layer (password reset, profile updates) |
| `admin.py` | Django admin configuration for user management |
| `urls.py` | Authentication route endpoints |
| `tests.py` | Authentication unit tests |
| `migration/` | Database schema migrations for custom user model |
| `templates/` | Includes `login.html` in `templates/registration/` |

**Key Features:**
- Multi-role support (Admin, HR/Manager, Learner)
- Email, username, and phone-based authentication
- User profile management
- Password reset workflow

---

### 2. `/apps/organizations/` - Multi-Tenant Organization Support

**Purpose:** Handle organizational hierarchies, departments, and organization-level settings.

| File | Purpose |
|------|---------|
| `models.py` | Organization, Department, OrganizationMember models |
| `services.py` | Organization management operations |
| `admin.py` | Django admin for org management |
| `apps.py` | App configuration |
| `migrations/` | Schema migrations for org/dept models |

**Key Features:**
- Multi-tenant organization support
- Department hierarchies
- Organization member management
- Role-based access per organization

---

### 3. `/apps/courses/` - Course Management & Content

**Purpose:** Core learning content: courses, modules, lessons, and progress tracking.

**File Breakdown:**

| File | Purpose |
|------|---------|
| `models.py` | Course, Module, Lesson, LessonProgress, CourseComment, CalendarEvent, CourseNotification |
| `views.py` | Course detail, list, enrollment, lesson playback, comment threads, calendar management |
| `forms.py` | Course/module/lesson creation forms, calendar event forms |
| `services.py` | Course enrollment, progress tracking, progress calculations |
| `urls.py` | Course and lesson routing endpoints |
| `admin.py` | Django admin for course management |
| `video.py` | Video processing and HLS integration helper functions |
| `subtitles.py` | Subtitle/caption file handling (WebVTT, SRT) |
| `tests.py` | Course, module, lesson tests |

**Models:**
- `Course` - Main course container
- `Module` - Chapter/section within a course
- `Lesson` - Individual learning unit (video, article, quiz)
- `LessonProgress` - Tracks user progress through lessons
- `CourseComment` - Comments on courses/lessons
- `CourseNotification` - Push notifications for course updates
- `CalendarEvent` - Meeting/event scheduling within courses

**Templates:** (in `courses/templates/courses/`)
- `course_list.html` - Browse all courses
- `course_detail.html` - Single course view
- `course_form.html` - Create/edit course
- `course_builder.html` - Drag-drop module/lesson ordering
- `lesson_detail.html` - Lesson player (video/article view)
- `lesson_form.html` - Create/edit lesson
- `calendar_board.html` - Calendar widget for scheduling
- `comment_thread.html` - Comment section
- `course_complete.html` - Completion confirmation screen

**Management Commands:**
- `generate_lesson_subtitles.py` - Auto-generate subtitles for video lessons

**Media Storage:** Media files stored in `media/lessons/`:
- `articles/` - Article images (.webp, .png, .jpg)
- `media/` - Video files (.mp4) and PDFs
- `subtitles/` - WebVTT and SRT subtitle files

---

### 4. `/apps/assessments/` - Quiz & Testing Engine

**Purpose:** Quiz creation, attempt tracking, grading, and answer evaluation.

| File | Purpose |
|------|---------|
| `models.py` | AssessmentCategory, Quiz, Question, Choice, QuizAttempt, QuizAnswer, QuizAssignment |
| `views.py` | Quiz display, start flow, draft save, answer submission, results view, manual review, live insights |
| `forms.py` | Quiz creation, question building forms |
| `services.py` | Attempt start, draft save, grading logic, score calculation, result generation |
| `admin.py` | Quiz/question management in admin |
| `urls.py` | Quiz endpoints |
| `tests.py` | Quiz engine tests |
| `migrations/` | Assessment schema migrations |
| `templates/assessments/` | Learner/admin assessment templates |

**Models:**
- `AssessmentCategory` - Quiz categorization
- `Quiz` - Assessment/test container
- `Question` - Individual quiz question
- `Choice` - Multiple choice answers
- `QuizAttempt` - User's quiz attempt record
- `QuizAnswer` - User's answers to specific questions
- `QuizAssignment` - Department or learner quiz allocation

**Templates:** (in `apps/assessments/templates/assessments/`)
- `quiz_list.html` - Assessment hub for learner/admin
- `quiz_detail.html` - Learner quiz experience and admin analytics view
- `quiz_result.html` - Result screen with badge/certificate connection
- `quiz_builder_form.html` - Admin quiz builder
- `quiz_assignment_form.html` - Department/learner assignment form
- `quiz_attempt_review.html` - Manual grading screen
- `includes/quiz_question_card.html` - Shared learner question card partial

**Key Features:**
- Multiple question types (MCQ, fill-the-blank, essay)
- Auto-grading for objective questions
- Manual review for subjective answers
- Attempt history and score tracking
- Detailed attempt analytics
- Autosaved in-progress answers
- Instruction modal and start-quiz workflow
- Section-by-section learner navigation
- Timer-based auto-submit to results

---

### 5. `/apps/certificates/` - Certificate Issuance & Management

**Purpose:** Generate and track certificates upon course completion.

| File | Purpose |
|------|---------|
| `models.py` | Certificate, CertificateTemplate, CertificateIssue |
| `views.py` | Certificate preview, download, certificate list |
| `services.py` | Certificate generation, email delivery |
| `admin.py` | Certificate admin configuration |
| `urls.py` | Certificate endpoints |
| `migrations/` | Schema migrations |
| `templates/certificates/certificate_list.html` | User's earned certificates list |

**Models:**
- `CertificateTemplate` - Certificate design template
- `Certificate` - Earned by user upon course completion
- `CertificateIssue` - Metadata about certificate issuance

**Key Features:**
- PDF certificate generation
- Customizable certificate templates
- Completion-triggered issuance
- Certificate verification/download

---

### 6. `/apps/messaging/` - Real-Time Chat & Direct Messaging

**Purpose:** Direct messaging between users with WebSocket support for real-time updates.

| File | Purpose |
|------|---------|
| `models.py` | Conversation, ConversationMessage, UserConversation participant tracking |
| `views.py` | Conversation list, detail, message creation |
| `forms.py` | Message create/edit forms |
| `consumers.py` | Django Channels WebSocket consumer for real-time messaging |
| `routing.py` | WebSocket URL routing configuration |
| `admin.py` | Conversation admin |
| `urls.py` | HTTP conversation endpoints |
| `migrations/` | Schema migrations |

**Models:**
- `Conversation` - Group chat/DM container
- `ConversationMessage` - Individual messages
- `UserConversation` - User participation in conversation

**Templates:**
- `conversation_list.html` - User's conversations
- `conversation_detail.html` - Single conversation view with message thread
- `conversation_create.html` - Start new conversation

**Key Features:**
- Real-time WebSocket messaging via Django Channels
- Group and 1-on-1 conversations
- Message history
- Online presence indicators
- Redis-backed message queuing

---

### 7. `/apps/analytics/` - Learning Analytics & Dashboards

**Purpose:** Track learning metrics and provide visualizations for admins and learners.

| File | Purpose |
|------|---------|
| `views.py` | Dashboard views with learning metrics |
| `services.py` | Analytics computation (engagement, completion rates, time spent) |
| `urls.py` | Analytics route endpoints |
| `tests.py` | Analytics tests |

**Key Features:**
- Engagement metrics (login frequency, activity time)
- Course completion rates
- Time-on-task tracking
- Question-level performance analytics
- Customizable dashboards

---

### 8. `/apps/common/` - Shared Utilities & Common Functionality

**Purpose:** Reusable components used across all apps.

| File | Purpose |
|------|---------|
| `models.py` | BaseModel, AbstractTimeStamped, Organization soft-delete utilities |
| `services.py` | Shared service functions |
| `views.py` | Common view mixins and base views |
| `context_processors.py` | Template context injection (current user, org, settings) |
| `pagination.py` | Custom pagination logic for large result sets |
| `search.py` | Cross-app search functionality |
| `holidays.py` | Holiday/non-working day definitions |
| `tests.py` | Common test utilities and factories |
| `migrations/` | Schema migrations |

**Key Utilities:**
- Pagination abstraction
- Full-text search across courses/lessons
- Holiday calendar management
- Common context variables for templates
- Timestamp-based models (created_at, updated_at)

---

## `/lms_portal/` - Django Project Configuration

**Purpose:** Core Django project settings and URL routing.

| File | Purpose |
|------|---------|
| `settings.py` | Main Django configuration - database, installed apps, middleware, auth backend, Redis, static files |
| `urls.py` | Root URL dispatcher - routes all requests to app URLs |
| `asgi.py` | ASGI config for async deployment (Channels support) |
| `wsgi.py` | WSGI config for traditional deployment |
| `__init__.py` | Package initializer |

**Key Settings:**
- **Database:** PostgreSQL primary, SQLite fallback for testing
- **Auth Backend:** Custom multi-auth (email/username/phone)
- **Channels:** Redis-backed for WebSocket scalability
- **Static Files:** Collected via Django's staticfiles app
- **Media Files:** User-uploaded content (lessons, PDFs, videos)

---

## `/frontend/` - React + TypeScript Frontend (Vite)

**Purpose:** Modern React-based frontend for interactive components and real-time features.

| File | Purpose |
|------|---------|
| `package.json` | Frontend dependencies (React, React-DOM) and build scripts |
| `vite.config.ts` | Vite bundler configuration for fast dev/prod builds |
| `tsconfig.json` | TypeScript configuration |
| `index.html` | HTML entry point |
| `tailwind.config.js` | Tailwind CSS configuration for utility-first styling |
| `postcss.config.js` | PostCSS plugins (Tailwind integration) |
| `build.mjs` | ESBuild-based build script for calendar component |

**src/ Directory:**

| File | Purpose |
|------|---------|
| `main.tsx` | React app entry point |
| `App.tsx` | Root component wrapper |
| `styles.css` | Global styles |
| `calendar-board.jsx` | Calendar event scheduling component (drag-drop) |

**lib/ Directory:**
| File | Purpose |
|------|---------|
| `api.ts` | API client for Django backend calls (fetch wrapper) |
| `socket.ts` | WebSocket client for real-time messaging |

**pages/ Directory:**
| File | Purpose |
|------|---------|
| `CalendarWorkspacePage.tsx` | Calendar management page (events, meetings) |
| `SearchWorkspacePage.tsx` | Global search and filtering interface |

**Build Scripts:**
- `npm run build:calendar` - Build calendar component
- `npm run build:frontend` - Build all frontend components

---

## `/templates/` - Django HTML Templates

**Purpose:** Server-rendered HTML templates for traditional views.

| File | Purpose |
|------|---------|
| `base.html` | Base template with sidebar shell, topbar, notification links, and active navigation layout |
| `includes/pagination.html` | Reusable pagination component |
| `registration/login.html` | Login page (accounts app) |

**Template Inheritance:**
- All app-specific templates extend `base.html`
- Shared components in `includes/` subdirectory
- Each app has its own `templates/app_name/` folder
- Assessments also use app-level templates in `apps/assessments/templates/assessments/`

---

## `/static/` - Static Assets (CSS, JS)

**Purpose:** Compiled and bundled static files served by Django.

```
static/
├── css/
│   ├── app.css              # Main application styles
│   ├── authoring.css        # Course/content creation styles
│   ├── courses.css          # Course-specific styles
│   ├── dashboard.css        # Dashboard/analytics styles
│   ├── shell.css            # Layout/shell styles, sidebar highlight, active nav visibility
│   └── ...                  # Additional stylesheets
├── js/
│   ├── shell.js             # Navigation and layout JS
│   ├── lesson_player.js     # Video player logic
│   ├── lesson_reading.js    # Article/text reading enhancements
│   ├── quiz_builder.js      # Quiz authoring interface
│   ├── quiz_experience.js   # Quiz-taking interface with section flow, autosave, and timers
│   ├── course_builder.js    # Course structure drag-drop
│   ├── chat.js              # Messaging UI logic
│   ├── date_holidays.js     # Holiday calendar utilities
│   ├── authoring.js         # Generic content creation JS
│   └── react/
│       └── calendar-board.js # Compiled React calendar component
```

**Compiled Output:** Static files are collected from frontend builds and static/ directory via Django's `collectstatic` command.

---

## `/media/` - User-Uploaded Content

**Purpose:** Stores course media, lesson files, and user uploads.

```
media/
└── lessons/
    ├── articles/            # Article cover images (.webp, .png, .jpg)
    │   ├── ai-chip-...webp
    │   ├── Ch1-title1.jpg
    │   └── ...
    ├── media/               # Video files (.mp4) and PDFs
    │   ├── Future_Of_Indian_IT_Service_Companies.mp4
    │   ├── handbook.pdf
    │   └── ... (100+ media files)
    └── subtitles/           # WebVTT and SRT caption files
        ├── captions.vtt
        ├── captions.srt
        └── ... (multi-language subtitles)
```

**File Types:**
- **Videos:** MP4 format (HLS-ready with ffmpeg processing)
- **Images:** WebP, PNG, JPG (responsive article thumbnails)
- **Subtitles:** VTT (video captions), SRT (traditional format)
- **Documents:** PDF (handbooks, supplementary materials)

---

## `/services/api/` - Legacy/Separate API Service

**Purpose:** Potential standalone API service (minimal in current project).

| File | Purpose |
|------|---------|
| `package.json` | API service NPM configuration |

*Note: Most API logic is in Django apps.*

---

## `/streamlit_dashboard/` - Analytics Dashboard

**Purpose:** Data visualization and analytics dashboard built with Streamlit.

| File | Purpose |
|------|---------|
| `app.py` | Streamlit application with learning analytics visualizations |

**Features:**
- Plotly-based interactive charts
- PyGWalker integration for exploratory data analysis
- Real-time learner metrics
- Engagement dashboards
- Course performance reports

**Run:** `streamlit run streamlit_dashboard/app.py`

---

## `/node_modules/` - NPM Dependencies

**Purpose:** Installed JavaScript dependencies for the project.

**Main Packages:**
- `react` - UI library
- `react-dom` - React DOM renderer
- `esbuild` - Ultra-fast JavaScript bundler
- `loose-envify` - Environment variable replacement
- `scheduler` - React scheduler

*Generated by `npm install` - not manually edited.*

---

## Key Dependencies Summary

### Python (`requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| Django | 6.0 | Web framework |
| Channels | 4.3 | WebSocket support |
| Daphne | 4.2 | ASGI server |
| Channels-Redis | 4.3 | Redis message broker |
| psycopg | 3.3 | PostgreSQL driver |
| python-ffmpeg-video-streaming | 0.1.16 | HLS video encoding |
| webvtt-py | 0.5.1 | Subtitle parsing |
| streamlit | 1.43 | Analytics dashboards |
| plotly | 6.0 | Interactive charts |
| pygwalker | 0.4.9 | Data exploration |
| python-dotenv | 1.0 | Environment variables |

### Node.js (`package.json`)

| Package | Version | Purpose |
|---------|---------|---------|
| react | 18.3.1 | Frontend library |
| react-dom | 18.3.1 | React rendering |
| esbuild | 0.25.3 (dev) | JS bundler |

---

## Data Models Overview

### User & Auth
- **User** - Custom user with roles (Admin, HR/Manager, Learner)
- **Organization** - Multi-tenant org container
- **Department** - Org sub-groups

### Learning Content
- **Course** - Main learning container
- **Module** - Course chapter/section
- **Lesson** - Learning unit (video, article, quiz)
- **LessonProgress** - Tracks learner progress

### Assessment
- **Quiz** - Assessment/test container
- **Question** - Quiz items
- **QuizAttempt** - Learner's attempt record
- **AttemptAnswer** - Individual question answers

### Certificates
- **Certificate** - Earned upon completion
- **CertificateTemplate** - Design template

### Messaging
- **Conversation** - Chat group/DM
- **ConversationMessage** - Individual messages

### Other
- **CalendarEvent** - Meeting/event scheduling
- **CourseComment** - Lesson/course discussions
- **CourseNotification** - Update notifications

---

## URL Routing Structure

```
Root URLs (lms_portal/urls.py)
├── /accounts/           → accounts app (login, register, profile)
├── /courses/            → courses app (courses, lessons, progress)
├── /quiz/               → assessments app (quizzes, attempts)
├── /certificates/       → certificates app (earned certs)
├── /messages/           → messaging app (conversations)
├── /analytics/          → analytics app (dashboards)
├── /organizations/      → organizations app (org management)
├── /admin/              → Django admin panel
└── /api/ws/messages/    → WebSocket endpoint (Channels)
```

---

## Development Workflow

### Local Setup
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

### Docker Setup
```bash
docker-compose up -d
python manage.py migrate
```

### Frontend Build
```bash
npm run build:frontend
```

### Analytics Dashboard
```bash
streamlit run streamlit_dashboard/app.py
```

---

## Code Style & Architecture

### Django Structure
- **MVT Pattern** - Model, View, Template separation
- **Service Layer** - Business logic in `services.py`
- **Forms Layer** - Validation in `forms.py`
- **Admin Interface** - Management in `admin.py`
- **URL Routing** - Endpoints in `urls.py`

### React Components
- **TypeScript** - Type-safe components
- **Vite** - Fast dev/build server
- **Tailwind CSS** - Utility-first styling
- **API Client** - Centralized in `lib/api.ts`
- **WebSocket** - Real-time features via `lib/socket.ts`

### Template Structure
- **Base Templates** - `base.html` with common layout
- **Inheritance** - Child templates extend base
- **Includes** - Reusable components in `includes/`
- **App-Specific** - Each app has `templates/app_name/` folder

---

## Performance Considerations

1. **Database:** PostgreSQL with indexed fields on frequently queried columns
2. **Caching:** Redis for sessions, Channels broker, and cache
3. **Video Streaming:** HLS-encoded via ffmpeg for adaptive bitrate
4. **Pagination:** Custom pagination for large result sets in `common/pagination.py`
5. **Async:** Django Channels for non-blocking WebSocket connections
6. **Frontend:** Vite for instant HMR during development

---

## Testing Structure

- **Unit Tests:** Located in each app's `tests.py`
- **Coverage:** Common factories in `apps/common/tests.py`
- **Database:** SQLite for test isolation with transactions
- **Fixtures:** Test data generation via Django ORM

---

## Environment Variables (via `.env`)

```env
DEBUG=True/False
DATABASE_ENGINE=postgresql/sqlite
DATABASE_NAME=lms_db
DATABASE_USER=postgres
DATABASE_PASSWORD=***
DATABASE_HOST=localhost
DATABASE_PORT=5432
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://localhost:8000
```

---

## Production Deployment

- **Server:** Daphne ASGI server (handles WebSockets)
- **Reverse Proxy:** Nginx for static/media serving and SSL
- **Database:** PostgreSQL 13+
- **Cache/Queue:** Redis cluster
- **Container:** Docker with docker-compose or Kubernetes
- **Static Files:** Collected via `python manage.py collectstatic`

---

## Future Extensions

From roadmap files, planned features:
- Mobile-native app (React Native)
- Advanced analytics (machine learning)
- LTI integration (standard LMS protocols)
- API versioning and broader JavaScript SDK
- Microservices migration
- GraphQL API layer
- AI-powered course recommendations

---

This document covers all 150+ files across the LMS project. Use it as a reference when:
- Adding new features
- Understanding data flow
- Migrating functionality
- Generating boilerplate code
- Training AI models on your codebase
