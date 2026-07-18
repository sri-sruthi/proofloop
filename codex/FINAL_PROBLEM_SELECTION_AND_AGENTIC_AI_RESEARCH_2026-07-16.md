# Final Problem Selection and Agentic AI Industry Research

**Research date:** 2026-07-16  
**Status:** Research recommendation; no implementation has been started  
**Primary source:** Aivar's complete 30-page problem-statement document  
**Recommended statement:** **PS-5.1 — The Agent WAF**  
**Recommended product framing:** **AegisFlow — a customer-controlled, transaction-aware Agent Action Firewall for multi-agent invoice workflows**

## Executive decision

Choose PS-5.1, but do not submit a generic rate-limit/blocklist proxy and do not claim that agent firewalls do not exist.

That market premise is now outdated. AWS AgentCore Gateway and Policy, Microsoft Agent Governance Toolkit, Google Agent Gateway, Cisco AI Defense, Prisma AIRS, Check Point/Lakera, Portkey, Cloudflare and open-source projects already cover much of the assignment's basic feature set.

The defensible product is:

> Existing gateways control individual tool calls. AegisFlow controls and verifies the cumulative customer consequence of an entire agent workflow.

The project should govern a realistic Aivar-aligned freight-invoice workflow. It must prevent duplicate or premature payments, cross-tenant access, altered amounts, excessive cumulative effects, unsafe retries and tool loops. It should verify the actual postcondition after a mutating tool executes and quarantine or compensate safely when the observed result differs from what was authorized.

This is the best balance of:

- the user's genuine interest in the WAF statement;
- visible AWS and production engineering;
- current MCP, multi-agent, memory, evaluation and observability trends;
- direct relevance to Aivar's Velogent and freight-invoice work;
- a clear five-to-eight-minute demo;
- enough data-science rigor in evaluation, calibration and operational metrics;
- honest differentiation from products already in the market.

PS-5.2 has more pure technical whitespace, but it is predominantly identity, cryptography and revocation engineering. PS-4.3 is more directly aligned with anomaly-detection experience, but it is still cybersecurity-focused, which the user said is not her preferred direction. Difficulty alone is not a reason to choose either.

## What changed from the earlier recommendation

The earlier Codex research recommended PS-3.2 because it optimized for resume alignment and a short deadline. The new decision optimizes for the user's clarified priorities: a challenging AWS-aligned system, an Aivar-specific customer story, current agentic-AI patterns and a production control plane.

This is not a claim that PS-5.1 is easier or safer. It is the recommended hiring signal only if its scope remains a coherent vertical slice and its market comparison is candid.

## Evidence standard and limitations

The research prioritizes:

1. official Aivar material;
2. official AWS, Anthropic, Microsoft, Google, OpenTelemetry, MLflow and MCP documentation;
3. first-party company engineering reports and annual reports;
4. vendor/customer case studies, clearly treated as self-reported;
5. research papers only where products do not yet provide strong evidence.

The connected Google Drive could not be read in this session. Both the Drive profile/search connector and the separate rclone remote returned authentication/internal errors after the account switch. No Drive files were changed. Public Databricks agent-system guides and documentation were reviewed instead. The private downloaded guides can be incorporated later if they are copied into Downloads or the connector becomes readable.

## What Aivar appears to value

Aivar's public material says:

- it was founded by four former AWS colleagues;
- the customer is the fifth element at the center of the company;
- it builds production systems, not POCs;
- systems are deployed into the customer's environment with code and data control;
- AWS-native cloud and data architecture, DevOps maturity and Day-2 governance matter;
- no-black-box auditability is non-negotiable;
- Velogent targets document-heavy, exception-prone, multi-agent workflows such as invoice processing, contracts, RFQs and reconciliation;
- Velogent already exposes model usage, errors, pipeline status, Block/Review/Approve policies, event-level audit and HITL.

Therefore AegisFlow must not look like a second workflow dashboard. It is an independent enforcement boundary around consequential tools. It protects the customer's business invariants even if an agent, prompt, model or orchestration layer changes.

