"""Canonical key builders. Inputs are already normalized (slug + alias applied)."""


def build_actor_key(normalized_role_name: str) -> str:
    """Actor key: normalized role name."""
    return normalized_role_name


def build_object_key(normalized_object_name: str) -> str:
    """Object key: normalized object name."""
    return normalized_object_name


def build_action_key(normalized_verb: str, primary_object_key: str) -> str:
    """Action key: normalized_verb_<primary_object_key>. Same verb, different object -> different key."""
    return f"{normalized_verb}_{primary_object_key}"


def build_state_key(object_key: str, normalized_state_name: str) -> str:
    """State key: object_key__normalized_state_name (double underscore)."""
    return f"{object_key}__{normalized_state_name}"
