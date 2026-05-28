"""Unit tests for the HRRolloutInsightsAgent core logic."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("IBD_TESTING", "1")


@pytest.fixture
def mock_graph_result():
    """Mock LangGraph ainvoke result."""
    mock_msg = MagicMock()
    mock_msg.content = "The go-live criteria are: UAT sign-off, training completion, comms sent."
    return {"messages": [mock_msg]}


@pytest.mark.asyncio
async def test_invoke_returns_completed_response(mock_graph_result):
    """Agent invoke() returns a completed AgentResponse."""
    with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock, return_value=[]):
        from agent import HRRolloutInsightsAgent

        agent = HRRolloutInsightsAgent()

        with patch.object(agent, "_run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "The go-live criteria are UAT sign-off and training."

            result = await agent.invoke("What are go-live criteria?", "ctx-001")

    assert result.status == "completed"
    assert len(result.message) > 0


@pytest.mark.asyncio
async def test_stream_yields_processing_then_result(mock_graph_result):
    """Agent stream() yields a 'processing' chunk then a final completed chunk."""
    with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock, return_value=[]):
        from agent import HRRolloutInsightsAgent

        agent = HRRolloutInsightsAgent()

        with patch.object(agent, "_run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Answer from documents."

            chunks = []
            async for chunk in agent.stream("Test query", "ctx-002"):
                chunks.append(chunk)

    assert len(chunks) >= 2
    # First chunk should be a status update (not complete)
    assert chunks[0]["is_task_complete"] is False
    # Last chunk should be complete
    assert chunks[-1]["is_task_complete"] is True
    assert "Answer from documents" in chunks[-1]["content"]


@pytest.mark.asyncio
async def test_stream_handles_exceptions_gracefully():
    """Agent stream() catches exceptions and returns error response."""
    with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock, return_value=[]):
        from agent import HRRolloutInsightsAgent

        agent = HRRolloutInsightsAgent()

        with patch.object(agent, "_run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = RuntimeError("LLM service unavailable")

            chunks = []
            async for chunk in agent.stream("Test query", "ctx-003"):
                chunks.append(chunk)

    last = chunks[-1]
    assert last["is_task_complete"] is True
    assert "error" in last["content"].lower() or "encountered" in last["content"].lower()


@pytest.mark.asyncio
async def test_tools_cached_after_first_load():
    """Agent caches tools after first load — _get_tools returns same list on repeated calls."""
    with patch("agent.get_mcp_tools", new_callable=AsyncMock, return_value=[]):
        from agent import HRRolloutInsightsAgent

        agent = HRRolloutInsightsAgent()
        tools1 = await agent._get_tools()
        tools2 = await agent._get_tools()

    # Same list object returned on second call (cached)
    assert tools1 is tools2


@pytest.mark.asyncio
async def test_run_agent_passes_local_tools():
    """_run_agent uses LOCAL_TOOLS when no tools are passed."""
    with patch("mcp_tools.get_mcp_tools", new_callable=AsyncMock, return_value=[]):
        from agent import HRRolloutInsightsAgent, LOCAL_TOOLS
        from langchain_core.messages import AIMessage

        agent = HRRolloutInsightsAgent()

        mock_graph = MagicMock()
        mock_result = {"messages": [AIMessage(content="Answer from docs.")]}
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)

        with patch("agent.create_agent", return_value=mock_graph) as mock_create:
            result = await agent._run_agent("What is the status?", "ctx-run-1")

    assert "Answer from docs." in result
    call_args = mock_create.call_args
    used_tools = call_args[1]["tools"] if call_args[1] else call_args[0][1]
    assert len(used_tools) >= len(LOCAL_TOOLS)


def test_agent_decorator_count():
    """agent.py has exactly 3 decorated functions."""
    import subprocess
    result = subprocess.run(
        ["grep", "-c", r"^@agent_model\|^@agent_config\|^@prompt_section",
         "app/agent.py"],
        capture_output=True, text=True,
        cwd=os.path.join(os.path.dirname(__file__), ".."),
    )
    count = int(result.stdout.strip())
    assert count == 3, f"Expected 3 decorators, found {count}"


def test_get_system_prompt_contains_required_instructions():
    """System prompt contains source citation and scope enforcement instructions."""
    import sys
    app_dir = os.path.join(os.path.dirname(__file__), "..", "app")
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    from agent import get_system_prompt
    prompt = get_system_prompt()
    assert "cite" in prompt.lower() or "citation" in prompt.lower()
    assert "HR rollout" in prompt or "hr rollout" in prompt.lower()
    assert "100" in prompt  # page-size limit guardrail