## Current industry direction

### Multi-agent is important, but it is not a universal minimum

Anthropic recommends starting with the simplest architecture that satisfies the use case because agentic systems trade latency and cost for performance. Workflows are appropriate when the path is predictable; autonomous agents are appropriate when the steps cannot be hard-coded. Multi-agent patterns are justified when specialist roles or parallel work measurably improve outcomes.

For AegisFlow, three agents are justified because they have different authority:

1. an extraction agent may read invoices and propose structured fields;
2. a reconciliation agent may read POs, vendors and rate cards;
3. an execution agent may request approval or initiate a tightly scoped mutation.

The policy engine is not an agent. Deterministic controls must decide whether a high-impact action is allowed.

### Production patterns seen repeatedly

| Pattern | Production implication for this project |
|---|---|
| Bounded autonomy | Typed tools, explicit scopes, deterministic limits and HITL for irreversible actions |
| Specialist agents | Add an agent only where responsibility, authority or latency can be measured |
| MCP and APIs | Use MCP as the standardized agent-to-tool data plane; keep REST/OpenAPI for administration |
| Short-term state | Persist workflow state, approvals, effect budgets and idempotency keys |
| Selective long-term memory | Store only approved summaries or resolved-exception lessons with provenance and TTL |
| RAG with authoritative sources | Retrieve invoice policy/rate-card evidence only if it improves measured accuracy |
| Continuous evaluation | Evaluate tool choice, parameters, sequence, task success, false blocks and recovery |
| Full-path observability | Trace model, memory, handoff, policy, tool, retry, cost and business outcome |
| Cost governance | Bound calls, tokens, retries, elapsed time and cost per correctly completed workflow |
| Human control | Provide preview, reason, approve/reject/modify, SLA and rollback where technically safe |

### Representative production use cases

| Organization | Use case and lesson |
|---|---|
| BNY | Production AI solutions and multi-agent digital employees use credentials, supervisors, guardrails, telemetry and human oversight |
| Uber | Thousands of internal agents use registry, mesh/gateway, MCP, per-hop identity, short-lived credentials and full delegation provenance |
| Amazon | Q Developer agents modernized large application fleets, but generated changes remain reviewable and test-driven |
| DoorDash | High-volume voice support shows strict latency, short retained context, automated tests and explicit live-agent routing |
| Apollo Tyres | Specialist agents and RAG support industrial root-cause analysis; parallel work helped, while unused workflows and model choices had to be optimized for latency |
| Cox Automotive | AgentCore, Strands, memory, identity, observability and hierarchical agents are used with role-based permissions and API-first integration |
| Morgan Stanley | Enterprise RAG and meeting workflows require expert evaluation, regression tests, zero-retention controls and advisor review |
| Kaiser Permanente | Ambient documentation at large scale still requires patient notification, no retained audio and physician review of every draft |
| Rexera | Document and transaction workflows combine extraction, verification and human exception handling rather than relying on one free-form agent |
| Genentech | Agentic research uses RAG, internal APIs, citations and adaptive plans while scientists retain judgment |

The common denominator is not maximum autonomy. It is bounded, observable, measurable work against authoritative systems.

## Market scan of all 25 problem statements

This is a category scan, not a claim that every vendor has been exhaustively tested.

