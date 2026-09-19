# Modular Monolith Boundaries

This project remains a Django monolith, but each domain app should behave like a clear module. Cross-module access should happen through models for data ownership, selectors for reads, services for writes, and events for side effects.

## Modules

| Module | Current package | Owns |
| --- | --- | --- |
| Organizations | `apps.organizations` | Companies, departments, organization metadata |
| Accounts | `apps.accounts` | Users, roles, authentication, lifecycle requests |
| Courses | `apps.courses` | Courses, modules, lessons, enrollments, progress, calendar events, course notifications |
| Assessments | `apps.assessments` | Quizzes, questions, choices, assignments, attempts, answers |
| Certificates | `apps.certificates` | Certificate templates and issued certificates |
| Messaging | `apps.messaging` | Conversations, participants, messages, chat WebSocket handling |
| Analytics | `apps.analytics` | Dashboard read models and derived metrics |
| Common | `apps.common` | Shared base models, audit logs, pagination, search, holidays |

## Dependency Rules

- Views should coordinate request/response work only.
- Business writes should live in `services.py`.
- Reusable reads should live in `selectors.py`.
- Permission decisions should move toward `permissions.py` as modules grow.
- Domain-specific failures should move toward `exceptions.py` instead of bare `ValueError`.
- Cross-module side effects should be expressed through service calls now and domain events later.
- Shared helpers in `apps.common` must stay generic; domain rules belong in the owning app.

## First Refactor Targets

| Target | Reason | Direction |
| --- | --- | --- |
| Course reorder authorization | Prevent cross-company writes | Courses permission/service boundary |
| Quiz create/update flow | Large view methods mix validation, assignments, calendar sync, and audit logging | Assessment services/selectors |
| User lifecycle approval | Several write operations must succeed together | Account service with transaction boundary |
| Certificate issuance | Certificate file path is recorded separately from rendering | Certificate service and storage boundary |
| Calendar board data | Large read assembly in a view | Course selector/read-model function |

## Database Rule

Database constraints and indexes should be added from observed model relationships and query usage, not from guesses. Nullable assignment targets need explicit product decisions before enforcing uniqueness.
