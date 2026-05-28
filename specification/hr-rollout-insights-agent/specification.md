# Specification: hr-rollout-insights-agent

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent.md](../guidelines-agent.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [ ] Read the project input (`product-requirements-document.md` and `intent.md`)
- [ ] Bootstrap agent code in `assets/hr-rollout-insights-agent/` using skill `sap-agent-bootstrap` (invoke from inside `assets/hr-rollout-insights-agent/`, use copy commands — do NOT create files manually)
- [ ] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

## Document Ingestion Pipeline (R-05)

- [ ] Create `app/tools/ingest.py` — implement `ingest_documents` tool that accepts a rollout initiative name and a list of document source configs (type + connection details), fetches document content, chunks it, generates embeddings via SAP AI Core, and stores chunks in the vector store tagged with the rollout initiative name
- [ ] Implement a `SharePointConnector` class in `app/connectors/sharepoint.py` that uses the Microsoft Graph API (via an MCP-style tool wrapper) to list and download documents from a configured SharePoint site/folder; connector is read-only and never modifies source documents
- [ ] Implement a `LocalFileConnector` class in `app/connectors/local_file.py` for development/testing with local document files (used when `IBD_TESTING=true`)
- [ ] Implement a `DocumentChunker` in `app/ingestion/chunker.py` that splits document text into overlapping chunks with configurable size and overlap; preserve source document name and section header in each chunk's metadata
- [ ] Implement a `VectorStore` class in `app/ingestion/vector_store.py` backed by an in-memory or file-based store (ChromaDB or FAISS); supports `upsert(chunks, rollout_name)` and `search(query, rollout_name, top_k)` methods; rollout scoping is applied as a metadata filter on every query
- [ ] Implement embedding generation in `app/ingestion/embedder.py` using SAP AI Core embedding endpoint via LiteLLM; mock-able for tests
- [ ] Implement `app/registry.py` — a `RolloutRegistry` that maps rollout initiative names to their document source configs; loads from a `rollout_config.yaml` file at startup; allows programmatic registration for tests

## Rollout Initiative Scoping (R-06)

- [ ] Create `app/tools/scope.py` — implement `list_rollout_initiatives` tool that returns all registered rollout initiative names and their document counts from the registry
- [ ] In the agent system prompt, instruct the agent to always ask the user to confirm or specify the rollout initiative name before answering questions if no initiative is provided in the query
- [ ] Implement initiative name resolution in `app/utils/rollout_resolver.py` — fuzzy-matches a user-provided name against registered initiative names; returns exact match or closest match with a confirmation prompt
- [ ] Default behaviour: if no scope is specified and only one initiative is registered, use it automatically; if multiple, prompt the user

## Natural Language Q&A (R-01)

- [ ] Create `app/tools/query.py` — implement `query_rollout_documents` tool that accepts a natural language question and an optional rollout initiative name; retrieves top-K relevant document chunks from the vector store scoped to the specified initiative; returns a ranked list of chunks with source document name, section, and relevance score
- [ ] Implement RAG answer generation in `app/rag/answerer.py` — takes retrieved chunks and the user question, constructs a prompt that instructs the LLM to answer only from provided context, includes source citations (document name + section) in the response, and returns a structured answer object with `answer`, `sources`, and `confidence` fields
- [ ] System prompt MUST include: "You are an HR Rollout Insights Agent. Answer questions only from the provided document context. Always cite the source document and section for every claim. If the answer is not found in the context, explicitly say so — do not generate unsupported information."
- [ ] Implement confidence threshold check: if the top retrieved chunk's relevance score is below 0.5, prepend a disclaimer to the response advising the user to verify the source directly
- [ ] Implement scope enforcement: queries outside HR rollout topics must be declined with the message "I can only assist with questions about HR rollout documents."

## Document Summarisation (R-02)

- [ ] Create `app/tools/summarise.py` — implement `summarise_document` tool that accepts a document name and rollout initiative; retrieves all chunks for that document; uses the LLM to generate a concise summary of key points; returns summary with document name and source reference
- [ ] Implement `summarise_rollout` tool in the same file — accepts a rollout initiative name; retrieves representative chunks across all documents in the initiative; generates a synthesised overview covering scope, timeline, open items, and key decisions; cites contributing documents

## Rollout Status and Milestone Tracking (R-03)

- [ ] Create `app/tools/status.py` — implement `get_rollout_status` tool that accepts a rollout initiative name; queries the vector store for project plan and change management document chunks; uses the LLM to extract and return a structured list of: completed milestones, open milestones, and overdue items with source citations
- [ ] Implement `get_open_actions` tool in the same file — extracts action items, owners, and due dates from change management and communication documents for a given rollout initiative; returns a structured list with source citations

## Gap and Risk Identification (R-04)

- [ ] Create `app/tools/gap_analysis.py` — implement `identify_gaps` tool that accepts a rollout initiative name; analyses the indexed document corpus against an expected document coverage checklist (configurable per rollout type: e.g., must include project plan, training materials, change management plan, comms plan, go-live checklist); returns a structured gap report listing missing document types and undocumented process areas with source references
- [ ] Implement `identify_risks` tool in the same file — queries the vector store for risk register, issue log, and constraint-related chunks; uses the LLM to extract open risks, their status (open/mitigated/accepted), and responsible owners; returns a structured risk list with source citations
- [ ] Gap and risk findings are always presented as observations with source references; the agent must never recommend actions autonomously — all remediation is left to the human

## Agent Wiring

- [ ] Register all tools in `app/agent.py`: `ingest_documents`, `list_rollout_initiatives`, `query_rollout_documents`, `summarise_document`, `summarise_rollout`, `get_rollout_status`, `get_open_actions`, `identify_gaps`, `identify_risks`
- [ ] Set `@agent_model` to a supported SAP AI Core model (e.g. `gpt-4o`)
- [ ] Set `@agent_config` temperature to `0.0` — factual retrieval requires deterministic output
- [ ] Set `@prompt_section` to the system prompt defined above (source-grounded, HR rollout scope, citation required)
- [ ] Wire `RolloutRegistry` and `VectorStore` as shared singletons injected into all tools at startup
- [ ] Ensure the agent asks for rollout initiative name when ambiguous before invoking any retrieval tool

## Configuration

- [ ] Create `assets/hr-rollout-insights-agent/rollout_config.yaml.example` with an example rollout initiative config showing: initiative name, document sources (SharePoint URL + folder path), and document type hints (project_plan, training_material, change_management, comms_plan, go_live_checklist)
- [ ] Load config from `rollout_config.yaml` at agent startup via `RolloutRegistry`; if file is missing, log a warning and start with an empty registry
- [ ] Document all required environment variables in `assets/hr-rollout-insights-agent/env.example`: `AICORE_BASE_URL`, `AICORE_CLIENT_ID`, `AICORE_CLIENT_SECRET`, `AICORE_RESOURCE_GROUP`, `AICORE_DEPLOYMENT_ID`, `SHAREPOINT_TENANT_ID`, `SHAREPOINT_CLIENT_ID`, `SHAREPOINT_CLIENT_SECRET`

## Business Step Instrumentation (M1–M5)

- [ ] Implement business step instrumentation for each milestone from the PRD: structured logging with pattern `[MILESTONE_ID].[achieved|missed]: [description]` and OpenTelemetry custom spans. Extract business logic from `stream()` into a plain async helper (`_run_agent()`) and instrument that helper — never wrap a `yield` inside `with tracer.start_as_current_span(...)` (causes `GeneratorExit` context errors in async generators)
- [ ] M1 — Document Ingestion: emit `M1.achieved: document ingestion completed — [N] documents indexed for rollout [ROLLOUT_NAME]` on success; emit `M1.missed: document ingestion did not complete for rollout [ROLLOUT_NAME] — source: [SOURCE_URL]` on failure
- [ ] M2 — Rollout Context Established: emit `M2.achieved: rollout context established — initiative [ROLLOUT_NAME] mapped to [N] documents` when initiative is registered and has indexed docs; emit `M2.missed: rollout context not established — initiative [ROLLOUT_NAME] has no indexed documents` when empty
- [ ] M3 — Q&A Operational: emit `M3.achieved: Q&A response generated — rollout [ROLLOUT_NAME], query resolved with [N] source chunks` on successful RAG answer; emit `M3.missed: Q&A could not be resolved — rollout [ROLLOUT_NAME], no relevant documents found for query` when retrieval returns no results
- [ ] M4 — Status Tracking Active: emit `M4.achieved: status tracking completed — [N] milestones and [M] open items surfaced for rollout [ROLLOUT_NAME]` on success; emit `M4.missed: status tracking incomplete — no project plan or change management documents found for rollout [ROLLOUT_NAME]` when no relevant docs
- [ ] M5 — Gaps and Risks Identified: emit `M5.achieved: gap and risk analysis completed — [N] gaps and [M] risks identified for rollout [ROLLOUT_NAME]` on success; emit `M5.missed: gap and risk analysis did not complete — insufficient document coverage for rollout [ROLLOUT_NAME]` when corpus is too thin
- [ ] Verify `auto_instrument()` is called at top of `main.py` before any AI framework imports

## Testing

- [ ] `conftest.py` only sets `IBD_TESTING=true` — this causes the agent to run with mock MCP tool results during tests
- [ ] Write unit test `tests/test_ingest.py` — tests `ingest_documents` tool with mock `LocalFileConnector`, mock embedder, mock vector store; verifies chunks are created, tagged with rollout name, and M1 milestone log is emitted
- [ ] Write unit test `tests/test_query.py` — tests `query_rollout_documents` tool with a pre-seeded in-memory vector store; verifies retrieved chunks are scoped to the specified initiative and source citations are present
- [ ] Write unit test `tests/test_summarise.py` — tests `summarise_document` and `summarise_rollout` tools with mock vector store and mocked LLM; verifies summary contains document name reference
- [ ] Write unit test `tests/test_status.py` — tests `get_rollout_status` and `get_open_actions` tools with mock vector store chunks containing project plan content; verifies structured output contains milestone and action fields
- [ ] Write unit test `tests/test_gap_analysis.py` — tests `identify_gaps` and `identify_risks` tools; seed vector store with a partial document set missing training materials; verify gap report flags the missing type
- [ ] Write unit test `tests/test_scope.py` — tests `list_rollout_initiatives` tool and `RolloutRegistry`; verifies initiative list is correct and scoping filter is applied on vector store queries
- [ ] Write one integration test `tests/test_integration.py` — executes end-to-end agent flow: ingest sample local documents, ask a rollout question, verify the answer cites a source and contains no fabricated content; mock LLM and AI Core; use `LocalFileConnector` for document access
- [ ] Run `pytest` from `assets/hr-rollout-insights-agent/` (no args) — if coverage < 70%, add tests until threshold met
- [ ] Verify `assets/hr-rollout-insights-agent/app/agent.py` has exactly 3 decorated functions — run `grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/hr-rollout-insights-agent/app/agent.py` and confirm it returns 3
- [ ] Run `pytest` again from `assets/hr-rollout-insights-agent/` (no args) to generate final `test_report.json`
- [ ] Verify `test_report.json` exists in `assets/hr-rollout-insights-agent/` — if not, run pytest again until it does

## Validation Checklist

Run these before marking implementation complete:

```bash
# Instrumentation
grep -r "M[0-9]\.achieved" assets/hr-rollout-insights-agent/app/     # must return results

# Decorators
grep -r "sap_cloud_sdk.agent_decorators" assets/hr-rollout-insights-agent/app/  # must return results
grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/hr-rollout-insights-agent/app/agent.py  # must return 3

# Test report
ls assets/hr-rollout-insights-agent/test_report.json                  # must exist
```