| PS | Existing solution landscape | Remaining credible gap | Decision |
|---|---|---|---|
| 1.1 AI Asset Crawler | AWS Config/CloudTrail, CSPM, AI inventory and governance platforms | Cross-source ownership and runtime lineage | Useful but less aligned with demonstrated skills |
| 1.2 MCP Server Risk Scanner | Cisco, Prisma AIRS, Microsoft AGT, Snyk and MCP scanners | Continuous trust/schema drift across a fleet | Current but security-scanner heavy |
| 1.3 Governance Graph | AI registries, CMDBs, ModelOp/IBM/ServiceNow and knowledge graphs | Live blast radius with runtime provenance | Good visualization, lower differentiation |
| 2.1 Agent Identity Card | AgentCore Identity, Microsoft Entra Agent ID, Okta, SPIFFE/SPIRE | Portable lifecycle and review across clouds | IAM-dominant and difficult to defend quickly |
| 2.2 Tool Permission Enforcer | AgentCore Policy, Cedar, OPA, Permit/Auth0 FGA | Cross-provider conformance and dynamic business state | Largely covered per call |
| 2.3 Delegation Chain Governor | OBO/token exchange, A2A authentication, identity vendors | Portable multi-hop scope attenuation and revocation | High difficulty, weak resume fit |
| 3.1 Action Guardrail | AgentCore Policy, AGT, Cisco, Prisma, Lakera, Portkey | Consequence-aware cross-call enforcement | Absorbed by the recommended PS-5.1 extension |
| 3.2 Behavioral Injection Detector | Agent evaluations and behavioral security products | Pre-dispatch, task-conditioned anomaly calibration | Strong DS fit, but not preferred domain |
| 3.3 Cross-provider Guardrails | Portkey, LiteLLM, Guardrails AI and cloud safety APIs | Proving semantic equivalence across providers | Crowded |
| 4.1 Behavioral Baseline | AgentCore Evaluations, MLflow, Arize/Phoenix, LangSmith/Langfuse | Synthetic pre-production baseline plus drift refresh | Strong alternative, less customer-specific |
| 4.2 Governance-linked Observability | AgentOps products, CloudWatch, ServiceNow and governance suites | Automatic evidence-backed governance state changes | Strong Day-2 alternative |
| 4.3 Cross-session Pattern Detector | Mostly research plus general abuse/fraud tooling | LLM-specific cross-session correlation | Good whitespace and DS fit, but cybersecurity-focused |
| 5.1 Agent WAF | AWS, Microsoft, Google, Cisco, Prisma, Lakera, Portkey, Cloudflare, Pipelock | Cumulative business effects and postcondition verification | **Recommended only with extended framing** |
| 5.2 Inter-agent Trust | A2A auth, AgentCore Identity, SPIFFE and signed Agent Cards | Per-message authority, attenuation and immediate revocation | Highest whitespace, highest crypto/systems risk |
| 5.3 Semantic Exfiltration | Enterprise DLP and AI runtime security | Fact-level reconstruction across multiple outputs | Strong DS alternative, still security-heavy |
| 6.1 Compliance Card | Model cards, governance suites, A2A Agent Cards | Runtime-derived agent compliance evidence | Finishable but less technically distinctive |
| 6.2 Runtime-to-Compliance | ModelOp, IBM, ServiceNow and audit platforms | Open telemetry-to-control evidence bridge | Valuable Aivar Day-2 option |
| 7.1 Decision Path Auditor | MLflow/LangSmith/Arize traces and audit systems | Causal action evidence without hidden chain-of-thought | Good, but must avoid storing private reasoning |
| 7.2 Governed Audit Log | CloudTrail, SIEM, immutable stores and privacy tooling | Unified PII, retention, access and tamper controls | Important but mainly data governance |
| 8.1 Budget Controller | LiteLLM, Portkey, Kong, Helicone, AgentCore and FinOps tools | Domain-effect budgets beyond tokens and money | Basic version crowded |
| 8.2 Model Substitution Event | Gateways perform fallback and routing | Compliance-grade material-change evidence | Genuine narrow gap, but lower demo depth |
| 9.1 Graduated Autonomy | Velogent itself, approval workflows and policy engines | Outcome-calibrated thresholds by customer | Excellent customer story, but overlaps Aivar's product |
| 9.2 HITL SLA Queue | ServiceNow, Temporal/Step Functions and workflow platforms | Agent-specific review-quality feedback | Useful but not novel alone |
| 10.1 Policy-as-Code | OPA/Rego, Cedar, GitOps and AgentCore Policy | Portable semantic conformance and customer impact replay | Strong engineering, crowded category |
| 10.2 Dynamic Rules Engine | OPA, Cedar and context-aware authorization | Stateful workflow context and safe policy simulation | Valuable component, not best standalone choice |

