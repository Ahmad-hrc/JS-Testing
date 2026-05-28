"""Rollout initiative name resolver — fuzzy-matches user input to registered names."""

import difflib
import logging

logger = logging.getLogger(__name__)


def resolve_rollout_name(user_input: str, registered_names: list[str]) -> tuple[str | None, bool]:
    """Resolve a user-provided rollout name to a registered initiative.

    Returns:
        (resolved_name, is_exact) — resolved_name is None if no match found.
    """
    if not registered_names:
        return None, False

    normalized_input = user_input.strip().lower()

    # Exact match (case-insensitive)
    for name in registered_names:
        if name.lower() == normalized_input:
            return name, True

    # Fuzzy match
    close = difflib.get_close_matches(normalized_input, [n.lower() for n in registered_names], n=1, cutoff=0.6)
    if close:
        for name in registered_names:
            if name.lower() == close[0]:
                return name, False

    return None, False
