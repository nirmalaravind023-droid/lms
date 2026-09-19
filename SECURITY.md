# Security Policy

## Reporting a vulnerability

Please do not report security vulnerabilities through public issues. Contact the repository maintainer privately through the security contact published by the hosting organization, including reproduction steps, impact, and any suggested mitigation.

Do not include credentials, personal data, database dumps, or uploaded learner content in a report.

## Supported versions

Security fixes are applied to the current `main` branch while the project is in active development. Releases are not currently versioned with a long-term support policy.

## Secret handling

- Never commit `.env` files, API tokens, database credentials, or private keys.
- Set a unique `SECRET_KEY` and disable `DEBUG` in non-development deployments.
- Treat uploaded media and database backups as sensitive data.
- Use environment-specific credentials and rotate any credential accidentally disclosed.