## Three viable directions

| Direction | Strengths | Risks | Verdict |
|---|---|---|---|
| **A. PS-5.1 AegisFlow** | AWS/Aivar fit, visible production engineering, customer outcomes, clear demo, MCP and multi-agent relevance | Generic WAF is crowded; must deliver stateful innovation honestly | **Recommended** |
| B. PS-4.3 Vigil | Highest data-science alignment, genuine research whitespace, strong calibration story | User is not interested in cybersecurity; long-term privacy/identity questions | Backup only |
| C. PS-5.2 TrustChain | Hardest and least commoditized; directly multi-agent | Cryptography, key management, revocation and authorization dominate; hard to finish and defend | Do not choose for difficulty alone |

## Proposed product: AegisFlow

### Customer problem

An invoice automation agent may make every individual API call with a valid credential and still create a bad business outcome:

- it pays before reconciliation;
- it retries a payment after a timeout and creates a duplicate;
- it changes the amount after approval;
- it mixes tenant or vendor data;
- several individually permitted actions exceed the customer's cumulative exposure;
- a tool reports success but the authoritative system shows a different state;
- an agent loops and repeatedly contacts a customer or modifies records.

### Customer promises

1. **No bypass:** mutating tools are reachable only through the governed path.
2. **No model as judge of its own action:** deterministic policy enforces safety.
3. **No invisible decision:** every disposition carries rule, policy version, actor, tenant, workflow state and sanitized evidence.
4. **No blind retry:** all mutations require idempotency and postcondition verification.
5. **Customer-controlled autonomy:** thresholds, review requirements, retention, budgets and rollout mode are configurable.
6. **Customer-owned deployment:** infrastructure, policies, logs and code are deployable in the customer's AWS account.
7. **Measured value:** report prevented duplicate exposure, normal completion rate, false blocks, review time, latency and cost per completed invoice.

### Workflow and authority boundaries

The deterministic workflow is:

RECEIVED → EXTRACTED → RECONCILED → APPROVAL_REQUIRED → APPROVED → PAYMENT_QUEUED → PAID

Agents:

- **Extraction agent:** OCR/field interpretation; read-only tools.
- **Reconciliation agent:** PO, vendor and rate-card comparison; read-only tools.
- **Execution agent:** approval request, ERP export and payment initiation; narrowly scoped mutation tools.

Authoritative controls:

- identity and tenant scope;
- state-transition rules;
- parameter/schema rules;
- call and loop budgets;
- cumulative domain-effect budgets;
- approval binding to exact amount/vendor/document version;
- idempotency;
- postcondition verification;
- quarantine and safe compensation.

### What is actually innovative

#### 1. Cumulative domain-effect ledger

Track business effects across agents, calls, retries and sessions:

- records modified;
- external recipients contacted;
- sensitive rows disclosed;
- privileges expanded;
- aggregate refund exposure;
- tenant/geography boundaries crossed.

This must not be presented as merely a token or payment budget. Agent gateways and AgentCore Payments already cover those narrower dimensions.

#### 2. State-derived capability minimization

Expose only the tools legal in the current workflow state. This reduces tool-selection errors, schema tokens and attack surface. It is an efficiency and control feature, not a claim that dynamic tool filtering is unprecedented.

#### 3. Effect contract and postcondition reconciliation

Every mutating tool declares:

- predicted effect;
- reversibility;
- idempotency strategy;
- expected postcondition;
- verification probe;
- safe compensating action, if one exists.

AegisFlow authorizes the predicted effect, executes idempotently, reads the authoritative postcondition and compares actual versus approved. A mismatch freezes the workflow, emits evidence and routes to review or a safe compensating action.

#### 4. Outcome-driven policy rollout

Historical replay → shadow mode → selected-tenant canary → low-risk enforcement → high-impact enforcement.

Promotion requires customer-defined thresholds for false blocks, missed violations, latency, review burden and expected business loss. Policies automatically demote or roll back on regression.

### Architecture

