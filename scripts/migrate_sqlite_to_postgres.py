from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = REPO_ROOT / "db.sqlite3"
DEFAULT_FIXTURE_PATH = REPO_ROOT / ".migration-fixtures" / "sqlite-to-postgres.json"

COUNT_SCRIPT = """
import json
from django.apps import apps

excluded = {"auth.Permission", "contenttypes.ContentType"}
counts = {}
for model in apps.get_models():
    label = model._meta.label
    if label in excluded:
        continue
    counts[label] = model.objects.count()
print(json.dumps(counts, sort_keys=True))
"""


def run_manage(args: list[str], *, database_engine: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_ENGINE"] = database_engine
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "manage.py"), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def require_success(result: subprocess.CompletedProcess[str], step: str) -> None:
    if result.returncode == 0:
        if result.stdout.strip():
            print(result.stdout.strip())
        return

    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    raise SystemExit(f"{step} failed with exit code {result.returncode}. SQLite was not removed.")


def get_counts(database_engine: str) -> dict[str, int]:
    result = run_manage(["shell", "-c", COUNT_SCRIPT], database_engine=database_engine)
    require_success(result, f"Counting rows in {database_engine}")
    output = result.stdout.strip().splitlines()[-1]
    return json.loads(output)


def compare_counts(sqlite_counts: dict[str, int], postgres_counts: dict[str, int]) -> None:
    mismatches = {
        label: {"sqlite": sqlite_count, "postgres": postgres_counts.get(label)}
        for label, sqlite_count in sqlite_counts.items()
        if postgres_counts.get(label) != sqlite_count
    }
    if mismatches:
        print(json.dumps(mismatches, indent=2, sort_keys=True), file=sys.stderr)
        raise SystemExit("Imported row counts do not match SQLite. SQLite was not removed.")


def archive_sqlite(sqlite_path: Path) -> Path:
    backup_dir = REPO_ROOT / ".db-backups"
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    archive_path = backup_dir / f"{sqlite_path.name}.{timestamp}.bak"
    shutil.move(str(sqlite_path), archive_path)
    return archive_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export the local SQLite LMS database, import it into PostgreSQL, "
            "verify row counts, and optionally archive the SQLite file."
        )
    )
    parser.add_argument("--sqlite-path", type=Path, default=DEFAULT_SQLITE_PATH)
    parser.add_argument("--fixture-path", type=Path, default=DEFAULT_FIXTURE_PATH)
    parser.add_argument(
        "--archive-sqlite-after-import",
        action="store_true",
        help="Move db.sqlite3 to .db-backups only after PostgreSQL import verification succeeds.",
    )
    parser.add_argument(
        "--keep-fixture",
        action="store_true",
        help="Keep the temporary JSON fixture after a successful import.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sqlite_path = args.sqlite_path.resolve()
    fixture_path = args.fixture_path.resolve()

    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")

    fixture_path.parent.mkdir(parents=True, exist_ok=True)

    print("Counting SQLite rows...")
    sqlite_counts = get_counts("sqlite")

    print(f"Exporting SQLite data to {fixture_path}...")
    dump = run_manage(
        [
            "dumpdata",
            "--natural-foreign",
            "--natural-primary",
            "--exclude",
            "contenttypes",
            "--exclude",
            "auth.permission",
            "--output",
            str(fixture_path),
        ],
        database_engine="sqlite",
    )
    require_success(dump, "SQLite export")

    print("Applying PostgreSQL migrations...")
    migrate = run_manage(["migrate", "--noinput"], database_engine="postgresql")
    require_success(migrate, "PostgreSQL migrate")

    print("Importing data into PostgreSQL...")
    load = run_manage(["loaddata", str(fixture_path)], database_engine="postgresql")
    require_success(load, "PostgreSQL import")

    print("Verifying PostgreSQL row counts...")
    postgres_counts = get_counts("postgresql")
    compare_counts(sqlite_counts, postgres_counts)

    if args.archive_sqlite_after_import:
        archive_path = archive_sqlite(sqlite_path)
        print(f"SQLite database archived at {archive_path}")
    else:
        print("SQLite database kept. Re-run with --archive-sqlite-after-import to remove it after verification.")

    if not args.keep_fixture and fixture_path.exists():
        fixture_path.unlink()
        print(f"Removed temporary fixture {fixture_path}")

    print("SQLite to PostgreSQL migration completed and verified.")


if __name__ == "__main__":
    main()
