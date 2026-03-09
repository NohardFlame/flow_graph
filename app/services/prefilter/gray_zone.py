"""Gray-zone policy: which gray chunks to send (top-N or adjacent to accepted)."""

from __future__ import annotations

from app.services.prefilter.prefilter_models import PrefilterResult


def apply_gray_policy(
    results: list[PrefilterResult],
    *,
    top_gray_budget: int,
    adjacent_to_accepted: bool,
) -> list[PrefilterResult]:
    """Set selected_for_llm on each result: keep always True, reject False, gray by policy.

    Does not mutate decision; callers can use selected_for_llm to decide which chunks
    to send to the LLM. If selected_for_llm is not present, we add it to the result
    by returning new result objects (PrefilterResult is a dataclass; we need to add
    the field or return a wrapper). PrefilterResult currently has no selected_for_llm.
    So we will add it to the dataclass and set it here.
    """
    from app.core.constants import PrefilterDecision

    keep_indices = {i for i, r in enumerate(results) if r.decision == PrefilterDecision.KEEP}
    gray_indices = [i for i, r in enumerate(results) if r.decision == PrefilterDecision.GRAY]

    # Which gray chunks are adjacent to an accepted chunk?
    adjacent_gray = set()
    if adjacent_to_accepted:
        for i in gray_indices:
            if (i - 1) in keep_indices or (i + 1) in keep_indices:
                adjacent_gray.add(i)

    # Top-N gray by score (among grays)
    gray_with_score = [(i, results[i].prefilter_score) for i in gray_indices]
    gray_with_score.sort(key=lambda x: -x[1])
    top_n_indices = {gray_with_score[j][0] for j in range(min(top_gray_budget, len(gray_with_score)))}

    selected_gray = adjacent_gray | top_n_indices

    out: list[PrefilterResult] = []
    for i, r in enumerate(results):
        if r.decision == PrefilterDecision.KEEP:
            send = True
        elif r.decision == PrefilterDecision.REJECT:
            send = False
        else:
            send = i in selected_gray
        # PrefilterResult has no selected_for_llm yet; add it
        out.append(_with_selected(r, send))
    return out


def _with_selected(r: PrefilterResult, send: bool) -> PrefilterResult:
    """Return a copy of r with selected_for_llm set."""
    return r.with_selected_for_llm(send)