~~~mermaid
flowchart TB
    U["Customer or reviewer"] --> ID["Cognito or enterprise OIDC"]
    ID --> AR["AgentCore Runtime with bounded Strands agents"]
    AR --> GW["AgentCore Gateway - MCP"]
    GW --> AP["AgentCore Policy - Cedar per-call authorization"]
    GW --> AF["AegisFlow request interceptor"]
    AF --> DDB["DynamoDB workflow state, effect ledger, policy versions, idempotency"]
    AF --> SF["Step Functions approval and recovery workflow"]
    AF --> T["Private Lambda or API tools"]
    T --> VR["Postcondition verifier"]
    VR --> AF
    AF --> EV["EventBridge and SQS/DLQ"]
    EV --> WS["WebSocket dashboard and alerts"]
    AR --> OT["OpenTelemetry / ADOT"]
    GW --> OT
    AF --> OT
    T --> OT
    OT --> CW["AgentCore Observability and CloudWatch"]
~~~

AWS WAF can protect the HTTP edge of AgentCore Gateway, but it is not the product differentiator. AegisFlow governs agent actions and workflow consequences.

### End-to-end action flow

~~~mermaid
sequenceDiagram
    participant A as Agent
    participant G as MCP Gateway
    participant P as Cedar Policy
    participant F as AegisFlow
    participant S as State Store
    participant T as Tool

    A->>G: tools/call with identity, tenant, workflow, idempotency key
    G->>P: static least-privilege authorization
    P-->>G: allow or deny
    G->>F: normalized action request
    F->>S: conditional read/transition and effect-budget check
    S-->>F: versioned workflow state
    F-->>G: allow, block, review or shadow result
    G->>T: execute allowed action
    T-->>G: result and effect receipt
    G->>F: post-execution result
    F->>T: authoritative verification probe
    T-->>F: observed postcondition
    F->>S: atomic evidence and state update
    F-->>A: verified result or quarantine/review
~~~

## Mapping to PS-5.1 requirements

| Assignment requirement | AegisFlow implementation |
|---|---|
| Transparent proxy | AgentCore Gateway plus an externalized request interceptor on every MCP tool call |
| Rate limit | Per-agent/tool token bucket with DynamoDB conditional updates |
| Parameter validation | JSON Schema/Pydantic validation, normalization, size limits and block rules |
| Data scope | Signed tenant/user context, Cedar authorization and tool-side defense-in-depth |
| Sequence rules | Versioned finite-state transition graph |
| Sanitized audit | Structured decision event with redacted parameters and policy evidence |
| Real-time dashboard | API Gateway WebSocket updates; polling must be labelled near-real-time if used instead |
| Shadow mode | AgentCore LOG_ONLY plus AegisFlow outcome replay and canary promotion |
| Real LLM | Bedrock Converse through Strands; deterministic fixtures remain available for CI |
| Production readiness | IaC, AWS deployment, health/readiness, concurrency, state, alarms, retries, DLQ and runbooks |

## Recommended technology stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Resume fit, Strands/Bedrock/AWS SDK support |
| Agent framework | Strands Agents SDK | AWS-aligned, model-agnostic, supports MCP and bounded multi-agent patterns |
| Model | Amazon Bedrock Converse; inexpensive model by default | Real provider with IAM-based auth; stronger model only for ambiguous cases |
| Tool protocol | MCP Streamable HTTP | Standard typed agent-tool envelope |
| Gateway | Amazon Bedrock AgentCore Gateway | Managed MCP entry point, identity, observability and tool integration |
| Static policy | AgentCore Policy with Cedar | Deterministic default-deny authorization outside the model |
| Stateful enforcement | Lambda request interceptor | Business invariants, sequence, quotas and effect ledger |
| State | DynamoDB | Conditional writes, transactions, TTL and low operational burden |
| Durable HITL | Step Functions Standard callback pattern | Review timeouts and resumable workflows |
| Async events | EventBridge plus SQS/DLQ | Decoupled evidence, alerts and retry isolation |
| Tool adapters | Private Lambda functions / OpenAPI APIs | No direct agent bypass; least-privilege resource policies |
| Observability | OpenTelemetry/ADOT, AgentCore Observability, CloudWatch | Full-path traces, metrics and alarms |
| Dashboard | Small TypeScript/React or static web UI with WebSocket | Real-time decisions without building a large frontend |
| IaC | Terraform with pinned provider/lockfile | Matches Aivar's published AWS delivery pattern; reproducible deploy/destroy |
| CI/CD | GitHub Actions OIDC to AWS | No stored cloud access keys |
| Testing | pytest, Hypothesis, moto/local fixtures, contract and load tests | Determinism, concurrency and failure coverage |
| Security/quality | Ruff, mypy, Bandit, Trivy, Checkov, secret scan, SBOM | Reviewable production gates |
| GenAI evaluation | AgentCore Evaluations or open MLflow trace evaluation | Tool trajectory, task completion and production sampling |

