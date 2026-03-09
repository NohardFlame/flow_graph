"""Prefilter result and structural flags for explainability and persistence."""

from dataclasses import dataclass, field

from app.core.constants import PrefilterDecision


@dataclass
class PrefilterResult:
    """Result of scoring one chunk. Serializable for prefilter_features JSONB."""

    prefilter_score: float
    decision: PrefilterDecision
    feature_breakdown: dict[str, float] = field(default_factory=dict)
    matched_terms: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)
    structural_flags: dict[str, bool | float] = field(default_factory=dict)
    lexical_score: float = 0.0
    selected_for_llm: bool = True

    def to_dict(self) -> dict:
        """Serialize for ChunkRepository prefilter_features_jsonb."""
        return {
            "prefilter_score": self.prefilter_score,
            "decision": str(self.decision),
            "feature_breakdown": self.feature_breakdown,
            "matched_terms": self.matched_terms,
            "matched_patterns": self.matched_patterns,
            "structural_flags": {k: v for k, v in self.structural_flags.items()},
            "lexical_score": self.lexical_score,
            "selected_for_llm": self.selected_for_llm,
        }

    def with_selected_for_llm(self, send: bool) -> "PrefilterResult":
        """Return a copy with selected_for_llm set."""
        return PrefilterResult(
            prefilter_score=self.prefilter_score,
            decision=self.decision,
            feature_breakdown=dict(self.feature_breakdown),
            matched_terms=list(self.matched_terms),
            matched_patterns=list(self.matched_patterns),
            structural_flags=dict(self.structural_flags),
            lexical_score=self.lexical_score,
            selected_for_llm=send,
        )
