#!/usr/bin/env python3
"""
Tests for run_parser: flow_graph run graph response -> TestGen v1 model.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.run_parser import parse_run_graph_to_model


def test_empty_items():
    """Empty items returns empty v1 model."""
    out = parse_run_graph_to_model({"run_id": "r1", "items": []})
    assert out == {}


def test_single_action_no_states():
    """Single action with no state keys gets empty init_states and final_states."""
    run_graph = {
        "run_id": "r1",
        "items": [
            {
                "id": "a1",
                "action_label": "Create document",
                "action_canonical": "create_document",
                "input_state_key": None,
                "output_state_key": None,
            }
        ],
    }
    out = parse_run_graph_to_model(run_graph)
    assert out == {
        "Create document": {
            "init_states": [],
            "final_states": [],
            "b_value": 1,
        }
    }


def test_single_action_with_states():
    """Single action with input/output states maps correctly."""
    run_graph = {
        "run_id": "r1",
        "items": [
            {
                "id": "a1",
                "action_label": "Submit form",
                "input_state_key": "form open",
                "output_state_key": "form submitted",
            }
        ],
    }
    out = parse_run_graph_to_model(run_graph)
    assert out == {
        "Submit form": {
            "init_states": ["form open"],
            "final_states": ["form submitted"],
            "b_value": 1,
        }
    }


def test_deduplication_same_action_twice():
    """Same action twice merges init_states and final_states."""
    run_graph = {
        "run_id": "r1",
        "items": [
            {
                "id": "a1",
                "action_label": "Click",
                "input_state_key": "page A",
                "output_state_key": "page B",
            },
            {
                "id": "a2",
                "action_label": "Click",
                "input_state_key": "page B",
                "output_state_key": "page C",
            },
        ],
    }
    out = parse_run_graph_to_model(run_graph)
    assert out == {
        "Click": {
            "init_states": ["page A", "page B"],
            "final_states": ["page B", "page C"],
            "b_value": 1,
        }
    }


def test_fallback_action_canonical():
    """Missing action_label uses action_canonical."""
    run_graph = {
        "run_id": "r1",
        "items": [
            {
                "id": "a1",
                "action_label": "",
                "action_canonical": "open_menu",
                "input_state_key": "home",
                "output_state_key": "menu open",
            }
        ],
    }
    out = parse_run_graph_to_model(run_graph)
    assert "open_menu" in out
    assert out["open_menu"]["init_states"] == ["home"]
    assert out["open_menu"]["final_states"] == ["menu open"]


def test_skips_empty_state_keys():
    """Null and empty string state keys are skipped."""
    run_graph = {
        "run_id": "r1",
        "items": [
            {
                "id": "a1",
                "action_label": "Do",
                "input_state_key": None,
                "output_state_key": "  ",
            }
        ],
    }
    out = parse_run_graph_to_model(run_graph)
    assert out == {
        "Do": {
            "init_states": [],
            "final_states": [],
            "b_value": 1,
        }
    }


def test_multiple_actions():
    """Multiple distinct actions produce multiple v1 entries."""
    run_graph = {
        "run_id": "r1",
        "items": [
            {"action_label": "A", "input_state_key": "s0", "output_state_key": "s1"},
            {"action_label": "B", "input_state_key": "s1", "output_state_key": "s2"},
            {"action_label": "C", "input_state_key": "s2", "output_state_key": "s3"},
        ],
    }
    out = parse_run_graph_to_model(run_graph)
    assert set(out.keys()) == {"A", "B", "C"}
    assert out["A"]["init_states"] == ["s0"] and out["A"]["final_states"] == ["s1"]
    assert out["B"]["init_states"] == ["s1"] and out["B"]["final_states"] == ["s2"]
    assert out["C"]["init_states"] == ["s2"] and out["C"]["final_states"] == ["s3"]


if __name__ == "__main__":
    test_empty_items()
    test_single_action_no_states()
    test_single_action_with_states()
    test_deduplication_same_action_twice()
    test_fallback_action_canonical()
    test_skips_empty_state_keys()
    test_multiple_actions()
    print("All run_parser tests passed.")
