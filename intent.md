# HR Rollout Insights Agent

AI agent that provides intelligent insights on documents related to specific HR rollouts.

## Business challenge

HR Business Partners managing HR rollouts (e.g., SuccessFactors module launches, policy deployments, org changes) work across a large volume of documents — project plans, training materials, change management policies, configuration guides, and communication templates — stored across SharePoint and multiple other sources. Finding relevant information, tracking rollout status, and identifying gaps or risks requires manual effort across fragmented systems. An AI agent is needed to unify these documents and provide on-demand summarisation, natural language Q&A, rollout status tracking, and gap/risk surfacing.

## Key Milestones

1. **Document Ingestion**: HR rollout documents ingested and indexed from SharePoint and additional sources into the agent's knowledge base.
2. **Rollout Context Established**: Documents are associated with specific rollout initiatives (e.g., SuccessFactors Onboarding go-live, Performance & Goals rollout).
3. **Q&A Operational**: Agent correctly answers natural language questions about rollout scope, timelines, decisions, and tasks sourced from documents.
4. **Status Tracking Active**: Agent surfaces rollout milestone status and open items from project and change management documents.
5. **Gaps & Risks Identified**: Agent detects and reports missing coverage, unresolved risks, or undocumented areas across a given rollout.

## Business Architecture (RBA)

### End-to-End Process

Recruit to Retire (E2E)

### Process Hierarchy

```
Recruit to Retire (E2E)
└── Recruit to Onboard (generic)
    └── Onboard talent (generic) [BPS-387]
        └── Manage workforce onboarding documentation
└── Manage Workforce (generic)
    └── Manage employee information and reporting (generic) [BPS-385]
        └── Manage HR reports
└── Develop to Grow (generic)
    └── Identify and grow talent (generic) [BPS-389]
        └── Manage employee performance and development
```

### Summary

An agent providing document insights for HR rollouts maps primarily to the Recruit to Retire E2E, spanning the onboarding, workforce management, and talent development phases where rollout documentation, compliance, and training artefacts are generated and consumed.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | Gap? | Notes / assumptions |
| ---------------------- | ----------------------- | ---------- | ----------------- | ---- | ------------------- |
| Access & query HR rollout documents across SharePoint and multiple sources | None | — | — | Yes | No standard SAP product provides cross-source document Q&A; custom AI Agent required |
| Summarise document content on demand | None | — | — | Yes | SAP SuccessFactors Knowledge Base stores content but offers no AI summarisation |
| Natural language Q&A over rollout documents | None | — | — | Yes | Core gap — requires RAG-based agent with document indexing |
| Track rollout status & milestones from documents | SAP SuccessFactors Employee Central (partial) | `sap.sf:apiResource:FoundationPlatformPLT:v1` | — | Partial | SuccessFactors tracks milestones natively but not derived from unstructured documents |
| Onboarding content management | SAP SuccessFactors Onboarding (SC1313), SAP SuccessFactors Work Zone (SC4287) | `sap.sf:apiResource:OnboardingOBX:v1` | — | No | Standard coverage; agent can surface this data |
| Compliance training tracking | SAP SuccessFactors Learning (SC1273, SC1281) | — | — | No | Standard coverage via SuccessFactors Learning |
| Surface gaps or risks in rollout coverage | None | — | — | Yes | No standard product; requires document analysis logic in agent |

### Key findings

- No standard SAP product provides cross-source intelligent document Q&A or rollout gap analysis — this is a full custom AI Agent build.
- SAP SuccessFactors covers the underlying HR processes (onboarding, learning, employee admin) but does not analyse unstructured rollout documents stored in SharePoint.
- The agent must connect to SharePoint (primary source) and potentially other document stores, index documents per rollout, and apply RAG for retrieval.
- MCP servers for SuccessFactors APIs are not currently available in the landscape; direct API calls will be needed for any SuccessFactors data enrichment.
- SAP SuccessFactors Work Zone is available and could serve as a complementary channel for agent output (knowledge articles, rollout status cards).
- The agent's value is highest when documents are tagged or organised by rollout initiative, enabling scoped retrieval.

## Recommendations

### HR Rollout Document Insights Agent

#### Executive Summary

Pro-code Python AI Agent with RAG over SharePoint rollout docs.

#### Recommended Solution

A Python-based AI Agent (A2A protocol) that ingests and indexes HR rollout documents from SharePoint and other configured sources using Retrieval-Augmented Generation (RAG). HR Business Partners interact with the agent via natural language to receive on-demand document summaries, get answers to rollout-specific questions, track open milestones and status from project artefacts, and identify gaps or risks across the document corpus. The agent is scoped per rollout initiative and leverages SAP AI Core as the LLM runtime.

#### Recommended solution category

AI Agent

#### Intent fit
85%
