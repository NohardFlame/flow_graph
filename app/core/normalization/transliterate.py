"""Transliteration adapter: map non-ASCII to controlled ASCII for deterministic slugs.

Production uses unidecode when available; tests can inject a no-op or deterministic stub.
"""

from typing import Protocol


class TransliterateProtocol(Protocol):
    """Transliterate text to ASCII for slug generation. Same input -> same output."""

    def __call__(self, text: str) -> str: ...


def _unidecode_transliterate(text: str) -> str:
    """Use unidecode if available, else return as-is."""
    try:
        from unidecode import unidecode
        return unidecode(text)
    except ImportError:
        return text


def default_transliterate(text: str) -> str:
    """Default transliteration: unidecode when installed, else identity. Deterministic."""
    return _unidecode_transliterate(text)


def noop_transliterate(text: str) -> str:
    """No-op for tests: return input unchanged."""
    return text
