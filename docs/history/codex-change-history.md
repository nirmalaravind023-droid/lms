# Codex Change History

This file is the running Codex-side project history for the Django `LMS` workspace.

User-facing note: many LMS screens now use the word `Section` even where backend model and route names still use `Course`.

Important note:
- Dates and times below use the workspace timeline we can recover from file modification timestamps and the completed Codex work sequence.
- Where the project itself did not store a per-change audit timestamp, entries are grouped under the closest reliable date/time window instead of inventing exact seconds.

---

## 2026-04-01

### 11:32:09
- Initial roadmap/learning documentation present in the repo:
  - `ZERO_TO_LMS_LEARNING_ROADMAP.md`

### 11:44:19
- Python-specific learning roadmap present:
  - `ZERO_TO_LMS_PYTHON_LEARNING_ROADMAP.md`

### 12:03:48
- Local container/deployment base files present:
  - `Dockerfile`
  - `docker-compose.yml`

### 12:27:49
- Project bootstrap/reference files present:
  - `.env.example`
  - `README.md`
  - `requirements.txt`
  - `.gitignore`

### 17:55:16
- `manage.py` present and active as the Django entry point.

---

## 2026-04-02

### 00:59:08 to 01:00:54
- Node/frontend package setup present:
  - `package.json`
  - `package-lock.json`

### 14:49:25
- Migration-plan documentation present:
  - `NEXTGEN_LMS_STACK_MIGRATION_PLAN.md`

### 14:54 to 15:17 window
- Virtualenv, frontend workspace, and package folders active in the project tree:
  - `.venv`
  - `frontend`
  - `.python_packages`

### 2026-04-02 summary
- Project contains the major Django apps:
  - `accounts`
  - `organizations`
  - `courses`
  - `assessments`
  - `certificates`
  - `messaging`
  - `analytics`
  - `common`
- React/Vite calendar frontend workspace present under:
  - `frontend/src/calendar-board.jsx`

---

## 2026-04-03

### 08:47:00 to 10:01:00 window
- Existing local runserver logs confirm active local development/testing:
  - `runserver.out.log`
  - `runserver.err.log`

### 10:36:10
- Architecture roadmap present:
  - `LMS_ARCHITECTURE_ROADMAP.md`

### 10:36 to 15:28 window
- Project documentation updated to match the newer LMS implementation:
  - `PROJECT_STRUCTURE.md`

---

## 2026-04-03 Codex Build History

### 10:30 to 12:30 window
- Switched work focus fully to the correct Django `LMS` project instead of `LMS2`.
- Verified the real project root, settings module, custom user model, and Django routing.
- Confirmed SQLite-mode local startup path for local testing.

### 12:30 to 13:15 window
- Restored and stabilized major course routing/view behavior in:
  - `apps/courses/views.py`
  - `apps/courses/urls.py`
- Repaired course-related tests to match working Django LMS behavior.

### 13:15 to 13:45 window
- Improved registration + approval flow:
  - pending-login state now shows a separate wait-for-admin message/UI
- Main files touched:
  - `apps/accounts/forms.py`
  - `templates/registration/login.html`
  - `static/css/app.css`
  - `apps/accounts/tests.py`

### 13:45 to 14:15 window
- Extended approval flow so new joinee approvals trigger learner-facing notifications and assignment sync.
- Improved notification redirect and button semantics for comments, courses, approvals, and assessments.
- Main files touched:
  - `apps/accounts/services.py`
  - `apps/courses/views.py`
  - `apps/courses/templates/courses/notification_list.html`
  - `static/css/app.css`

### 14:15 to 14:45 window
- Connected quiz badges and certificates:
  - passed quiz badge with marks
  - certificate page badge visibility
  - course-completion certificate linkage
- Main files touched:
  - `apps/certificates/views.py`
  - `apps/assessments/views.py`
  - `apps/courses/views.py`
  - `apps/certificates/templates/certificates/certificate_list.html`
  - `apps/assessments/templates/assessments/quiz_result.html`
  - `apps/courses/templates/courses/course_complete.html`

### 14:45 to 15:00 window
- Added gold/silver/bronze badge tiers for quiz results and certificate views.

### 15:00 to 15:20 window
- Fixed quiz attempt start flow:
  - start button now creates an in-progress attempt in SQL
  - draft answers autosave into `QuizAnswer`
  - admin weak-question analytics clarified
