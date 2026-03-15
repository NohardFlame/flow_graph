# Tests

## Database tests (API, DB, workers)

Tests use a **real PostgreSQL** database. Set `POSTGRES_*` (and optionally `ENVIRONMENT=test`).

### "column source_parts_jsonb does not exist" / "relation documents does not exist"

The schema must match the code. After pulling changes that add migrations (e.g. migration 002), apply them:

```bash
# With your Postgres env (e.g. POSTGRES_DB=app_test, POSTGRES_USER, POSTGRES_PASSWORD, etc.)
alembic upgrade head
```

Then run tests (same env):

```bash
pytest tests/ -v
```

If the test DB is empty, `alembic upgrade head` creates all tables. If it already had migration 001, it adds the new columns (e.g. `source_parts_jsonb` on `document_versions`).
