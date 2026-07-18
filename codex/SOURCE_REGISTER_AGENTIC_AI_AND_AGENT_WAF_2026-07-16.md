# Source Register — Agentic AI, Aivar, Agent WAF and Production Engineering

**Compiled:** 2026-07-16  
**Purpose:** Primary-source companion to the Codex problem-selection research  
**Policy:** Prefer official documentation and first-party engineering evidence. Vendor outcome figures are treated as self-reported.

## Assignment and Aivar

- Local assignment: /Users/srisruthi/Downloads/Problem_Statements_Aivar.docx
- Aivar About Us: https://www.aivar.tech/about-us
- Aivar Velogent: https://www.aivar.tech/velogent-ai
- Aivar Kubogent: https://www.aivar.tech/kubogent-ai
- Aivar freight-invoice case: https://www.aivar.tech/case-studies/automating-freight-invoice-processing-for-a-leading-logistics-platform-with-aws-and-generative-ai
- Aivar invoice automation case: https://www.aivar.tech/case-studies/ai-powered-invoice-processing-automation-for-global-logistics-provider
- Aivar Reva policy-management case: https://www.aivar.tech/case-studies/reva-ai-transforming-enterprise-policy-management-with-generative-ai-on-aws
- Aivar ITSM case: https://www.aivar.tech/case-studies/automated-it-service-management-for-a-global-cpaas-provider

## Agent architecture and Anthropic

- Anthropic, Building Effective Agents: https://www.anthropic.com/engineering/building-effective-agents
- Claude Code Skills: https://code.claude.com/docs/en/slash-commands
- Claude Code memory: https://code.claude.com/docs/en/memory
- Model Context Protocol introduction: https://modelcontextprotocol.io/docs/getting-started/intro
- MCP specification: https://modelcontextprotocol.io/specification/latest
- Anthropic 2026 State of AI Agents report: https://resources.anthropic.com/hubfs/The%202026%20State%20of%20AI%20Agents%20Report.pdf

## AWS AgentCore and current AWS agent platform

- AgentCore overview: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/
- AgentCore release notes: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/release-notes.html
- AgentCore Gateway: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html
- AgentCore Policy: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html
- Policy GA announcement: https://aws.amazon.com/about-aws/whats-new/2026/03/policy-amazon-bedrock-agentcore-generally-available/
- Policy concepts: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-core-concepts.html
- Policy creation: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-create-policies.html
- Policy scope: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-scope.html
- Policy limitations: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-limitations-section.html
- Policy LOG_ONLY/testing: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-test-a-policy.html
- Policy metrics and spans: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-policy-metrics.html
- Gateway interceptors: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-interceptors.html
- Interceptor types/limits: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-interceptors-types.html
- Use Gateway with Policy: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/use-gateway-with-policy.html
- AgentCore Observability: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html
- Gateway observability: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-gateway-metrics.html
- AgentCore evaluation types: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations-types.html
- AgentCore Evaluate API: https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_Evaluate.html
- AgentCore Memory: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html
- AgentCore Identity/OBO: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-behalf-of-token-exchange.html
- AgentCore Registry concepts: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/registry-concepts.html
- AgentCore Payments: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/payments-how-it-works.html
- AWS WAF for AgentCore: https://aws.amazon.com/about-aws/whats-new/2026/06/aws-waf-amazon-bedrock-agentcore/
- AWS Agentic AI Well-Architected Lens: https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentic-ai-lens.html
- Agent design principles: https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/design-principles.html
- Orchestration cost controls: https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentcost01.html
- Model/token optimization: https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentcost02.html
- Cost attribution: https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentcost05.html
- AgentOps guidance: https://aws.amazon.com/blogs/machine-learning/agentops-operationalize-agentic-ai-at-scale-with-amazon-bedrock-agentcore/
- Amazon real-world agent evaluation: https://aws.amazon.com/blogs/machine-learning/evaluating-ai-agents-real-world-lessons-from-building-agentic-systems-at-amazon/
- Operationalizing Agentic AI: https://aws.amazon.com/blogs/machine-learning/operationalizing-agentic-ai-part-1-a-stakeholders-guide/
- Bedrock Agents maintenance notice: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-how.html

