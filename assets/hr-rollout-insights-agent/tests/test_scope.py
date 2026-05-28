"""Unit tests for list_rollout_initiatives tool and RolloutRegistry."""

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("IBD_TESTING", "1")


def test_list_rollout_initiatives_empty_registry():
    """list_rollout_initiatives returns helpful message when no initiatives exist."""
    from registry import RolloutRegistry
    from tools.scope import list_rollout_initiatives

    registry = RolloutRegistry()
    with patch("tools.scope.get_registry", return_value=registry):
        result = list_rollout_initiatives.invoke({})

    assert "No rollout initiatives" in result
    assert "ingest" in result.lower()


def test_list_rollout_initiatives_with_registered():
    """list_rollout_initiatives lists all registered initiatives with doc counts."""
    from registry import RolloutRegistry, RolloutInitiative
    from tools.scope import list_rollout_initiatives

    registry = RolloutRegistry()
    i1 = RolloutInitiative(name="Onboarding Q4", sources=[])
    i1.doc_count = 5
    i2 = RolloutInitiative(name="Performance Goals", sources=[])
    i2.doc_count = 3
    registry.register(i1)
    registry.register(i2)

    with patch("tools.scope.get_registry", return_value=registry):
        result = list_rollout_initiatives.invoke({})

    assert "Onboarding Q4" in result
    assert "Performance Goals" in result
    assert "5" in result
    assert "3" in result


def test_registry_scoping_in_vector_store():
    """VectorStore correctly scopes searches to the specified rollout name."""
    from ingestion.vector_store import VectorStore, Chunk

    store = VectorStore()
    chunk_a = Chunk(
        text="Rollout A content.",
        source_doc="a.txt",
        section="S1",
        rollout_name="Rollout A",
        embedding=[1.0] + [0.0] * 1535,
    )
    chunk_b = Chunk(
        text="Rollout B content.",
        source_doc="b.txt",
        section="S1",
        rollout_name="Rollout B",
        embedding=[0.0, 1.0] + [0.0] * 1534,
    )
    store.upsert([chunk_a], "Rollout A")
    store.upsert([chunk_b], "Rollout B")

    # Query scoped to Rollout A should only return Rollout A chunk
    results = store.search([1.0] + [0.0] * 1535, rollout_name="Rollout A", top_k=5)
    assert all(c.rollout_name == "Rollout A" for c, _ in results)
    assert len(results) == 1

    # Query scoped to Rollout B
    results_b = store.search([0.0, 1.0] + [0.0] * 1534, rollout_name="Rollout B", top_k=5)
    assert all(c.rollout_name == "Rollout B" for c, _ in results_b)


def test_rollout_resolver_exact_match():
    """resolve_rollout_name returns exact match."""
    from utils.rollout_resolver import resolve_rollout_name

    names = ["Onboarding Q4", "Performance Goals", "Benefits Rollout"]
    resolved, is_exact = resolve_rollout_name("Onboarding Q4", names)
    assert resolved == "Onboarding Q4"
    assert is_exact is True


def test_rollout_resolver_fuzzy_match():
    """resolve_rollout_name returns fuzzy match for close names."""
    from utils.rollout_resolver import resolve_rollout_name

    names = ["Onboarding Q4", "Performance Goals"]
    resolved, is_exact = resolve_rollout_name("onboarding q4", names)
    assert resolved == "Onboarding Q4"


def test_rollout_resolver_no_match():
    """resolve_rollout_name returns None for unrecognised names."""
    from utils.rollout_resolver import resolve_rollout_name

    names = ["Onboarding Q4"]
    resolved, is_exact = resolve_rollout_name("Completely Different Thing", names)
    assert resolved is None