- Main files touched:
  - `apps/assessments/services.py`
  - `apps/assessments/views.py`
  - `apps/assessments/urls.py`
  - `apps/assessments/templates/assessments/quiz_detail.html`
  - `static/js/quiz_experience.js`

### 15:20 to 15:35 window
- Added learner autosave status chip:
  - `Autosave ready`
  - `Saving...`
  - `Autosaved`
  - `Save failed`

### 15:35 to 15:50 window
- Reworked notification page semantics:
  - type-specific badges/actions/icons/colors
  - lesson/video notifications mapped to learning updates
  - course updates mapped to update actions instead of comment actions
- Main files touched:
  - `apps/courses/models.py`
  - `apps/courses/views.py`
  - `apps/courses/templates/courses/notification_list.html`
  - `apps/courses/tests.py`

### 15:50 to 16:05 window
- Fixed sidebar active-state visibility:
  - assessment item now clearly shows as selected
  - active nav card changed to a stronger white/blue highlighted state
- Main files touched:
  - `templates/base.html`
  - `static/css/shell.css`

### 16:05 to 16:20 window
- Simplified learner assessment list UI:
  - removed extra filter area for learners
  - assessment cards became clearer and less cluttered

### 16:20 to 16:40 window
- Rebuilt learner quiz experience:
  - instruction modal before start
  - one-question-at-a-time section flow
  - timer-based auto-submit to result page
  - section locking between completed and future sections
  - stronger resume/retry/locked/result states in the learner UI
- Main files touched:
  - `apps/assessments/views.py`
  - `apps/assessments/templates/assessments/quiz_detail.html`
  - `apps/assessments/templates/assessments/includes/quiz_question_card.html`
  - `apps/assessments/templates/assessments/quiz_list.html`
  - `static/js/quiz_experience.js`
  - `static/css/app.css`
  - `apps/assessments/tests.py`

### 16:40 to 16:50 window
- Updated `PROJECT_STRUCTURE.md` to reflect:
  - latest quiz changes
  - templates/static structure
  - recent change log section

### 16:50 to 17:00 window
- Fixed CSS/static serving problems in local Django usage:
  - identified duplicate `runserver` processes
  - fixed local static asset routing for CSS/JS when local env behaved like `DEBUG=False`
  - reduced global stylesheet bleed from loading unrelated CSS on every page
- Main files touched:
  - `lms_portal/urls.py`
  - `templates/base.html`

### 17:00 to 17:10 window
- Diagnosed and fixed React calendar crash caused by backend/frontend payload mismatch:
  - backend now returns full calendar JSON contract
  - frontend now has safe fallback handling for missing fields
  - React calendar bundle rebuilt
- Main files touched:
  - `apps/courses/views.py`
  - `frontend/src/calendar-board.jsx`
  - `apps/courses/templates/courses/calendar_board.html`
  - `apps/courses/tests.py`

### 17:10 to 17:20 window
- Clarified learner calendar behavior:
  - separate `Holidays` count
  - clear no-department-tasks empty state
  - made it obvious that holidays are visible even when LMS task counts are zero

### 17:20 to 17:30 window
- Added holiday filter UI to React calendar:
  - toggle LMS tasks on/off
  - filter by calendar source/religion
  - Google-style calendar categories exposed in UI
- Improved calendar task-management wording:
  - `Assigned To` wording
  - cleaner management/help copy
- Main files touched:
  - `frontend/src/calendar-board.jsx`
  - `apps/courses/views.py`
  - `apps/courses/templates/courses/calendar_manage_list.html`
  - `static/css/app.css`

### 17:30 to 17:40 window
- Ensured all holiday calendar filters always appear, including:
  - `India National`
  - `Hindu`
  - `Islam`
  - `Christianity`
  - `Sikhism`
  - `Buddhism`
  - `Jainism`
- Removed visible numeric badges from the holiday chips per request.
- Main files touched:
  - `apps/common/holidays.py`
  - `apps/courses/views.py`
  - `frontend/src/calendar-board.jsx`
  - `apps/courses/templates/courses/calendar_board.html`

### 17:40 to 17:50 window
- Cleaned the quiz builder:
  - removed `Department Random Distribution`
  - kept clean department assignment + specific learner assignment
  - kept section field clearly visible
  - simplified noisy builder guidance
  - improved due-date area styling
  - preserved department-level assignment logic for future learners joining that department
