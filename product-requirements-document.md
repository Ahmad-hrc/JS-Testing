# Product Requirements Document (PRD)

**Title:** HR Rollout Insights Agent  
**Date:** 2026-05-28  
**Owner:** HR Business Partners / HR Transformation Team  
**Solution Category:** AI Agent

---

## Product Purpose & Value Proposition

**Elevator Pitch:**  
HR Business Partners managing HR rollouts wade through dozens of scattered documents — project plans, policies, training materials, and change management artefacts — stored across SharePoint and other sources. This AI agent brings all of that together: ask a question, get an answer grounded in the actual rollout documents. No more manual document hunting.

**Business Need:**  
HR rollouts (e.g., SAP SuccessFactors module go-lives, policy deployments, organisational changes) generate a significant volume of documentation across multiple systems. HR Business Partners must manually locate, read, and synthesise information from fragmented sources to answer questions, report on status, or identify gaps. This creates bottlenecks, inconsistencies, and delays in rollout execution. No standard SAP product addresses cross-source intelligent document Q&A for HR rollout contexts.

**Expected Value:**  
- Reduction in time spent searching for rollout information
- Faster identification of open issues and gaps before go-live
- Consistent, source-grounded answers to rollout queries across the HR team
- Improved rollout quality through proactive risk and gap surfacing

**Product Objectives (Prioritized):**
1. Enable HR Business Partners to query any HR rollout document corpus in natural language and receive accurate, source-grounded answers.
2. Surface rollout milestone status and open items from project and change management documents without manual review.
3. Detect and flag gaps or undocumented areas within a rollout initiative's document set.
4. Provide on-demand document summaries to reduce time-to-insight across project plans, policies, and training materials.

---

## User Profiles & Personas

### Primary Persona: Miriam — HR Business Partner

Miriam is a 38-year-old HR Business Partner responsible for overseeing the regional rollout of SAP SuccessFactors Onboarding. She manages relationships between HR, IT, and business stakeholders across three countries. She spends a significant portion of her day answering questions from managers and employees about what's happening, when, and what's expected of them — questions that require her to dig through SharePoint folders, email threads, and slide decks. She's comfortable with Microsoft 365 tools and uses Teams daily, but is not technical. She wants reliable, quick answers and is frustrated by inconsistency in how rollout progress is tracked and communicated. Success for her means running a rollout where everyone has the right information at the right time, and she isn't the bottleneck.

### Secondary Persona: Thomas — HR Project Manager

Thomas is a 44-year-old HR Project Manager coordinating the go-live plan for a SuccessFactors Performance & Goals deployment. He owns the master project plan, risk register, and stakeholder communication documents. He needs a way to quickly check what's been completed, what's outstanding, and whether any documentation gaps exist — without reading through every artefact manually. He tracks milestones and escalates blockers. He values accuracy and traceability, and needs to trust that the agent's answers reference real documents.

### Other User Types

- **HR Managers**: Ask rollout-related questions about training schedules, process changes, or policy updates.
- **IT Deployment Consultants**: Verify configuration decisions documented in design or build artefacts.

---

## User Goals & Tasks

### For Miriam (HR Business Partner):

**Goals:**
- Get accurate answers to rollout questions without manually reviewing documents.
- Understand the current status of a rollout from project artefacts without scheduling a status call.
- Identify any risks or undocumented areas before a go-live milestone.

**Key Tasks:**
- Ask the agent: "What are the go-live readiness criteria for the Onboarding rollout?"
- Ask: "Which country is behind on completing onboarding training materials?"
- Ask: "Summarise the change management plan for the Performance & Goals rollout."
- Ask: "Are there any open risks or unresolved items in the Q4 rollout documents?"

### For Thomas (HR Project Manager):

**Goals:**
- Track rollout milestone status from documented project artefacts.
- Surface gaps in rollout documentation coverage without manual audit.

**Key Tasks:**
- Ask: "What milestones are marked as complete in the project plan?"
- Ask: "Which process areas are missing documented training materials?"
- Ask: "Give me a summary of open actions from the stakeholder communication plan."

---

## Product Principles

1. **Source-grounded answers**: Every agent response must cite the source document and section. No answer without provenance.
2. **Rollout-scoped retrieval**: The agent must operate within the scope of a specific rollout initiative. Cross-rollout queries are supported but must be explicit.
3. **HR Business Partner-first**: Interactions are designed for non-technical users. Plain language in, plain language out.
4. **Human in the loop for risk**: Gap and risk findings are surfaced as observations, not decisions. The agent recommends; humans act.
5. **Minimal footprint**: The agent reads documents; it does not modify, delete, or move them.

