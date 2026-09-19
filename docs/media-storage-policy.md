# Media Storage Policy

The current LMS implementation stores uploaded media under Django `MEDIA_ROOT`, which defaults to `media/` in local development. This includes lesson files, article images, subtitles, and course comment images.

The repository does not currently include object-storage integration, bucket provisioning, media replication, or media lifecycle automation.

## Current Implementation

| Area | Current Behavior |
| --- | --- |
| Storage backend | Django local filesystem storage |
| Local path | `media/` |
| Public serving | Django serves media only when `DEBUG=True` |
| Production object storage | Not implemented |
| Media backup automation | Not implemented |

## Production Target

Production deployments should move media to persistent storage that survives container replacement.

Recommended options:

- S3-compatible object storage.
- Cloud object storage such as S3, GCS, or Azure Blob Storage.
- A persistent shared filesystem only when object storage is not available.

## Object Storage Controls

When object storage is introduced, enable:

- Versioning for recovery from accidental overwrite/delete.
- Replication to another region, bucket, or backup account.
- Lifecycle rules for old temporary files and stale derived media.
- Server-side encryption.
- Access logs or equivalent audit trails.
- Least-privilege application credentials.

## Backup Lifecycle

Media backup policy should include:

| Item | Target |
| --- | --- |
| Primary object versioning | Enabled |
| Off-site replication | Enabled for production |
| Deleted-object recovery | Retain versions or delete markers for a defined window |
| Lifecycle cleanup | Apply only to generated/temporary objects, not source uploads |
| Restore testing | Quarterly sample restore |

## Restore Testing

At least once per quarter:

1. Restore a sample article image, PDF/video lesson file, and subtitle file.
2. Verify the restored object path matches the database record.
3. Open the corresponding lesson in a staging environment.
4. Confirm browsers can fetch the restored media.
5. Record the object key, restore date, and any broken references.

## Important Boundary

Database backups do not protect media files. A usable LMS restore needs both:

- PostgreSQL data from [backup and restore policy](backup-and-restore.md).
- Media objects from this policy.