Do not introduce EKS merely to look advanced. A serverless workload is more credible at assignment scale. EKS is a measured future migration path for sustained throughput, custom isolation or model serving.

## Production engineering decisions

### No bypass

- Agents receive permission to invoke only the Gateway.
- Mutating tool Lambdas accept only the Gateway/AegisFlow role.
- Tool adapters independently validate tenant, action and idempotency context.
- Direct tool endpoints are private or protected by resource policies.

Without this, the proxy is advisory governance, not enforcement.

### Concurrency and consistency

- Every workflow carries a monotonic version.
- DynamoDB conditional writes or TransactWriteItems atomically validate state, record the decision and reserve an idempotency key.
- At-least-once SQS/Lambda delivery is assumed.
- No claim of magical exactly-once delivery is made; exactly-once business effect is achieved through idempotent handlers and conditional state.
- SQS FIFO groups by workflow ID, not tenant ID, so separate workflows remain concurrent.

### Failure semantics

| Failure | Required behavior |
|---|---|
| Policy/state store unavailable | Fail closed for payments, sensitive reads/writes and external communication |
| Bedrock throttling | Bounded exponential backoff with jitter, retry budget and cheaper-model fallback only if policy permits |
| Tool timeout after possible side effect | Do not retry blindly; verify by idempotency key and postcondition probe |
| Invalid or stale approval | Block and require new approval bound to exact action payload |
| Duplicate/replayed request | Return the prior verified result or reject; never repeat the mutation |
| Postcondition mismatch | Quarantine workflow, open circuit, alert and compensate only if explicitly safe |
| Audit/event sink degraded | Preserve primary decision locally/transactionally and queue delivery; alarm on lag |
| Dashboard unavailable | Enforcement continues; UI is not in the safety path |
| Agent loop | Stop at call/token/time/effect limits and route to review |

### Retries and backpressure

- Retry only eligible timeouts, 429s and selected 5xx errors.
- Apply circuit breakers per downstream tool.
- Cap redrive attempts and require explicit DLQ recovery.
- Use Lambda reserved concurrency and SQS maximum concurrency to protect ERP/payment systems.
- Treat API Gateway throttling as best effort, not the sole business quota.

### Privacy and audit

- Redact before persistence.
- Do not log raw invoices, full prompts, credentials or hidden chain-of-thought.
- Log normalized tool parameters only where required for evidence.
- Capture actor, tenant, workflow, tool, policy/rule version, prior state, decision, reason code, latency, idempotency key hash and verification outcome.
- Use retention categories and TTL; allow the customer to choose longer immutable archival separately.

## Evaluation strategy

Separate software correctness, policy correctness, agent quality and customer outcome.

### Required suites

