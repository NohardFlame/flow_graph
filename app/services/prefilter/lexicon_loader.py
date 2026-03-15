"""Load and validate prefilter lexicons from versioned data files. Fail fast if missing."""

from pathlib import Path

from app.core.errors import ConfigError


# Lexicon file names under lexicon_dir (all required for fail-fast)
LEXICON_FILES = [
    "action_verbs.txt",
    "permission_terms.txt",
    "restriction_terms.txt",
    "role_nouns.txt",
    "state_indicators.txt",
    "transition_indicators.txt",
    "condition_indicators.txt",
    "object_domain_terms.txt",
    "heading_relevant_terms.txt",
]
SEEDED_QUERIES_FILE = "seeded_queries.txt"


def _normalize_line(line: str) -> str | None:
    """Strip and lowercase; return None if empty or comment."""
    s = line.strip().lower()
    if not s or s.startswith("#"):
        return None
    return s


def load_lexicon_file(path: Path) -> list[str]:
    """Load one lexicon file: one phrase per line, normalized. Skip empty and # lines."""
    if not path.exists():
        raise ConfigError(f"Lexicon file not found: {path}")
    terms: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            t = _normalize_line(line)
            if t is not None:
                terms.append(t)
    return terms


def load_lexicon_file_optional(path: Path) -> list[str]:
    """Load one lexicon file if it exists; return [] if missing. Same format as load_lexicon_file."""
    if not path.exists():
        return []
    terms: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            t = _normalize_line(line)
            if t is not None:
                terms.append(t)
    return terms


def load_seeded_queries(path: Path) -> list[str]:
    """Load seeded queries for TF-IDF (one per line)."""
    if not path.exists():
        raise ConfigError(f"Seeded queries file not found: {path}")
    return load_lexicon_file(path)


def load_lexicons(lexicon_dir: str | Path) -> tuple[dict[str, list[str]], list[str]]:
    """Load all lexicons and seeded queries. Fail fast if directory or any file is missing.

    Optional Russian files (*_ru.txt) are merged into the same category if present.
    Returns:
        (lexicons_by_category, seeded_queries)
        lexicons_by_category keys are stem of filename without .txt, e.g. 'action_verbs'.
    """
    base = Path(lexicon_dir)
    if not base.is_dir():
        raise ConfigError(f"Lexicon directory not found or not a directory: {base}")

    lexicons: dict[str, list[str]] = {}
    for filename in LEXICON_FILES:
        path = base / filename
        key = filename.removesuffix(".txt")
        terms = load_lexicon_file(path)
        ru_path = base / f"{key}_ru.txt"
        terms = terms + load_lexicon_file_optional(ru_path)
        lexicons[key] = terms

    queries_path = base / SEEDED_QUERIES_FILE
    seeded_queries = load_seeded_queries(queries_path)
    ru_queries_path = base / "seeded_queries_ru.txt"
    seeded_queries = seeded_queries + load_lexicon_file_optional(ru_queries_path)

    return lexicons, seeded_queries
