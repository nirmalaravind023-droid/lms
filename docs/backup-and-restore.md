# Backup And Restore Policy

This document describes the production backup target state. The current repository does not include an automated backup job, scheduler, or managed backup service configuration yet.

## PostgreSQL Backups

Production deployments should back up PostgreSQL daily at minimum. Backups must be stored outside the application container and outside the database host.

Recommended minimum controls:

- Daily logical backup with `pg_dump` or managed PostgreSQL snapshots.
- Backup retention policy with short-term and long-term windows.
- Encryption at rest for every backup artifact.
- Off-server storage in object storage, backup storage, or a managed backup service.
- Restore testing on a recurring schedule.

## Suggested Retention

| Backup Type | Frequency | Retention |
| --- | --- | --- |
| Daily | Every 24 hours | 14 days |
| Weekly | Once per week | 8 weeks |
| Monthly | Once per month | 12 months |

Adjust the retention window for company policy, legal requirements, and available storage budget.

## Encryption

Backups should be encrypted before leaving the database host or encrypted by the managed backup service. Encryption keys must not be committed to this repository.

Acceptable key locations:

- Cloud KMS.
- Docker secrets.
- Server environment managed by operations.
- Dedicated secrets manager.

## Restore Testing

A backup policy is incomplete until restores are tested. At least once per quarter:

1. Restore the latest production backup into an isolated environment.
2. Run `python manage.py migrate --check` or the closest supported schema check.
3. Sign in with a non-production test/admin account.
4. Verify users, courses, assessments, certificates, messages, and audit rows are readable.
5. Record the restore date, backup identifier, operator, and issues found.

## Application Data To Include

PostgreSQL backups cover relational data:

- Users, organizations, departments.
- Courses, modules, lessons, enrollments, progress.
- Assessments, questions, attempts, answers.
- Certificates and certificate records.
- Conversations and messages.
- Audit logs and analytics events.

PostgreSQL backups do not include uploaded media files stored under `MEDIA_ROOT`. Media backup is covered separately in [media storage policy](media-storage-policy.md).
