# Contributing

Thanks for improving Python LMS Foundation.

## Development setup

Follow the local setup instructions in [README.md](README.md). Use a virtual environment, copy `.env.example` to an untracked `.env`, and use SQLite unless the work requires PostgreSQL or Redis.

## Workflow

1. Fork the repository and create a branch from `main`.
2. Use a focused branch name, such as `feat/calendar-filter` or `fix/quiz-score`.
3. Keep changes scoped and preserve Django migrations unless a model change requires one.
4. Add or update tests with behavior changes.
5. Run the validation commands below before opening a pull request.

## Validation

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check
```

When changing `frontend/src/calendar-board.jsx`, also run:

```bash
npm ci
npm run build:calendar
```

## Code standards

- Prefer small, domain-focused changes in the appropriate Django app.
- Keep authorization and organization scoping explicit in views and services.
- Do not commit `.env`, SQLite databases, media uploads, logs, virtual environments, dependency directories, or generated local build output.
- Write clear commit messages using a concise prefix such as `feat:`, `fix:`, `docs:`, `test:`, or `chore:`.

## Pull requests

Explain the problem, solution, tests run, and any migration or configuration impact. Keep pull requests reviewable; separate unrelated refactors from behavior changes.

## Labels and newcomer work

Maintainers use `good first issue` for well-scoped tasks with clear guidance, `help wanted` for work where community contributions are especially useful, and `needs triage` for new reports awaiting review. Before starting a labelled issue, comment that you intend to work on it so effort is not duplicated.