1. **Unit tests:** schemas, normalization, rules, state transitions, redaction and cost math.
2. **Policy tests:** default deny, forbid precedence, tenant scope and policy version.
3. **Property tests:** duplicate/reordered/replayed events cannot create more than one permitted effect.
4. **Concurrency test:** one hundred concurrent payment attempts produce exactly one mutation.
5. **Contract tests:** MCP tools/list and tools/call, JWT audience/scope, Gateway target schemas and effect receipts.
6. **Adversarial fixtures:** cross-tenant access, prompt injection, altered amount, payment before approval, stale approval, replay, loop and malicious tool response.
7. **Failure injection:** policy outage, DynamoDB conflict, tool timeout, Bedrock throttling, DLQ and partial success.
8. **Load test:** throughput plus p50/p95/p99 enforcement overhead.
9. **Agent evaluations:** tool choice, parameter accuracy, expected trajectory, normal task completion and recovery.
10. **Policy replay:** false blocks, unsafe allows, added latency and review workload before promotion.

### Primary metrics

- unsafe allow rate on maintained test corpus;
- duplicate side effects;
- tenant leakage;
- required-rule recall;
- false-block rate on legitimate workflows;
- correct tool sequence and parameter accuracy;
- normal workflow completion rate;
- review precision and reviewer minutes;
- policy decision p95 latency;
- loop terminations;
- cost per correctly completed invoice;
- prevented financial/exposure amount;
- postcondition mismatch recovery rate.

An LLM judge may score explanations or ambiguous extraction quality. It must never be the final authority for a payment or access decision.

## Cost strategy

The goal is a deployable reference environment with a clear production scaling path.

- AgentCore is consumption-priced with no stated minimum.
- Gateway is approximately $0.005 per 1,000 invocations in the current official pricing.
- AgentCore Policy authorization is approximately $0.000025 per evaluation.
- Lambda includes one million requests and 400,000 GB-seconds per month in its free tier.
- DynamoDB's provisioned free tier includes 25 GB and 25 read/write capacity units.
- Bedrock model inference, CloudWatch, Step Functions and optional AWS WAF are separate.
- AWS WAF adds a small recurring ACL/rule cost, so it may be deployed only during evaluation windows on a strict personal budget and disclosed honestly.
- A Claude Code subscription does not pay for Bedrock or Anthropic API inference.

Cost controls:

- billing alarm and resource tags from the first deployment;
- one region and one environment for the submission;
- automatic teardown;
- deterministic agent/tool fixtures in CI;
- paid model calls only for regression and smoke suites;
- compact typed handoffs rather than full histories;
- smaller model for extraction/routing and stronger model only for ambiguous exceptions;
- maximum model calls, tool calls, tokens, retries and wall time per workflow;
- trace sampling and short log retention in the demo account;
- no always-on EKS, OpenSearch Serverless or managed vector database.

Do not give a fixed monthly production quote without the region, traffic, model and retention assumptions. A submission-scale evaluation should be kept to a small capped budget and torn down after verification.

## RAG, memory, looping and other trend choices

| Trend | Use it? | Decision |
|---|---|---|
| Multi-agent | Yes, bounded | Three roles with distinct authority; no swarm |
| MCP | Yes | Standard tool data plane and interception boundary |
| RAG | Conditional | Small policy/rate-card corpus only if evaluation proves benefit |
| Short-term memory | Yes | Workflow state, prior tool outcomes, approvals and budgets |
| Long-term memory | Limited | Provenance-linked summaries of resolved exceptions with TTL; no raw customer memory by default |
| Agent loop | Yes, bounded | Maximum steps, calls, tokens, time and cumulative effects |
| Reflection/evaluator loop | Offline | Improve policies/evals; not in the high-impact authorization path |
| Model fallback | Yes, governed | Record substitution; restrict approved model list; never silently weaken policy |
| Semantic anomaly model | Optional shadow signal | May support future DS extension but never overrides deterministic controls |
| Skills/slash commands | Development only | Reusable Claude Code workflows, not a runtime product feature |

## How to use Claude Code and Codex together

- Keep Claude and Codex outputs in separate directories, as the user is already doing.
- Use one shared decision log for final human-approved choices.
- Give only one tool ownership of a file at a time.
- Use Claude Code for focused implementation loops, project-local skills, runtime debugging and repetitive repository workflows.
- Use Codex for independent architecture/market verification, failure-mode review, tests, documentation and second-pass code review.
- Have each review the other's completed diff or document, not edit the same file simultaneously.
- Use small, explicit handoffs: goal, accepted decisions, files changed, tests run, known gaps and next task.
- Never accept generated infrastructure or security code without being able to explain its IAM, network, failure and cost behavior.