---

## Business Context

**Current State:**  
HR Business Partners manually search SharePoint and other document repositories to answer rollout questions. Documents are unstructured, inconsistently named, and spread across project sites, Teams channels, and shared drives. Status tracking relies on manual updates to project plans. Gap identification requires experience and manual cross-referencing.

**Strategic Alignment:**  
Accelerating HR transformation programme delivery through AI-assisted knowledge management. Aligns to the enterprise's cloud-first and AI adoption strategy on SAP BTP.

**Success Criteria:**
- HR Business Partners can answer rollout questions via the agent without opening a document manually.
- Rollout status can be reported from agent output in under 2 minutes per initiative.
- Gap reports generated by the agent are validated as accurate by HR Project Managers in >80% of cases.

---

## Goals and Non-Goals

### Goals (In Scope)

- Ingest and index HR rollout documents from SharePoint and other configured document sources.
- Provide natural language Q&A over scoped rollout document corpora.
- Summarise individual documents or document sets on demand.
- Surface rollout milestone status and open items from project and change management documents.
- Identify and report gaps or undocumented areas within a rollout initiative's document corpus.
- Associate documents with named rollout initiatives for scoped retrieval.

### Non-Goals (Out of Scope)

- Modifying, updating, or writing rollout documents.
- Acting as a workflow engine or task assignment system.
- Replacing SAP SuccessFactors for HR process execution or milestone tracking in the live system.
- Providing real-time data from SAP SuccessFactors (e.g., employee records, live training completions) without explicit integration scope.
- Supporting non-HR document types or business domains.

---

## Requirements

### Must-Have Requirements

**R-01**: Natural Language Q&A over Rollout Documents

- **Problem to Solve**: HR Business Partners cannot quickly find answers to rollout questions buried across multiple documents and sources.
- **User Story**: As an HR Business Partner, I need to ask plain-language questions about any HR rollout and receive accurate, source-cited answers so that I can respond to stakeholders without manually searching documents.
- **Acceptance Criteria**:
  - Given documents have been ingested for a rollout, when a user asks a rollout-scoped question, then the agent returns a relevant answer citing the source document and section.
  - Given a query that cannot be answered from the indexed documents, when the agent is asked, then it clearly states that the information was not found in the available documents.
- **Maps to Objective**: Objective 1
- **Priority Rank**: 1

**R-02**: Document Summarisation

- **Problem to Solve**: HR Business Partners spend excessive time reading full documents to extract key points.
- **User Story**: As an HR Business Partner, I need on-demand summaries of individual documents or groups of documents so that I can quickly understand the content of a rollout artefact.
- **Acceptance Criteria**:
  - Given a document has been indexed, when a user requests a summary, then the agent returns a concise summary of its key points.
  - Given a rollout initiative name, when a user requests a summary of all documents in that rollout, then the agent returns a synthesised overview.
- **Maps to Objective**: Objective 4
- **Priority Rank**: 2

**R-03**: Rollout Status and Milestone Tracking

- **Problem to Solve**: Project managers and HR Business Partners must manually review project documents to understand rollout status.
- **User Story**: As an HR Project Manager, I need the agent to surface milestone status and open items from project and change management documents so that I can report on rollout progress without reading every artefact.
- **Acceptance Criteria**:
  - Given project plan documents are indexed, when a user asks about milestone status, then the agent returns a list of completed and open milestones sourced from those documents.
  - Given a change management document is indexed, when a user asks for open actions, then the agent returns a list of unresolved items.
- **Maps to Objective**: Objective 2
- **Priority Rank**: 3

**R-04**: Gap and Risk Identification

- **Problem to Solve**: Undocumented areas and unresolved risks in rollout document sets are only discovered late, causing delays.
- **User Story**: As an HR Business Partner, I need the agent to identify gaps or risks in the rollout document corpus so that I can address them before they impact the go-live.
- **Acceptance Criteria**:
  - Given a rollout's document set is indexed, when a user asks for gaps or risks, then the agent returns a structured list of undocumented areas or open risk items with source references.
  - Given no risks or gaps are found, then the agent explicitly confirms that no gaps were detected in the available documents.
- **Maps to Objective**: Objective 3
- **Priority Rank**: 4

**R-05**: Document Ingestion from SharePoint and Multiple Sources

- **Problem to Solve**: Rollout documents are stored across SharePoint and other systems; the agent must access them to provide value.
- **User Story**: As an HR administrator, I need to configure the agent to ingest documents from SharePoint sites and other document sources so that the agent's knowledge base stays current.
- **Acceptance Criteria**:
  - Given a SharePoint site URL and credentials are configured, when ingestion is triggered, then documents are indexed and available for Q&A.
  - Given a new document is added to a configured source, when the next ingestion cycle runs, then the document is included in the index.