## Production engineering on AWS

- DynamoDB transactions: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html
- DynamoDB IAM condition keys: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/specifying-conditions.html
- Lambda with SQS and idempotency implications: https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html
- SQS/Lambda scaling controls: https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-scaling.html
- Step Functions callback pattern: https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html
- API Gateway throttling: https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html
- CloudWatch sensitive-data masking: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/mask-sensitive-data.html
- GitHub Actions OIDC with AWS: https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws
- Terraform AWS provider: https://registry.terraform.io/providers/hashicorp/aws/latest/docs

## Pricing

- AgentCore pricing: https://aws.amazon.com/bedrock/agentcore/pricing/
- Bedrock pricing: https://aws.amazon.com/bedrock/pricing/
- Lambda pricing: https://aws.amazon.com/lambda/pricing/
- DynamoDB pricing: https://aws.amazon.com/dynamodb/pricing/
- AWS WAF pricing: https://aws.amazon.com/waf/pricing/
- Step Functions pricing: https://aws.amazon.com/step-functions/pricing/
- CloudWatch pricing: https://aws.amazon.com/cloudwatch/pricing/

## Direct Agent WAF competitors and adjacent controls

- Microsoft MCP Security Gateway specification: https://microsoft.github.io/agent-governance-toolkit/specs/MCP-SECURITY-GATEWAY-1.0/
- Microsoft, Securing MCP: https://developer.microsoft.com/blog/securing-mcp-a-control-plane-for-agent-tool-execution
- Microsoft Agent Control Specification: https://microsoft.github.io/agent-governance-toolkit/packages/agent-control-specification/
- Microsoft AGT Quick Start: https://microsoft.github.io/agent-governance-toolkit/quickstart/
- Google Agent Gateway/IAM announcement: https://cloud.google.com/blog/products/identity-security/whats-new-in-iam-security-governance-and-runtime-defense
- Google Agent Gateway codelab: https://codelabs.developers.google.com/agw-cuj-arun-egress-gmcp
- Cisco AI Defense data sheet: https://www.cisco.com/c/en/us/products/collateral/security/ai-defense/ai-defense-ds.html
- Cisco Zero Trust for agentic AI: https://www.cisco.com/c/en/us/solutions/collateral/artificial-intelligence/security/zero-trust-agentic-ai-wp.html
- Palo Alto Prisma AIRS runtime security: https://www.paloaltonetworks.com/prisma/prisma-ai-runtime-security/ai-runtime-security
- Palo Alto agent security: https://www.paloaltonetworks.com/prisma/agent-security
- Lakera Agent Behavior Defense: https://docs.lakera.ai/docs/agent-behavior-defense
- Portkey MCP Gateway: https://portkey.ai/docs/product/mcp-gateway
- Portkey budgets/rate limits: https://portkey.ai/docs/product/administration/enforce-budget-and-rate-limit
- Portkey parameter guardrail: https://portkey.ai/docs/integrations/guardrails/request-parameters-check
- Cloudflare MCP Portals: https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/mcp-portals/
- Cloudflare AI Gateway rate limiting: https://developers.cloudflare.com/ai-gateway/features/rate-limiting/
- Cloudflare AI Gateway logging: https://developers.cloudflare.com/ai-gateway/observability/logging/
- Pipelock open source: https://github.com/luckyPipewrench/pipelock
- Invariant Guardrails: https://github.com/invariantlabs-ai/invariant
- OPA decision logs and masking: https://www.openpolicyagent.org/docs/management-decision-logs
- OPA/Envoy external authorization: https://www.openpolicyagent.org/docs/envoy
- Cedar validation: https://docs.cedarpolicy.com/policies/validation.html
- A2A specification: https://github.com/a2aproject/A2A/blob/main/docs/specification.md

## Databricks and MLflow

