# Production Deployment Notes

The development stack uses Django's development server. Production should keep ASGI support because chat uses Django Channels and WebSockets.

## Recommended Web Stack

```text
Client
  -> TLS terminator / load balancer
  -> Nginx
  -> Daphne
  -> Django ASGI
```

Use Let's Encrypt or infrastructure-managed TLS and enforce HTTP to HTTPS redirects.

## Services

Minimum production services:

- `nginx` for TLS termination, static files, media strategy, and WebSocket proxying.
- `web` running `daphne lms_portal.asgi:application`.
- `db` running PostgreSQL.
- `redis` for Django Channels.

Do not add `celery` or `celery-beat` containers until the project contains Celery dependencies, a Celery app, and real worker tasks.

## Docker

`Dockerfile` remains the local development image. `Dockerfile.prod` is the production-oriented image:

- Uses a wheel-building stage.
- Runs as a non-root `lms` user.
- Runs Daphne instead of Django's development server.
- Runs `collectstatic` during image build.
- Includes a simple HTTP healthcheck.

Example build:

```bash
docker build -f Dockerfile.prod -t lms:prod .
```

## Secrets

Never commit:

- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `SMTP_PASSWORD`
- cloud access keys
- API keys

Development may use `.env`. Production should use Docker secrets, cloud secrets manager, or server environment variables.

## Static And Media

Serve `staticfiles/` through Nginx or an object storage/CDN setup. User-uploaded media should use a persistent volume or object storage; do not store production media only inside ephemeral containers.

## Monitoring

Separate logs by responsibility:

- Application logs
- Security logs
- Audit logs
- Worker logs, once workers exist
- Nginx access/error logs
- Database logs and slow-query logs
