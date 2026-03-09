"""Load versioned alias/rewrite and reserved-word config from files.

File format: one mapping per line as 'alias -> canonical' or 'alias=canonical'.
Keys and values are normalized to slug form when loaded for deterministic lookup.
Comment lines start with #. Reserved file: one word per line (stored as slug).
"""

from dataclasses import dataclass
from pathlib import Path

from app.core.errors import ConfigError
from app.core.normalization.slug import slugify


ALIAS_FILES = {
    "role_aliases": "role_aliases.txt",
    "object_aliases": "object_aliases.txt",
    "verb_rewrites": "verb_rewrites.txt",
    "state_rewrites": "state_rewrites.txt",
}
RESERVED_FILE = "reserved.txt"
VERSION_FILE = "version.txt"


def _parse_mapping_line(line: str) -> tuple[str, str] | None:
    """Parse 'alias -> canonical' or 'alias=canonical'. Returns (key_slug, value_slug) or None."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "->" in line:
        parts = line.split("->", 1)
    elif "=" in line:
        parts = line.split("=", 1)
    else:
        return None
    if len(parts) != 2:
        return None
    left, right = parts[0].strip(), parts[1].strip()
    if not left:
        return None
    key = slugify(left)
    value = slugify(right)
    if not key:
        return None
    return (key, value if value else key)


def load_alias_file(path: Path) -> dict[str, str]:
    """Load one alias/rewrite file. Returns dict mapping key_slug -> value_slug."""
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            pair = _parse_mapping_line(line)
            if pair:
                result[pair[0]] = pair[1]
    return result


def load_reserved_file(path: Path) -> set[str]:
    """Load reserved words (one per line, normalized to slug)."""
    if not path.exists():
        return set()
    result: set[str] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                result.add(slugify(s))
    return result


def load_version_file(path: Path) -> str:
    """Load normalization version from first non-empty line."""
    if not path.exists():
        return ""
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                return s
    return ""


@dataclass
class NormalizationConfig:
    """In-memory alias/rewrite and reserved sets. Keys are slug-normalized for lookup."""

    role_aliases: dict[str, str]
    object_aliases: dict[str, str]
    verb_rewrites: dict[str, str]
    state_rewrites: dict[str, str]
    reserved: set[str]
    version: str

    def resolve_role(self, slug: str) -> str:
        return self.role_aliases.get(slug, slug)

    def resolve_object(self, slug: str) -> str:
        return self.object_aliases.get(slug, slug)

    def resolve_verb(self, slug: str) -> str:
        return self.verb_rewrites.get(slug, slug)

    def resolve_state(self, slug: str) -> str:
        return self.state_rewrites.get(slug, slug)

    def is_reserved(self, slug: str) -> bool:
        return slug in self.reserved


def load_normalization_config(
    config_dir: str | Path,
    *,
    version_override: str | None = None,
    require_dir: bool = True,
) -> NormalizationConfig:
    """Load all normalization config from a directory.

    If require_dir is False and directory does not exist, returns config with empty
    aliases/reserved and version from version_override or ''.
    """
    base = Path(config_dir)
    if require_dir and not base.is_dir():
        raise ConfigError(f"Normalization config directory not found: {base}")

    if not base.is_dir():
        return NormalizationConfig(
            role_aliases={},
            object_aliases={},
            verb_rewrites={},
            state_rewrites={},
            reserved=set(),
            version=version_override or "",
        )

    role_aliases = load_alias_file(base / ALIAS_FILES["role_aliases"])
    object_aliases = load_alias_file(base / ALIAS_FILES["object_aliases"])
    verb_rewrites = load_alias_file(base / ALIAS_FILES["verb_rewrites"])
    state_rewrites = load_alias_file(base / ALIAS_FILES["state_rewrites"])
    reserved = load_reserved_file(base / RESERVED_FILE)
    version = version_override if version_override is not None else load_version_file(base / VERSION_FILE)

    return NormalizationConfig(
        role_aliases=role_aliases,
        object_aliases=object_aliases,
        verb_rewrites=verb_rewrites,
        state_rewrites=state_rewrites,
        reserved=reserved,
        version=version or "v1",
    )