Current Claude Code documentation says custom slash commands have been merged into Skills. Project skills live under .claude/skills/name/SKILL.md, load on demand and can be invoked as /name. Useful later project skills would be deploy-staging, policy-replay, run-evals, failure-drill and verify-release. They should be created only after the architecture is approved.

## Best Coursera Plus course

### One-course recommendation

**Building AI Agent Harnesses with Strands Agents — Amazon Web Services**

https://www.coursera.org/learn/build-ai-agents

Why this is the closest single match:

- included with Coursera Plus as verified on 2026-07-16;
- offered by AWS;
- updated in July 2026;
- about six hours;
- agent loop and model providers;
- MCP tools;
- hooks, plugins, skills and steering;
- context, state, persistent memory and sessions;
- agents-as-tools, graph workflows and swarms;
- trajectory and multi-turn evaluation;
- cloud deployment and Amazon Bedrock AgentCore.

This course directly covers the agent side of AegisFlow. It will not teach all of Cedar, DynamoDB concurrency, Terraform or Step Functions, so the project documentation and AWS service guides remain necessary.

### Optional second course

**DevOps and AI on AWS: CI/CD for Generative AI Applications**

https://www.coursera.org/learn/cicd-generative-ai-apps

Also verified as included. It covers CI/CD, infrastructure as code, deployment, CloudWatch, CloudTrail and X-Ray. Choose it only after the six-hour Strands course or after the submission if the deadline is unchanged.

## Delivery workflow after approval

The following is a project workflow, not an authorization to implement yet.

1. Freeze the product contract, demo story, SLOs, trust boundaries and claims.
2. Build deterministic action contracts, state machine and policy tests before the agent.
3. Build private synthetic tools with idempotency and verification probes.
4. Implement the Gateway/interceptor enforcement path and required PS-5.1 rules.
5. Add the normal single-workflow agent, then split into specialist agents only where authority differs.
6. Add persistence, concurrency controls, audit events, health/readiness and failure semantics.
7. Deploy with Terraform and least-privilege IAM.
8. Add full-path tracing, metrics, alarms and the real-time dashboard.
9. Run normal, adversarial, failure, concurrency and load suites.
10. Perform historical replay, shadow mode and one canary policy.
11. Produce evidence artifacts, architecture diagrams, threat/failure model, runbook, cost report and limitations.
12. Record the demo: outcome first, then architecture, blocked scenarios, verified success, dashboard and deployment evidence.

If the Saturday deadline is still active, the submission must be a vertical slice:

- one invoice workflow;
- the exact required WAF controls;
- one transaction innovation end to end;
- one AWS deployment;
- strong tests and evidence.

Do not attempt a general-purpose enterprise platform in two days.

## Claims to make and avoid

### Defensible claims

- transaction-aware enforcement across a demonstrated workflow;
- deterministic control outside the model;
- duplicate-side-effect prevention under the tested concurrency;
- policy replay, shadow and canary workflow;
- postcondition verification for the implemented synthetic tools;
- AWS-deployed reference implementation;
- compatible with the tested MCP/AgentCore path;
- designed for customer-owned AWS deployment.

### Claims to avoid

- first or unique Agent WAF;
- no competing solution exists;
- detects all attacks or prevents all agent failures;
- exactly once delivery;
- zero false positives in the world;
- production proven across enterprises;
- safe rollback of irreversible real payments;
- hidden chain-of-thought capture;
- support for every model, agent framework or MCP server without validation.

## Approval requested

Before implementation or a final implementation plan is created, approve or reject this direction:

> **PS-5.1 AegisFlow: transaction-aware Agent Action Firewall for a bounded, multi-agent freight-invoice workflow on AWS AgentCore.**

If approved, the next Codex document should be the detailed design specification with frozen APIs, schemas, SLOs, threat boundaries and acceptance tests. Only after that should an implementation plan be written.
