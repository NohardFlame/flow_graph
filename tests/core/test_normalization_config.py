"""Config loader: alias/rewrite files and reserved words."""

from pathlib import Path

import pytest

from app.core.errors import ConfigError
from app.core.normalization_config import (
    load_alias_file,
    load_normalization_config,
    load_reserved_file,
    load_version_file,
)
from tests.fixtures.normalization_fixtures import get_fixture_config_dir


def test_load_alias_file_missing_returns_empty() -> None:
    path = Path("/nonexistent/role_aliases.txt")
    assert load_alias_file(path) == {}


def test_load_alias_file_parses_arrow_and_equals() -> None:
    fixture_dir = get_fixture_config_dir()
    role_path = fixture_dir / "role_aliases.txt"
    result = load_alias_file(role_path)
    assert result["user"] == "applicant"
    assert result["admin"] == "administrator"


def test_load_alias_file_normalizes_to_slug() -> None:
    """Keys and values are normalized to slug form when loaded."""
    fixture_dir = get_fixture_config_dir()
    obj_path = fixture_dir / "object_aliases.txt"
    result = load_alias_file(obj_path)
    assert "form" in result
    assert result["form"] == "application_form"
    assert result["doc"] == "document"


def test_load_reserved_file_missing_returns_empty_set() -> None:
    assert load_reserved_file(Path("/nonexistent/reserved.txt")) == set()


def test_load_reserved_file_parses_lines() -> None:
    fixture_dir = get_fixture_config_dir()
    path = fixture_dir / "reserved.txt"
    result = load_reserved_file(path)
    assert "reserved_word" in result
    assert "banned" in result


def test_load_version_file() -> None:
    fixture_dir = get_fixture_config_dir()
    path = fixture_dir / "version.txt"
    assert load_version_file(path) == "fixture_v1"


def test_load_version_file_missing_returns_empty() -> None:
    assert load_version_file(Path("/nonexistent/version.txt")) == ""


def test_load_normalization_config_from_fixture_dir() -> None:
    fixture_dir = get_fixture_config_dir()
    config = load_normalization_config(fixture_dir, require_dir=True)
    assert config.version == "fixture_v1"
    assert config.resolve_role("user") == "applicant"
    assert config.resolve_object("form") == "application_form"
    assert config.resolve_verb("send") == "submit"
    assert config.is_reserved("reserved_word")
    assert config.is_reserved("banned")
    assert not config.is_reserved("unknown")


def test_load_normalization_config_nonexistent_dir_raises_when_required() -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_normalization_config("/nonexistent/normalization", require_dir=True)


def test_load_normalization_config_nonexistent_dir_optional_returns_empty() -> None:
    config = load_normalization_config(
        "/nonexistent/normalization", require_dir=False, version_override="v0"
    )
    assert config.version == "v0"
    assert config.role_aliases == {}
    assert config.reserved == set()


def test_load_normalization_config_version_override() -> None:
    fixture_dir = get_fixture_config_dir()
    config = load_normalization_config(fixture_dir, version_override="overridden")
    assert config.version == "overridden"
