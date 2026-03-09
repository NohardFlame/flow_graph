"""Migration smoke tests: apply all migrations to empty DB."""

import subprocess
import sys
from pathlib import Path

# Project root (flow_graph)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestMigrations:
    def test_upgrade_head(self):
        """Apply all migrations (requires ENVIRONMENT and POSTGRES_* set for test DB)."""
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)

    def test_downgrade_and_upgrade(self):
        """Downgrade to base then upgrade head."""
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", "base"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
