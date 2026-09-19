# Environment configuration

Copy `.env.example` to `.env` for local development. Never commit `.env`.

| Variable | Required | Purpose | Safe local value |
| --- | --- | --- | --- |
| `DEBUG` | Yes | Enables Django debug mode. | `True` |
| `SECRET_KEY` | Yes | Django cryptographic signing key. | A unique local-only value |
| `ALLOWED_HOSTS` | Yes | Comma-separated HTTP host allowlist. | `127.0.0.1,localhost` |
| `CSRF_TRUSTED_ORIGINS` | Yes | Comma-separated trusted origins. | Local HTTP origins on port 8000 |
| `SECURE_SSL_REDIRECT` | Production | Redirects HTTP to HTTPS. | `False` locally, `True` in production |
| `SECURE_HSTS_SECONDS` | Production | Enables HSTS when greater than zero. | `0` locally, `31536000` in production |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | Production | Applies HSTS to subdomains. | `False` locally, usually `True` after domain review |
| `SECURE_HSTS_PRELOAD` | Production | Opts into browser preload requirements. | `False` locally, only `True` when ready |
| `SESSION_COOKIE_SECURE` | Production | Sends session cookies only over HTTPS. | `False` locally, `True` in production |
| `CSRF_COOKIE_SECURE` | Production | Sends CSRF cookies only over HTTPS. | `False` locally, `True` in production |
| `SESSION_COOKIE_SAMESITE` | Yes | SameSite policy for session cookies. | `Lax` |
| `CSRF_COOKIE_SAMESITE` | Yes | SameSite policy for CSRF cookies. | `Lax` |
| `SECURE_REFERRER_POLICY` | Yes | Referrer header policy. | `strict-origin-when-cross-origin` |
| `X_FRAME_OPTIONS` | Yes | Clickjacking protection. | `DENY` |
| `DATABASE_ENGINE` | Yes | Selects SQLite when set to `sqlite`; any other value enables PostgreSQL settings. | `sqlite` |
| `POSTGRES_DB` | PostgreSQL only | Database name. | `lms` |
| `POSTGRES_USER` | PostgreSQL only | Database user. | `lms` |
| `POSTGRES_PASSWORD` | PostgreSQL only | Database password. | Unique local password |
| `POSTGRES_HOST` | PostgreSQL only | PostgreSQL host. | `127.0.0.1` |
| `POSTGRES_PORT` | PostgreSQL only | PostgreSQL port. | `5432` |
| `REDIS_URL` | Optional | Enables the Redis Channels layer when present. | `redis://127.0.0.1:6379/0` |
| `COMPANY_NAME` | Optional | Organization display name. | `Acme Learning` |
| `DEFAULT_FROM_EMAIL` | Optional | Default outgoing sender. | `noreply@example.com` |

Production deployments must use a unique secret, `DEBUG=False`, non-default database credentials, deployment-specific host/origin values, HTTPS, secure cookies, HSTS, and security headers.
