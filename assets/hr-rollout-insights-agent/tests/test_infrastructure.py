"""Tests for infrastructure modules: chunker, embedder, vector_store, registry, answerer, resolver."""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

os.environ.setdefault("IBD_TESTING", "1")


# --- Chunker ---

def test_chunker_produces_chunks_with_metadata():
    from ingestion.chunker import chunk_text
    text = "# Section One\n\nThis is the first paragraph with some content.\n\n# Section Two\n\nThis is the second paragraph."
    chunks = chunk_text(text, source_doc="my_doc.txt", doc_type="project_plan")
    assert len(chunks) >= 1
    assert all(c["source_doc"] == "my_doc.txt" for c in chunks)
    assert all(c["doc_type"] == "project_plan" for c in chunks)
    assert all("text" in c for c in chunks)


def test_chunker_handles_long_text():
    from ingestion.chunker import chunk_text, CHUNK_SIZE
    long_text = "\n\n".join([f"Paragraph {i}: " + "x" * 200 for i in range(10)])
    chunks = chunk_text(long_text, source_doc="long.txt")
    assert len(chunks) > 1
    assert all(len(c["text"]) <= CHUNK_SIZE + 200 for c in chunks)


def test_chunker_empty_text_returns_empty():
    from ingestion.chunker import chunk_text
    assert chunk_text("", "empty.txt") == []


# --- Embedder ---

def test_embedder_returns_zero_vectors_on_failure():
    from ingestion.embedder import embed_texts, EMBEDDING_DIM
    with patch("litellm.embedding", side_effect=RuntimeError("no AI Core")):
        result = embed_texts(["hello world"])
    assert len(result) == 1
    assert len(result[0]) == EMBEDDING_DIM
    assert all(v == 0.0 for v in result[0])


def test_embed_query_single_text():
    from ingestion.embedder import embed_query, EMBEDDING_DIM
    with patch("litellm.embedding", side_effect=RuntimeError("no AI Core")):
        result = embed_query("test query")
    assert len(result) == EMBEDDING_DIM


def test_embed_texts_empty_returns_empty():
    from ingestion.embedder import embed_texts
    assert embed_texts([]) == []


# --- Vector Store ---

def test_vector_store_upsert_and_count():
    from ingestion.vector_store import VectorStore, Chunk
    store = VectorStore()
    chunks = [
        Chunk("text a", "doc1.txt", "Sec1", "RolloutX", embedding=[0.1] * 1536),
        Chunk("text b", "doc1.txt", "Sec2", "RolloutX", embedding=[0.2] * 1536),
    ]
    store.upsert(chunks, "RolloutX")
    assert store.count("RolloutX") == 2


def test_vector_store_upsert_replaces_existing_source():
    from ingestion.vector_store import VectorStore, Chunk
    store = VectorStore()
    c1 = Chunk("old content", "doc1.txt", "S1", "R1", embedding=[0.1] * 1536)
    store.upsert([c1], "R1")
    c2 = Chunk("new content", "doc1.txt", "S1", "R1", embedding=[0.9] * 1536)
    store.upsert([c2], "R1")
    assert store.count("R1") == 1
    assert store.get_by_doc("doc1.txt", "R1")[0].text == "new content"


def test_vector_store_doc_types_present():
    from ingestion.vector_store import VectorStore, Chunk
    store = VectorStore()
    store.upsert([Chunk("t", "a.txt", "S", "R1", doc_type="project_plan", embedding=[0.1] * 1536)], "R1")
    store.upsert([Chunk("t", "b.txt", "S", "R1", doc_type="training_material", embedding=[0.2] * 1536)], "R1")
    types = store.doc_types_present("R1")
    assert "project_plan" in types
    assert "training_material" in types


def test_vector_store_clear_rollout():
    from ingestion.vector_store import VectorStore, Chunk
    store = VectorStore()
    store.upsert([Chunk("t", "a.txt", "S", "R1", embedding=[0.1] * 1536)], "R1")
    store.upsert([Chunk("t", "b.txt", "S", "R2", embedding=[0.2] * 1536)], "R2")
    store.clear_rollout("R1")
    assert store.count("R1") == 0
    assert store.count("R2") == 1


# --- Registry ---

def test_registry_load_from_yaml():
    from registry import RolloutRegistry
    yaml_content = """
rollouts:
  - name: "Test Rollout"
    sources:
      - type: local
        connection:
          folder_path: ./docs
        doc_type_hints:
          - project_plan
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        fname = f.name

    try:
        registry = RolloutRegistry()
        registry.load_from_yaml(fname)
        assert "Test Rollout" in registry.all_names()
        initiative = registry.get("Test Rollout")
        assert initiative is not None
        assert len(initiative.sources) == 1
        assert initiative.sources[0].doc_type_hints == ["project_plan"]
    finally:
        os.unlink(fname)


def test_registry_missing_file_is_graceful():
    from registry import RolloutRegistry
    registry = RolloutRegistry()
    registry.load_from_yaml("/nonexistent/path/config.yaml")
    assert registry.all_names() == []


def test_registry_update_doc_count():
    from registry import RolloutRegistry, RolloutInitiative
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="R1"))
    registry.update_doc_count("R1", 10)
    assert registry.get("R1").doc_count == 10


# --- RAG Answerer ---

def test_build_rag_prompt_with_chunks():
    from ingestion.vector_store import Chunk
    from rag.answerer import build_rag_prompt
    chunks = [
        (Chunk("Training must be done.", "training.txt", "Sec1", "R1", embedding=[]), 0.9),
        (Chunk("Go-live Dec 1.", "project_plan.txt", "Sec2", "R1", embedding=[]), 0.8),
    ]
    prompt = build_rag_prompt("What is required?", chunks)
    assert "training.txt" in prompt
    assert "Training must be done" in prompt


def test_build_rag_prompt_no_chunks():
    from rag.answerer import build_rag_prompt
    prompt = build_rag_prompt("What is required?", [])
    assert "not available" in prompt.lower() or "No relevant" in prompt.lower() or "not found" in prompt.lower()


def test_format_rag_answer_low_confidence_adds_disclaimer():
    from ingestion.vector_store import Chunk
    from rag.answerer import format_rag_answer, LOW_CONFIDENCE_DISCLAIMER
    chunks = [(Chunk("x", "d.txt", "S", "R", embedding=[]), 0.3)]
    answer = format_rag_answer("Some answer.", chunks)
    assert answer.confidence == 0.3
    assert LOW_CONFIDENCE_DISCLAIMER in answer.answer


def test_format_rag_answer_high_confidence_no_disclaimer():
    from ingestion.vector_store import Chunk
    from rag.answerer import format_rag_answer
    chunks = [(Chunk("x", "d.txt", "S", "R", embedding=[]), 0.9)]
    answer = format_rag_answer("Good answer.", chunks)
    assert answer.confidence == 0.9
    assert "verify" not in answer.answer.lower() or "Note" not in answer.answer


# --- Rollout Resolver ---

def test_resolver_case_insensitive():
    from utils.rollout_resolver import resolve_rollout_name
    resolved, is_exact = resolve_rollout_name("ONBOARDING Q4", ["Onboarding Q4", "Performance Goals"])
    assert resolved == "Onboarding Q4"
    assert is_exact is True


def test_resolver_empty_registry():
    from utils.rollout_resolver import resolve_rollout_name
    resolved, is_exact = resolve_rollout_name("anything", [])
    assert resolved is None
    assert is_exact is False
