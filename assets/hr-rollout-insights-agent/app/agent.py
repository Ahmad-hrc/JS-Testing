import logging
import time
from dataclasses import dataclass
from typing import AsyncGenerator, Literal, Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langgraph.checkpoint.memory import InMemorySaver
from opentelemetry import trace
from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section

from mcp_tools import get_mcp_tools
from tools.ingest import ingest_documents
from tools.scope import list_rollout_initiatives
from tools.query import query_rollout_documents
from tools.summarise import summarise_document, summarise_rollout
from tools.status import get_rollout_status, get_open_actions
from tools.gap_analysis import identify_gaps, identify_risks

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

THREAD_TTL_SECONDS = 3600  # evict threads inactive for 1 hour

LOCAL_TOOLS: list[BaseTool] = [
    ingest_documents,
    list_rollout_initiatives,
    query_rollout_documents,
    summarise_document,
    summarise_rollout,
    get_rollout_status,
    get_open_actions,
    identify_gaps,
    identify_risks,
]


@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return "sap/anthropic--claude-4.6-opus"


@agent_config(
    key="config.temperature",
    label="LLM Temperature",
    description="Controls randomness of responses (0.0 = deterministic, 1.0 = creative)",
)
def get_temperature() -> float:
    return 0.0


@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The full system prompt defining the agent's role and behavior",
    validation={"format": "markdown", "max_length": 5000},
)
def get_system_prompt() -> str:
    return (
        "You are an HR Rollout Insights Agent. "
        "Answer questions only from the provided document context returned by your tools. "
        "Always cite the source document and section for every claim. "
        "If the answer is not found in the context, explicitly say so — do not generate unsupported information. "
        "Only assist with questions about HR rollout documents. "
        "When a user asks a question without specifying a rollout initiative, "
        "use list_rollout_initiatives to show available options and ask the user to confirm before proceeding. "
        "Set top or equivalent page-size parameter to a maximum of 100 on every tool call that accepts it "
        "to prevent context overflow, and inform the user when this limit is applied."
    )


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


async def _load_tools() -> list[BaseTool]:
    """Load MCP tools (lazy, async) and combine with local tools."""
    try:
        mcp_tools = await get_mcp_tools()
        return LOCAL_TOOLS + list(mcp_tools)
    except Exception as exc:
        logger.warning("Could not load MCP tools (%s) — using local tools only", exc)
        return LOCAL_TOOLS


class HRRolloutInsightsAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self.llm = ChatLiteLLM(model=get_model_name(), temperature=get_temperature())
        self._checkpointer = InMemorySaver()
        self._last_active: dict[str, float] = {}
        self._tools: list[BaseTool] | None = None
        self._summarization_middleware = SummarizationMiddleware(
            model=self.llm,
            trigger=("tokens", 100_000),
        )

    def _touch(self, thread_id: str) -> None:
        now = time.monotonic()
        expired = [tid for tid, ts in list(self._last_active.items()) if now - ts > THREAD_TTL_SECONDS]
        for tid in expired:
            self._checkpointer.delete_thread(tid)
            del self._last_active[tid]
            logger.info("Evicted inactive thread: %s", tid)
        self._last_active[thread_id] = now

    async def _get_tools(self) -> list[BaseTool]:
        if self._tools is None:
            self._tools = await _load_tools()
        return self._tools

    async def _run_agent(self, query: str, context_id: str, tools: list[BaseTool] | None = None) -> str:
        """Core agent logic — extracted so OTel spans do not wrap yield statements."""
        with tracer.start_as_current_span("hr_rollout_agent.run") as span:
            span.set_attribute("query.length", len(query))
            span.set_attribute("context_id", context_id)

            if tools is None:
                tools = await self._get_tools()
            span.set_attribute("tools.count", len(tools))
            graph = create_agent(
                self.llm,
                tools=tools,
                system_prompt=get_system_prompt(),
                checkpointer=self._checkpointer,
                middleware=[self._summarization_middleware],
            )
            config = {"configurable": {"thread_id": context_id}}
            result = await graph.ainvoke({"messages": [HumanMessage(content=query)]}, config)
            response = result["messages"][-1].content
            span.set_attribute("response.length", len(response))
            return response

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream agent responses."""
        self._touch(context_id)
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Processing your HR rollout query...",
        }
        try:
            logger.info("HR Rollout Agent processing query for context: %s", context_id)
            # Merge executor-provided tools (MCP) with local tools
            merged_tools: list[BaseTool] | None = None
            if tools is not None:
                merged_tools = LOCAL_TOOLS + list(tools)
            response = await self._run_agent(query, context_id, tools=merged_tools)
            self._touch(context_id)
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response,
            }
        except Exception as e:
            logger.exception("Agent stream() failed for context: %s", context_id)
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"I encountered an error while processing your request: {str(e)}. Please try again.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AgentResponse:
        """Invoke agent and return final response."""
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(status="error", message=last.get("content", "Unknown error"))


# Alias for backward-compatible import used by agent_executor.py
SampleAgent = HRRolloutInsightsAgent
