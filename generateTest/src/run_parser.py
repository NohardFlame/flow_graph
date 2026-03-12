#!/usr/bin/env python3
"""
Parser from flow_graph app run graph API response to TestGen v1 model format.
Used by the TestGen UI "Import from run" flow: GET /runs/{run_id}/graph -> v1 model -> loadV1Model().
"""

from typing import Any, Dict, List, Optional


def _normalize_state_key(key: Any) -> Optional[str]:
    """Return non-empty string or None for null/empty."""
    if key is None:
        return None
    s = str(key).strip()
    return s if s else None


def parse_run_graph_to_model(run_graph: dict) -> dict:
    """
    Convert a RunGraphResponse-shaped dict to TestGen v1 model.

    Input: { "run_id": str, "items": [ { "action_label", "action_canonical",
            "input_state_key", "output_state_key", ... }, ... ] }
    Output: { "action name": { "init_states": list, "final_states": list, "b_value": 1 }, ... }

    For each unique action (by action_label, fallback action_canonical), merges all
    input_state_key into init_states and output_state_key into final_states.
    Null/empty state keys are skipped. Empty lists are valid (no precondition / no outcome).
    """
    items: List[dict] = run_graph.get("items") or []
    # action_name -> { init_states: set, final_states: set }
    merged: Dict[str, Dict[str, set]] = {}

    for it in items:
        name = (it.get("action_label") or it.get("action_canonical") or "").strip()
        if not name:
            continue
        if name not in merged:
            merged[name] = {"init_states": set(), "final_states": set()}

        inp = _normalize_state_key(it.get("input_state_key"))
        if inp:
            merged[name]["init_states"].add(inp)
        out = _normalize_state_key(it.get("output_state_key"))
        if out:
            merged[name]["final_states"].add(out)

    # Convert to v1 format: lists and b_value
    result: Dict[str, Dict[str, Any]] = {}
    for action_name, data in merged.items():
        result[action_name] = {
            "init_states": sorted(data["init_states"]),
            "final_states": sorted(data["final_states"]),
            "b_value": 1,
        }
    return result