- **Maps to Objective**: Objective 1
- **Priority Rank**: 1

**R-06**: Rollout Initiative Scoping

- **Problem to Solve**: Queries across all documents without context return noisy, unfocused answers.
- **User Story**: As an HR Business Partner, I need to scope my queries to a specific rollout initiative so that answers are relevant and not mixed with documents from other programmes.
- **Acceptance Criteria**:
  - Given multiple rollout initiatives are configured, when a user specifies a rollout name, then the agent restricts retrieval to documents tagged to that initiative.
  - Given no rollout scope is provided, then the agent asks the user to clarify or defaults to all indexed documents.
- **Maps to Objective**: Objective 1
- **Priority Rank**: 2

---

## Solution Architecture

**Architecture Overview:**  
A Python-based AI Agent deployed on SAP BTP using the A2A protocol. It connects to SharePoint and other document sources for ingestion, indexes documents in a vector store scoped per rollout initiative, and uses RAG with SAP Generative AI Hub (SAP AI Core) to answer user queries. The agent exposes a conversational interface and is observable via OpenTelemetry instrumentation.

**Key Components:**

- **Agent Runtime (Python / A2A)**: Core agent logic handling conversation, tool orchestration, and RAG retrieval.
- **Document Ingestion Connector**: Connects to SharePoint (Microsoft Graph API) and other configured document sources; extracts and chunks document content.
- **Vector Store**: Stores document embeddings scoped by rollout initiative for semantic retrieval.
- **SAP Generative AI Hub (SAP AI Core)**: LLM and embedding model runtime for generating answers and embeddings.
- **Rollout Initiative Registry**: Configuration layer mapping documents to named rollout initiatives.

**Integration Points:**

- **SharePoint / Microsoft Graph API**: Primary document source; read-only access to configured site collections.
- **SAP AI Core**: LLM inference and embedding generation; called per user query.
- **SAP SuccessFactors (optional)**: Read-only access for supplementary rollout context (e.g., onboarding milestones); via SuccessFactors OData API.

**Deployment Environments:**

- **Dev**: Local agent with mock document corpus for development and unit testing.
- **QA**: BTP-deployed agent with staging SharePoint sites and non-production AI Core instance.
- **Prod**: BTP-deployed agent connected to production SharePoint and AI Core; scoped access controls enforced.

---

### Agent Extensibility & Instrumentation

**Agent Extensibility:**
- The agent is designed with extension points to support additional document sources (e.g., Google Drive, Confluence) without re-architecting the ingestion layer.
- Tool definitions are modular: new tools (e.g., SuccessFactors live data lookup, Teams message retrieval) can be added as independent modules.
- Rollout initiative scoping is configuration-driven, allowing new rollouts to be onboarded without code changes.
- The agent supports future extension to write-back capabilities (e.g., creating knowledge articles in SAP SuccessFactors Work Zone) as a separate, gated tool.

**Business Step Instrumentation:**
- All five milestone steps (M1–M5 below) must emit structured log statements on achievement and on miss.
- Log statements follow the pattern: `[MILESTONE_ID].[achieved|missed]: [description]`
- Logs are emitted via OpenTelemetry spans to enable monitoring in production.

---

### Automation & Agent Behaviour

**Automation Level:** Autonomous agent (RAG-based reasoning with human review for risk outputs)

**Actions the system performs without human approval:**
- Retrieves and ranks relevant document chunks for a given query.
- Generates and returns summarised or Q&A responses to the user.
- Identifies and lists open items or milestones from indexed documents.

**Actions that require human review or approval:**
- Gap and risk findings are presented as observations only; remediation actions require human decision.
- Document source configuration changes (adding/removing SharePoint sites) require admin approval.

**Model or engine used:** SAP Generative AI Hub via SAP AI Core (GPT-4o or equivalent); embedding model for vector indexing.

**Knowledge & data sources accessed:**

- **SharePoint (Microsoft 365)**: Primary rollout document store; read-only; owned by HR project teams.
- **Additional document sources**: Configurable (e.g., shared drives, other document management systems); read-only.
- **SAP SuccessFactors (optional enrichment)**: Onboarding and milestone data via OData API; read-only.

**Tools or connectors invoked:**

- **SharePoint Connector**: Reads document content from configured SharePoint sites. Read-only.
- **Vector Store Retrieval Tool**: Performs semantic search over indexed rollout documents. Read-only.
- **LLM Inference Tool**: Calls SAP AI Core for answer generation and summarisation. Read-only.
- **Rollout Scope Filter**: Restricts retrieval to documents tagged to a specified rollout initiative. Read-only.

