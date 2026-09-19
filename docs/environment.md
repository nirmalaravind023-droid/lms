# Environment configuration

Copy `.env.example` to `.env` for local development. Never commit `.env`.

| Variable | Required | Purpose | Safe local value |
| --- | --- | --- | --- |
| `DEBUG` | Yes | Enables Django debug mode. | `True` |
| `SECRET_KEY` | Yes | Django cryptographic signing key. | A unique local-only value |
| `ALLOWED_HOSTS` | Yes | Comma-separated HTTP host allowlist. | `127.0.0.1,localhost` |
| `CSRF_TRUSTED_ORIGINS` | Yes | Comma-separated trusted origins. | Local HTTP origins on port 8000 |
| `DATABASE_ENGINE` | Yes | Selects SQLite when set to `sqlite`; any other value enables PostgreSQL settings. | `sqlite` |
| `POSTGRES_DB` | PostgreSQL only | Database name. | `lms` |
| `POSTGRES_USER` | PostgreSQL only | Database user. | `lms` |
| `POSTGRES_PASSWORD` | PostgreSQL only | Database password. | Unique local password |
| `POSTGRES_HOST` | PostgreSQL only | PostgreSQL host. | `127.0.0.1` |
| `POSTGRES_PORT` | PostgreSQL only | PostgreSQL port. | `5432` |
| `REDIS_URL` | Optional | Enables the Redis Channels layer when present. | `redis://127.0.0.1:6379/0` |
| `COMPANY_NAME` | Optional | Organization display name. | `Acme Learning` |
| `DEFAULT_FROM_EMAIL` | Optional | Default outgoing sender. | `noreply@example.com` |

Production deployments must use a unique secret, `DEBUG=False`, non-default database credentials, and deployment-specific host/origin values.

## Docker Compose database selection

The checked-in `.env.example` keeps `DATABASE_ENGINE=sqlite` because that is the lightest local setup outside Docker. `docker-compose.yml` overrides the database variables for the `web` and `streamlit` services so containers use PostgreSQL through the Compose service name `db` and Redis through the service name `redis`.

For Docker Compose, keep the `POSTGRES_*` values aligned between the `db`, `web`, and `streamlit` services. Override the credentials from your shell or `.env` when needed, but do not change `POSTGRES_HOST=db` inside Compose unless the database runs outside the Compose network.