- Databricks agents documentation: https://docs.databricks.com/aws/en/agents/
- Databricks agent concepts and production guidance: https://docs.databricks.com/aws/en/agents/concepts/
- Databricks author/deploy agent guidance: https://docs.databricks.com/aws/en/agents/agent-framework/author-agent
- Databricks agent tools and MCP: https://docs.databricks.com/aws/en/agents/agent-framework/agent-tool
- Databricks evaluation and monitoring: https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor
- Databricks compact guide to agent systems: https://www.databricks.com/sites/default/files/2025-03/databricks-ebook-a-compact-guide-to-agent-systems.pdf
- Databricks AI governance framework: https://www.databricks.com/br/sites/default/files/2025-06/databricks-183717-whitepaper-databricks-ai-governance-framework.pdf
- MLflow agent tracing: https://mlflow.org/docs/latest/genai/tracing
- MLflow GenAI overview: https://mlflow.org/docs/latest/genai/overview/
- MLflow production-trace evaluation: https://www.mlflow.org/docs/latest/genai/eval-monitor/running-evaluation/traces/

## Observability standards

- OpenTelemetry semantic conventions: https://opentelemetry.io/docs/specs/semconv/
- OpenTelemetry GenAI conventions repository: https://github.com/open-telemetry/semantic-conventions/tree/main/docs/gen-ai

## Production use-case evidence

- BNY annual report: https://www.bny.com/corporate/global/en/investor-relations/annual-report-2025.html
- BNY enterprise AI platform: https://www.bny.com/corporate/global/en/insights/unlocking-potential-enterprise-ai-platform-bny.html
- Uber agent identity: https://www.uber.com/us/en/blog/solving-the-agent-identity-crisis/
- Uber QueryGPT: https://www.uber.com/gb/en/blog/query-gpt/
- Uber enhanced agentic RAG: https://www.uber.com/de/en/blog/enhanced-agentic-rag/
- Amazon Q modernization: https://press.aboutamazon.com/2024/12/new-amazon-q-developer-capabilities-accelerate-large-scale-transformations-of-legacy-workloads
- DoorDash agent support architecture: https://aws.amazon.com/blogs/machine-learning/deploy-generative-ai-agents-in-your-contact-center-for-voice-and-chat-using-amazon-connect-amazon-lex-and-amazon-bedrock-knowledge-bases/
- Apollo Tyres manufacturing reasoner: https://aws.amazon.com/blogs/machine-learning/how-apollo-tyres-is-unlocking-machine-insights-using-agentic-ai-powered-manufacturing-reasoner/
- Cox Automotive: https://aws.amazon.com/solutions/case-studies/cox-auto-case-study/
- Morgan Stanley: https://openai.com/index/morgan-stanley/
- Kaiser Permanente ambient AI: https://divisionofresearch.kaiserpermanente.org/ai-assisted-notetaking-gains-steady-support-from-kaiser-permanente-physicians/
- Rexera: https://aws.amazon.com/solutions/case-studies/bedrock-rexera/
- Genentech research agent: https://aws.amazon.com/solutions/case-studies/genentech-generativeai-case-study/
- Spotify multi-agent advertising: https://engineering.atspotify.com/2026/2/our-multi-agent-architecture-for-smarter-advertising
- Walmart agentic strategy: https://corporate.walmart.com/news/2025/05/29/inside-walmarts-strategy-for-building-an-agentic-future
- Druva and Cox with AgentCore/Claude: https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-agentcore-and-claude-transforming-business-with-agentic-ai/

## Coursera Plus verification

- Recommended course, Building AI Agent Harnesses with Strands Agents: https://www.coursera.org/learn/build-ai-agents
- Optional DevOps course: https://www.coursera.org/learn/cicd-generative-ai-apps
- AWS Cloud Technical Essentials: https://www.coursera.org/learn/aws-cloud-technical-essentials
- Vanderbilt MCP specialization: https://www.coursera.org/specializations/ai-agents-model-context-protocol

At the research date, the first two recommended items displayed inclusion with Coursera Plus. Catalog inclusion can change; verify the badge while signed into the user's Coursera account before enrolling.

## Source-use cautions

- Aivar and vendor case-study outcome figures are self-reported.
- A product page demonstrates a claimed capability, not independent efficacy.
- Preview features and service limits can change.
- Current pricing is region-, model- and usage-dependent.
- OpenTelemetry GenAI conventions continue to evolve.
- Public architecture reports rarely disclose all token ceilings, error rates or security incidents.
- No source supports claiming that AegisFlow is the first or only agent firewall.
