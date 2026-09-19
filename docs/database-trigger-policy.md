# Database Trigger Policy

Normal LMS business logic stays in Django services, models, and views. Do not move course completion, quiz grading, certificate generation, notifications, enrollment, authorization, or email behavior into database triggers.

## Allowed Trigger Candidates

Use database triggers only when the database itself must enforce or protect data independently of application code:

- Audit timestamps when Django-managed timestamps are not enough.
- Immutable audit rows, if audit tampering becomes a demonstrated risk.
- Critical integrity rules that cannot be expressed safely with Django constraints.

## Keep In Django

| Workflow | Owner |
| --- | --- |
| Course completion | `apps.courses` services |
| Quiz grading | `apps.assessments` services |
| Certificate generation | `apps.certificates` services |
| Notifications | Owning app service layer |
| Enrollment | `apps.courses` / `apps.accounts` services |
| Authorization | View mixins, permission helpers, services |
| Emails | Mail service or task layer |

## Review Rule

Any proposed database trigger must document:

- The integrity risk it protects.
- Why Django constraints or service transactions are not sufficient.
- How it behaves on SQLite local development and PostgreSQL production.
- How it is tested and rolled back.
