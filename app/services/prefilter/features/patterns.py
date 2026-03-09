"""Token-pattern matching via spaCy Matcher. Adapter for testability."""

from __future__ import annotations

from typing import Protocol


class PatternMatcherProtocol(Protocol):
    """Protocol for token pattern matching. Implement with spaCy or fake in tests."""

    def match_patterns(self, text: str) -> list[str]:
        """Return list of pattern names that fired on the text."""
        ...


def _ensure_spacy_model(model_name: str) -> "any":
    """Load spaCy model; raise ConfigError if not available."""
    from app.core.errors import ConfigError

    try:
        import spacy
        nlp = spacy.load(model_name)
        return nlp
    except OSError as e:
        raise ConfigError(
            f"spaCy model '{model_name}' not found. Run: python -m spacy download {model_name}"
        ) from e


class SpacyPatternMatcher:
    """Use spaCy token Matcher for role+modal+action, condition+action, etc."""

    def __init__(self, model_name: str = "en_core_web_sm") -> None:
        nlp = _ensure_spacy_model(model_name)
        self._nlp = nlp
        self._matcher, self._pattern_names = self._build_matcher()

    def _build_matcher(self) -> tuple["any", list[str]]:
        from spacy.matcher import Matcher

        matcher = Matcher(self._nlp.vocab)
        pattern_names: list[str] = []

        # Pattern: "must" + verb (obligation)
        must_verb = [{"LOWER": "must"}, {"POS": "VERB"}]
        matcher.add("obligation_must_verb", [must_verb])
        pattern_names.append("obligation_must_verb")

        # Pattern: "may" + verb (permission)
        may_verb = [{"LOWER": "may"}, {"POS": "VERB"}]
        matcher.add("permission_may_verb", [may_verb])
        pattern_names.append("permission_may_verb")

        # Pattern: "shall not" / "must not" (prohibition)
        shall_not = [{"LOWER": "shall"}, {"LOWER": "not"}]
        must_not = [{"LOWER": "must"}, {"LOWER": "not"}]
        matcher.add("prohibition_shall_not", [shall_not, must_not])
        pattern_names.append("prohibition_shall_not")

        # Pattern: "if" / "when" at start of clause (condition)
        if_cond = [{"LOWER": {"in": ["if", "when", "unless"]}}]
        matcher.add("condition_if_when", [if_cond])
        pattern_names.append("condition_if_when")

        # Pattern: "user" / "admin" + "may" / "must" (role + modal)
        role_modal = [
            {"LOWER": {"in": ["user", "admin", "system", "administrator"]}},
            {"LOWER": {"in": ["may", "must", "shall", "can"]}},
        ]
        matcher.add("role_modal", [role_modal])
        pattern_names.append("role_modal")

        return matcher, pattern_names

    def match_patterns(self, text: str) -> list[str]:
        """Return pattern names that fired on the text."""
        doc = self._nlp(text[:100000])  # spaCy doc length limit
        matches = self._matcher(doc)
        seen: set[str] = set()
        result: list[str] = []
        for match_id, _start, _end in matches:
            name = self._nlp.vocab.strings[match_id]
            if name not in seen:
                seen.add(name)
                result.append(name)
        return result


class FakePatternMatcher:
    """Fake for tests: returns a fixed list of pattern names."""

    def __init__(self, patterns_to_return: list[str] | None = None) -> None:
        self._patterns = patterns_to_return or []

    def match_patterns(self, text: str) -> list[str]:
        return list(self._patterns)
