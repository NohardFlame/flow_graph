"""Prefilter service: score chunks and produce keep/gray/reject with explainability."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config.settings import PrefilterSettings
from app.core.errors import ConfigError
from app.domain.parse_models import ExtractionChunk
from app.services.prefilter.features.context_boost import context_boost_score
from app.services.prefilter.features.exact_match import find_matches
from app.services.prefilter.features.lexical import lexical_scores
from app.services.prefilter.features.patterns import FakePatternMatcher, PatternMatcherProtocol, SpacyPatternMatcher
from app.services.prefilter.features.structural import structural_features
from app.services.prefilter.gray_zone import apply_gray_policy
from app.services.prefilter.lexicon_loader import load_lexicons
from app.services.prefilter.prefilter_models import PrefilterResult
from app.services.prefilter.scoring import apply_weights, thresholds_to_decision


class PrefilterService:
    """Score extraction chunks using deterministic features. Fail fast at init if resources missing."""

    def __init__(
        self,
        settings: PrefilterSettings | None = None,
        *,
        lexicon_dir: str | Path | None = None,
        pattern_matcher: PatternMatcherProtocol | None = None,
    ) -> None:
        from app.config.settings import get_settings

        self._settings = settings or get_settings().prefilter
        base = Path(lexicon_dir or self._settings.lexicon_dir)
        if not base.is_absolute():
            # Resolve relative to cwd (tests can set cwd or pass absolute path)
            base = Path.cwd() / base
        self._lexicons, self._seeded_queries = load_lexicons(base)

        if pattern_matcher is not None:
            self._pattern_matcher = pattern_matcher
        elif self._settings.enable_pattern_matching:
            self._pattern_matcher = SpacyPatternMatcher(self._settings.spacy_model)
        else:
            self._pattern_matcher = FakePatternMatcher([])

        self._heading_relevant = self._lexicons.get("heading_relevant_terms", [])
        self._structural_weights = {
            "heading_relevant": self._settings.weight_structural_heading,
            "has_table_list": self._settings.weight_structural_table_list,
            "depth_score": self._settings.weight_structural_depth,
            "appendix_penalty": self._settings.weight_structural_appendix_penalty,
        }

    def score_chunks(
        self,
        chunks: list[ExtractionChunk],
        *,
        apply_gray_policy_flag: bool = True,
    ) -> list[PrefilterResult]:
        """Score each chunk and return PrefilterResult per chunk. Optionally apply gray-zone policy."""
        if not chunks:
            return []

        chunk_texts = [c.chunk_text for c in chunks]
        lexical_list = lexical_scores(chunk_texts, self._seeded_queries)

        results: list[PrefilterResult] = []
        for i, chunk in enumerate(chunks):
            text_for_match = chunk.chunk_text
            if chunk.section_path:
                text_for_match = " ".join(chunk.section_path) + " " + chunk.chunk_text

            struct_components, struct_flags = structural_features(chunk, self._heading_relevant)
            matched_terms, exact_counts = find_matches(text_for_match, self._lexicons)
            pattern_names = self._pattern_matcher.match_patterns(chunk.chunk_text)

            context = context_boost_score(
                chunk.chunk_text,
                action_terms=self._lexicons.get("action_verbs", []),
                object_terms=self._lexicons.get("object_domain_terms", []),
                modal_restriction_terms=self._lexicons.get("permission_terms", []) + self._lexicons.get("restriction_terms", []),
                role_terms=self._lexicons.get("role_nouns", []),
                state_terms=self._lexicons.get("state_indicators", []),
            )

            score, breakdown = apply_weights(
                struct_components,
                self._structural_weights,
                exact_counts,
                self._settings.weight_exact_match,
                len(pattern_names),
                self._settings.weight_pattern,
                context,
                self._settings.weight_context_boost,
                lexical_list[i] if i < len(lexical_list) else 0.0,
                self._settings.weight_lexical,
            )

            decision = thresholds_to_decision(
                score,
                self._settings.accept_threshold,
                self._settings.gray_threshold,
            )

            results.append(
                PrefilterResult(
                    prefilter_score=score,
                    decision=decision,
                    feature_breakdown=breakdown,
                    matched_terms=matched_terms,
                    matched_patterns=pattern_names,
                    structural_flags=struct_flags,
                    lexical_score=lexical_list[i] if i < len(lexical_list) else 0.0,
                    selected_for_llm=decision.value != "reject",  # gray policy may set gray to False
                )
            )

        if apply_gray_policy_flag:
            results = apply_gray_policy(
                results,
                top_gray_budget=self._settings.top_gray_budget_per_document,
                adjacent_to_accepted=self._settings.gray_adjacent_to_accepted,
            )

        return results