**Guardrails & fail-safes:**

- The agent never modifies, deletes, or moves source documents.
- All answers must be grounded in retrieved document chunks; hallucinated responses are mitigated by strict RAG prompting.
- If no relevant documents are found, the agent explicitly states it cannot answer rather than generating an unsupported response.
- Confidence below a defined threshold triggers a disclaimer and suggests the user verify the source directly.
- Queries outside HR rollout context are declined with a clear scope message.

---

### Configuration & Data

**Configuration Scope:**  
SharePoint site URLs and access credentials, rollout initiative registry (name → document folder mappings), ingestion schedule, and AI Core model endpoint configuration.

**Organisational & Master Data:**
- Rollout initiative names and document folder mappings must be configured by an HR administrator before first use.
- No organisational master data migration required.

---

## Milestones

### M1: Document Ingestion

- **Description**: HR rollout documents successfully ingested and indexed from SharePoint and additional configured sources.
- **Achieved when**: All documents from configured sources for a given rollout initiative are indexed and retrievable via semantic search.
- **Log on achievement**: `M1.achieved: document ingestion completed — [N] documents indexed for rollout [ROLLOUT_NAME]`
- **Log on miss**: `M1.missed: document ingestion did not complete for rollout [ROLLOUT_NAME] — source: [SOURCE_URL]`

### M2: Rollout Context Established

- **Description**: Indexed documents are associated with a named rollout initiative, enabling scoped retrieval.
- **Achieved when**: A rollout initiative is configured in the registry and documents are tagged and retrievable under that scope.
- **Log on achievement**: `M2.achieved: rollout context established — initiative [ROLLOUT_NAME] mapped to [N] documents`
- **Log on miss**: `M2.missed: rollout context not established — initiative [ROLLOUT_NAME] has no indexed documents`

### M3: Q&A Operational

- **Description**: The agent correctly answers natural language questions sourced from indexed rollout documents.
- **Achieved when**: Agent returns a relevant, source-cited answer for a rollout-scoped question using the RAG pipeline.
- **Log on achievement**: `M3.achieved: Q&A response generated — rollout [ROLLOUT_NAME], query resolved with [N] source chunks`
- **Log on miss**: `M3.missed: Q&A could not be resolved — rollout [ROLLOUT_NAME], no relevant documents found for query`

### M4: Status Tracking Active

- **Description**: The agent surfaces rollout milestone status and open items from project and change management documents.
- **Achieved when**: Agent returns a structured list of milestones or open actions from project artefacts for a given rollout.
- **Log on achievement**: `M4.achieved: status tracking completed — [N] milestones and [M] open items surfaced for rollout [ROLLOUT_NAME]`
- **Log on miss**: `M4.missed: status tracking incomplete — no project plan or change management documents found for rollout [ROLLOUT_NAME]`

### M5: Gaps and Risks Identified

- **Description**: The agent detects and reports missing coverage, unresolved risks, or undocumented areas across a rollout's document corpus.
- **Achieved when**: Agent returns a structured gap or risk report for a given rollout initiative.
- **Log on achievement**: `M5.achieved: gap and risk analysis completed — [N] gaps and [M] risks identified for rollout [ROLLOUT_NAME]`
- **Log on miss**: `M5.missed: gap and risk analysis did not complete — insufficient document coverage for rollout [ROLLOUT_NAME]`

---

## Risks, Assumptions, and Dependencies

### Risks

- **Document quality**: If source documents are incomplete, outdated, or unstructured, agent answers will reflect those limitations.
- **SharePoint access**: Permissions and authentication configuration for SharePoint are a prerequisite; delays here block the entire ingestion pipeline.
- **LLM accuracy**: RAG-based answers may miss nuance in complex documents; quality depends on chunking strategy and prompt design.
- **Adoption**: HR Business Partners must trust the agent's source citations; low trust will reduce adoption even if accuracy is high.

### Assumptions

- HR rollout documents in SharePoint are accessible via Microsoft Graph API with appropriate service account credentials.
- Rollout initiatives can be clearly named and mapped to document folders or SharePoint sites.
- SAP AI Core is provisioned and accessible on the BTP tenant.
- Documents are primarily in English or a supported language for the configured LLM.

### Dependencies

- SAP AI Core instance (provisioned on BTP)
- SharePoint / Microsoft Graph API access (service account with read permissions)
- BTP subaccount for agent deployment
- Rollout initiative document organisation (HR team must maintain structured folder conventions)
