# Source Register — PS-6.2 ProofLoop Runtime-to-Compliance Research

**Compiled:** 2026-07-16  
**Purpose:** Source companion to the separate PS-6.2 research and design proposal  
**Evidence policy:** Prefer official standards, regulations, AWS documentation, first-party vendor documentation and files supplied by the user. Vendor capability and outcome statements are treated as self-reported.  
**Legal caution:** Framework and regulation sources support design mapping only; this research is not legal advice or a compliance certification.

## Original assignment

- **Aivar problem statements:** `/Users/srisruthi/Downloads/Problem_Statements_Aivar.docx`
  - PS-6.2, Runtime-to-Compliance Bridge, appears on page 20 of the Word document.
  - The assignment requires a deployed production-ready system, API/state/logging/error handling, a five-to-eight-minute demo, a PDF write-up, architecture diagrams, market comparison and automated deployment scripts.

## Aivar: company and customer alignment

| Source | Evidence used |
|---|---|
| [Aivar About Us](https://www.aivar.tech/about-us) | Four former AWS colleagues; customer as fifth element; Day-2 AI led by governance and integration; no-black-box auditability; production focus |
| [Aivar home / governed agentic stack](https://www.aivar.tech/) | AWS depth, continuous monitoring, production operations, governed agentic stack and customer outcomes |
| [Aivar Reva.ai policy-governance case](https://www.aivar.tech/case-studies/reva-ai-transforming-enterprise-policy-management-with-generative-ai-on-aws) | Bedrock, SageMaker, Verified Permissions/Cedar/OPA, monitoring, audit and policy-governance relevance |
| [Aivar case studies](https://www.aivar.tech/case-studies) | Agentic finance/customer workflows, regulatory and production architecture themes |
| [Aivar AWS Marketplace build service](https://aws.amazon.com/marketplace/pp/prodview-fqbumdxlwd2lg) | Agentic workflows, Guardrails, AWS Well-Architected controls and customer-account delivery |
| [Bessemer on Aivar](https://www.bvp.com/news/realizing-ai-for-global-enterprises-with-aivar) | Independent investor description of ex-AWS founders, productized accelerators and production enterprise execution |

## AWS AgentCore, Bedrock and CloudWatch

| Source | Evidence used |
|---|---|
| [Amazon Bedrock AgentCore overview](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/) | Runtime, memory, gateway, policy, registry, MCP/A2A, model/framework portability and production operations |
| [AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-tools-runtime.html) | Secure serverless hosting and framework/model flexibility |
| [How AgentCore Runtime works](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-how-it-works.html) | Immutable runtime versions, environment endpoints, identity and deployment model |
| [AgentCore observability concepts](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-telemetry.html) | Sessions, traces, spans, ADOT instrumentation, errors, tools and resource visibility |
| [View AgentCore observability in CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/view-observability-data-cloudwatch.html) | Agent/session/trace views, log groups, span store and metrics |
| [AgentCore evaluation types](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations-types.html) | Online, on-demand and batch evaluation; continuous production monitoring |
| [AgentCore evaluation results](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/results-and-output.html) | Evaluation results in CloudWatch logs/metrics with OTel conventions and trace/session references |
| [CloudWatch AgentCore Evaluations](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/session-traces-evaluations.html) | Production sessions, sampling, evaluators, alarms and direct log/metric access |
| [AgentCore Policy metrics and spans](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-policy-metrics.html) | Allow/deny/mismatch metrics, policy/gateway dimensions and authorization decision spans |
| [AgentCore Policy LOG_ONLY mode](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-test-a-policy.html) | Shadow evaluation, real-traffic metrics and safe promotion to active enforcement |
| [Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html) | Configurable safety/privacy filters and direct `ApplyGuardrail` use |
| [Bedrock sensitive-information filters](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-sensitive-filters.html) | PII block/mask behavior and important limitations for tool output, model logs and trace fields |
| [Agentic AI Lens: output filtering](https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentsec08-bp02.html) | Need to protect every output path, including memory, agent handoffs and logs |
| [AgentOps with AgentCore](https://aws.amazon.com/blogs/machine-learning/agentops-operationalize-agentic-ai-at-scale-with-amazon-bedrock-agentcore/) | Production feedback loop across traces, quality, governance, cost and deployment |
| [AgentCore release notes](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/release-notes.html) | March–May 2026 GA changes, evaluation performance, stable CDK constructs and current service status |

## AWS production engineering and failure handling

| Source | Evidence used |
|---|---|
| [EventBridge Scheduler failure handling](https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule.html) | Retry policies and DLQs for scheduled reconciliation/canaries |
| [EventBridge Scheduler DLQ](https://docs.aws.amazon.com/scheduler/latest/UserGuide/configuring-schedule-dlq.html) | SQS standard queue behavior and dead-letter evidence |
| [EventBridge retry behavior](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-retry-policy.html) | Exponential backoff, retry duration and need for DLQ |
| [AWS Config conformance packs](https://docs.aws.amazon.com/config/latest/developerguide/conformance-packs.html) | Declarative control bundles as an adjacent AWS compliance pattern |
| [AWS Audit Manager availability change](https://docs.aws.amazon.com/audit-manager/latest/userguide/audit-manager-availability-change.html) | Maintenance mode; no new-account setup after 2026-04-30, therefore not a core dependency |
| [DynamoDB pricing and free tier](https://aws.amazon.com/dynamodb/pricing/) | Provisioned free-tier capacity, 25 GB storage and on-demand/provisioned choices |
| [Lambda pricing and free tier](https://aws.amazon.com/lambda/pricing/) | One million requests and 400,000 GB-seconds per month in the free tier |
| [API Gateway pricing and free tier](https://aws.amazon.com/api-gateway/pricing/) | Request-based pricing and new-customer API allowances |
| [EventBridge pricing](https://aws.amazon.com/eventbridge/pricing/) | Scheduler free-tier statement and event-based pricing |
| [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/) | Five-GB free-tier logs allowance and telemetry-volume cost risk |
| [CloudWatch log classes](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatch_Logs_Log_Classes.html) | Standard versus lower-ingestion-cost Infrequent Access trade-offs |
| [AgentCore pricing](https://aws.amazon.com/bedrock/agentcore/pricing/) | Consumption-based pricing, no upfront minimum and example per-session resource costing |
| [AWS Free Tier FAQ](https://aws.amazon.com/free/free-tier-faqs/) | Current up-to-USD-200 credit model, eligibility, account plans and expiry cautions |
| [AWS Pricing Calculator](https://calculator.aws/) | Required pre-deployment regional estimate rather than a blanket “free” claim |

## Standards, monitoring and regulation

| Source | Evidence used |
|---|---|
| [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) | Voluntary trustworthy-AI risk framework and lifecycle focus |
| [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) | Continuous/timely risk management; Govern, Map, Measure, Manage; post-deployment monitoring and incident response |
| [NIST AI RMF 1.0 publication](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10) | Authoritative framework publication and scope |
| [NIST AI 800-4, Challenges to Monitoring Deployed AI Systems](https://www.nist.gov/publications/challenges-monitoring-deployed-ai-systems-center-ai-standards-and-innovation) | 2026 evidence that post-deployment monitoring is necessary and current practice remains fragmented |
| [NIST summary of monitoring challenges](https://www.nist.gov/news-events/news/2026/03/new-report-challenges-monitoring-deployed-ai-systems) | Functional, operational and other monitoring categories; burden, cadence and human/automated oversight questions |
| [EU AI Act official overview](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) | Logging, human oversight, monitoring and provider post-market monitoring overview |
| [EU AI Act Article 72 text](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng) | Active, systematic collection/documentation/analysis for continuous compliance of high-risk systems |
| [EU AI Act navigation FAQ](https://digital-strategy.ec.europa.eu/en/faqs/navigating-ai-act) | Deployer monitoring, human oversight, incident action and traceability overview |
| [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/) | Vendor-neutral telemetry conventions |
| [OpenTelemetry GenAI conventions repository](https://github.com/open-telemetry/semantic-conventions/tree/main/docs/gen-ai) | Current GenAI, agent, model and MCP telemetry work after documentation move |

## Direct competitors and adjacent products

These sources validate the category. They do not independently prove product efficacy.

| Source | Capability relevant to comparison |
|---|---|
| [ServiceNow AI Control Tower](https://www.servicenow.com/products/ai-control-tower.html) | AI inventory, lifecycle governance, continuous compliance, runtime agent monitoring, value and workflow integration |
| [ServiceNow May 2026 AI Control Tower release](https://newsroom.servicenow.com/press-releases/details/2026/ServiceNow-expands-AI-Control-Tower-to-discover-observe-govern-secure-and-measure-AI-deployed-across-any-system-in-the-enterprise/default.aspx) | Live metrics/alerts, Traceloop runtime observability, risk frameworks, MCP gateway and action controls |
| [IBM watsonx.governance model governance](https://www.ibm.com/products/watsonx-governance/model-governance) | Factsheets, third-party model governance, lifecycle metrics, drift/safety/quality monitoring |
| [IBM watsonx.governance plans](https://www.ibm.com/docs/en/watsonx/saas?topic=watsonxgovernance-plans) | Agentic catalog, production-agent monitoring, thresholds and GRC capabilities |
| [IBM AI assurance direction, Think 2026](https://www.ibm.com/think/perspectives/ai-governance-to-assurance-what-we-shared-think-2026) | Continuous visibility, enforceable controls and live metrics linked to controls/owners |
| [IBM Agentic Control Plane](https://www.ibm.com/products/watsonx-orchestrate/governance-and-observability) | Multi-platform agent operations, policy, reliability, cost and observability |
| [OneTrust Dynamic Risk Scoring](https://www.onetrust.com/solutions/ai-governance/dymanic-risk-scoring/) | Production telemetry, policy/business context, continuous risk scores and downstream enforcement |
| [MLflow production tracing and monitoring](https://mlflow.org/docs/latest/genai/tracing/prod-tracing) | Async traces, sampling, continuous judges, cost/latency and user feedback |
| [MLflow production-trace evaluation](https://www.mlflow.org/docs/latest/genai/eval-monitor/running-evaluation/traces/) | Reuse of production traces, custom scorers, full agent trajectory and feedback |
| [MLflow tracing](https://mlflow.org/docs/latest/genai/tracing) | Open-source, self-hosted, OTel-compatible and framework-agnostic observability |
| [LangSmith evaluation](https://docs.langchain.com/langsmith/evaluation) | Offline/online evaluation, production traces, sampling, alerts and feedback loop |

## Anthropic and current agentic engineering

| Source | Evidence used |
|---|---|
| [Anthropic, Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) | Simplest architecture first; workflow/agent distinction; tools, memory, MCP and evaluator-optimizer patterns |
| [Anthropic, Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | Multi-turn/trajectory evaluation, agent loops, tools, state and real task grading |
| [Anthropic, Long-running Claude for Scientific Computing](https://www.anthropic.com/research/long-running-Claude) | Persistent memory, test oracles and bounded verification loops |
| [Anthropic, Building Effective AI Agents 2026 guide](https://resources.anthropic.com/building-effective-ai-agents) | Single-agent, multi-agent and workflow selection; context, skills and production patterns |
| [Model Context Protocol](https://docs.anthropic.com/en/docs/mcp) | Standardized connection of models to tools and data |
| [Claude Code setup](https://docs.anthropic.com/en/docs/claude-code/getting-started) | Claude app subscription use for Claude Code and separate enterprise provider options |
| [Claude Code CLI reference](https://docs.anthropic.com/en/docs/claude-code/cli-usage) | Bounded turns, allowed/disallowed tools, JSON automation and MCP configuration |
| [Claude Code memory](https://docs.anthropic.com/en/docs/claude-code/memory) | Project/user memory via `CLAUDE.md` and explicit memory management |
| [Claude Agent Skills best practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices) | Progressive disclosure, concise skill design, explicit errors and verification/evaluation expectations |

## User-provided Databricks guides in connected Google Drive

The Drive account was readable during this research. Eight Databricks/MIT files were discovered and their extracted text was scanned end to end for the production, governance, evaluation, monitoring, data, memory, RAG and cost sections. These are private/user-supplied background sources; reviewers may not be able to open them unless the user includes permitted copies in the private submission.

| Drive file | Relevant evidence used |
|---|---|
| [State-of-AI-Agents-2026-Final.pdf](https://drive.google.com/file/d/1AR0pMh__v5uw-UcGqL4Ayd3LfQO9F17E) | Multi-agent growth, multi-model strategy, production evaluation, governance and lifecycle feedback |
| [making-ai-deliver-2026-report-new.pdf](https://drive.google.com/file/d/1pCDLQuDoCfKdk8XnH06F9O_dnJv-gQUz) | Governance thinning after go-live, monitored/governed services, business outcomes, observability and multi-agent complexity |
| [2026-03-eb-big-book-of-genai-ss-200225.pdf](https://drive.google.com/file/d/11v1RFdI8jui0ZWAXN9JXTbv-cD2ZaB5M) | Reliability wall, traces/assessments/evaluation data model, lifecycle monitoring, AgentOps and tool governance |
| [hands-on-guide-apps-databricks.pdf](https://drive.google.com/file/d/1JchRP7p-NBSYGjGikllnVKYfyvS23I-k) | Production deployment, OAuth, CI/CD, operational state, memory, cost/freshness trade-offs and avoiding policy drift |
| [Databricks Compact Guide to RAG, 2nd edition](https://drive.google.com/file/d/1NavkDcPkDLETCIE9cVAMYpPQdtEUVxc8) | RAG lifecycle, retrieval/evaluation/feedback, production quality/cost/latency and why RAG is optional rather than universal |
| [MIT Technology Review Data and AI 2025](https://drive.google.com/file/d/1WXspxaZr8YtZdQ6r59gfKElk0rSzeIE4) | Agentic AI raises data-governance stakes; quality, openness, explainability and measurable customer outcomes |
| [MIT CIO Generative AI Report](https://drive.google.com/file/d/1O6G4oqtraTvGuIhiPJ2VEBaHtN9Ki2Iq) | Unified governance, privacy, data infrastructure and enterprise production concerns |
| [big-book-data-engineering.pdf](https://drive.google.com/file/d/1TJgMAaGhU20Yi4FeQ3wib83w5XXDVN3o) | Data observability, freshness, drift, lineage, pipeline failure handling and cost reporting |

## Public Databricks and MLflow documentation

| Source | Evidence used |
|---|---|
| [Databricks agent documentation](https://docs.databricks.com/aws/en/agents/) | End-to-end agent lifecycle and production deployment patterns |
| [Databricks evaluation and monitoring](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor) | Agent evaluation, monitoring, human feedback and production improvement |
| [MLflow GenAI overview](https://www.mlflow.org/docs/latest/genai/overview/) | Continuous improvement from production traces and customer/domain feedback |
| [MLflow production monitoring](https://mlflow.org/docs/latest/genai/tracing/prod-tracing) | Async logging, production SDK, sampling and continuous quality evaluation |

## Coursera Plus verification

| Course | Verification and fit |
|---|---|
| [Building AI Agent Harnesses with Strands Agents](https://www.coursera.org/learn/build-ai-agents) | Page showed Coursera Plus inclusion, six hours, updated July 2026; covers MCP, hooks/plugins/skills, context/memory, multi-agent patterns, trajectory/multi-turn evaluation and AgentCore cloud deployment |
| [DevOps and AI on AWS: CI/CD for Generative AI Applications](https://www.coursera.org/learn/cicd-generative-ai-apps) | Page showed Coursera Plus inclusion; covers CI/CD, reliable automation, monitoring and observability |
| [DevOps and AI on AWS specialization](https://www.coursera.org/specializations/devops-ai-aws) | Page showed Coursera Plus inclusion; three-course option if the user wants the broader DevOps flywheel |

Coursera inclusion and course content can change. Verify the badge while signed into the user's Coursera account immediately before enrolling.

## Source-use cautions

- Product pages establish vendor claims, not independent comparative performance.
- Aivar and customer case-study metrics are self-reported.
- The 2026 Databricks reports use Databricks product telemetry and survey data; they are directional evidence, not universal market measurements.
- The EU AI Act sources must be reviewed with qualified legal counsel for a real regulated deployment.
- OpenTelemetry GenAI conventions are evolving; pin schema versions and test adapters.
- AWS features, regions, limits, free tiers and prices can change. Recheck before deployment.
- A ChatGPT/Claude subscription is not a substitute for production API/cloud billing.
- ProofLoop should claim evidence support and operational assurance, not legal certification.