- Main files touched:
  - `apps/assessments/forms.py`
  - `apps/assessments/views.py`
  - `apps/assessments/templates/assessments/quiz_builder_form.html`
  - `static/css/app.css`
  - `apps/assessments/tests.py`

### 17:50 to 18:20 window
- Fixed quiz edit reliability and builder data loading:
  - existing saved questions/options preload correctly in edit mode
  - admin can edit question text, options, question type, order, and section naming
  - added `Move Up`, `Move Down`, `Delete Question`, and `Add Section` support
- Main files touched:
  - `apps/assessments/views.py`
  - `apps/assessments/templates/assessments/quiz_builder_form.html`
  - `static/js/quiz_builder.js`
  - `apps/assessments/tests.py`

### 18:20 to 18:50 window
- Fixed learner quiz submission flow:
  - UUID-based choice submission no longer crashes with `500`
  - draft save and final grading both normalize selected choice IDs safely
  - learner result page now shows:
    - each question
    - learner answer
    - correct answer
    - explanation
    - awarded marks / manual review state
- Main files touched:
  - `apps/assessments/views.py`
  - `apps/assessments/services.py`
  - `apps/assessments/templates/assessments/quiz_result.html`
  - `apps/assessments/tests.py`

### 18:50 to 19:15 window
- Simplified learner quiz wording and navigation:
  - removed extra buzz text from learner attempt state
  - moved `Previous` / `Next Question` controls into the question area for easier navigation
  - kept section-by-section learner flow intact
- Main files touched:
  - `apps/assessments/views.py`
  - `apps/assessments/templates/assessments/quiz_detail.html`
  - `apps/assessments/templates/assessments/includes/quiz_question_card.html`
  - `static/js/quiz_experience.js`
  - `static/css/app.css`

### 19:15 to 19:40 window
- Continued single-company LMS cleanup:
  - department selectors and labels no longer expose multi-company wording
  - assessment builder defaults to a single LMS company scope when user company data is incomplete
  - registration and assessment forms now show department names only
- Main files touched:
  - `apps/assessments/forms.py`
  - `apps/accounts/forms.py`
  - `apps/assessments/tests.py`
  - `apps/accounts/tests.py`

### 19:40 to 20:05 window
- Added module-level certificate support:
  - `Certificate` can now optionally link to a specific module
  - one completed module can issue one module certificate
  - course completion keeps the full-course certificate separate
  - certificate page now shows a `Module` column
- Main files touched:
  - `apps/certificates/models.py`
  - `apps/certificates/services.py`
  - `apps/certificates/views.py`
  - `apps/certificates/templates/certificates/certificate_list.html`
  - `apps/certificates/migrations/0002_certificate_module.py`
  - `apps/courses/views.py`
  - `apps/courses/tests.py`

### 20:05 to 20:30 window
- Simplified learner certificate page presentation:
  - removed heavy banner-style section heads for learner view
  - reduced oversized quiz badge styling
  - changed quiz badge area away from big card/banner styling toward a cleaner compact list
- Main files touched:
  - `apps/certificates/templates/certificates/certificate_list.html`
  - `static/css/app.css`
  - `templates/base.html`

---

## 2026-04-04 Codex Build History

### 09:30 to 10:00 window
- Verified local LMS runtime behavior again:
  - confirmed Django app can run locally on `127.0.0.1:8000`
  - identified duplicate `runserver` processes during repeated local starts
  - confirmed homepage returned HTTP `200` when server was active

### 10:00 to 10:20 window
- Expanded unit-test coverage across missing apps so every core domain has baseline tests:
  - added organization model tests
  - added messaging flow tests
  - added certificate/module-certificate tests
- New files added:
  - `apps/organizations/tests.py`
  - `apps/messaging/tests.py`
  - `apps/certificates/tests.py`
- Verified:
  - `python manage.py test apps.organizations apps.messaging apps.certificates`
  - `python manage.py check`

### 10:20 to 10:26 window
- Updated Codex-maintained project history/log files to include:
  - module-certificate work
  - certificate page UI simplification
  - new app-level unit testing additions
  - latest local run/verification notes

---

## Current State At Time Of Writing

### 2026-04-04 10:26:51
- Local project history updated through the latest Codex session.
- Django local verification and recent focused test runs completed successfully in SQLite mode.

### Active Codex-maintained history file
- This file should be updated going forward whenever major Codex work changes project behavior, UI, data flow, routing, or developer docs.
