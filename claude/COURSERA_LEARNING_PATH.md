# Coursera Plus Learning Path for the Agent WAF Project
*Researched & verified 2026-07-12 — every item below shows "Included with Coursera Plus" on its Coursera page.*

---

## ★ DevOps + AWS track — NON-NEGOTIABLE for Aivar (verified Jul 13)
*Intel from past Aivar interviewees: DevOps + AWS are non-negotiable. 30–40h budget.
Do this in the POST-task / interview-prep window (NOT this crunch week — see WEEK_PLAN.md).
All three below are AWS-official and Coursera-Plus-included → maximum credibility with
ex-AWS founders, and they run on Amazon Bedrock, Aivar's actual LLM platform.*

**Core (~32h):**
1. **AWS Cloud Technical Essentials** (AWS) — ~20h. AWS foundation: IAM, Lambda, S3,
   DynamoDB, EC2, CloudWatch. Non-negotiable base (you have no AWS yet).
   https://www.coursera.org/learn/aws-cloud-technical-essentials
2. **DevOps and AI on AWS: CI/CD for Generative AI Applications** (AWS) — ~12h. THE core
   DevOps course: CI/CD pipelines, IaC (CloudFormation + CDK), monitoring (CloudWatch,
   X-Ray) — built on Bedrock. https://www.coursera.org/learn/cicd-generative-ai-apps

**Stretch to ~38h (do if time):**
3. **DevOps and AI on AWS: AIOps** (AWS) — ~6h. Anomaly detection, automated remediation,
   observability — remarkably aligned with Aivar's AI-governance/monitoring focus.
   https://www.coursera.org/learn/aiops-aws

Both #2 and #3 are part of the **DevOps and AI on AWS Specialization** (3 courses, ~26h,
Coursera Plus, by AWS). The 3rd course in it — "Upgrading Apps with Generative AI" (8h) —
is app-building, less DevOps; skip within a 30–40h budget.

**Sequencing:** #1 first (foundation) → #2 → #3. **Timing: interview-prep window, after
Saturday's task submission and the tests.** This week, let Claude Code write the task's
AWS IaC/CI-CD; backfill deep understanding with these courses after.

**Why this set wins:** covers BOTH Aivar non-negotiables (AWS + DevOps) in one AWS-official
path, on Aivar's exact stack (Bedrock), and every piece is directly reusable as the
DevOps wrapper (IaC + CI/CD + monitoring) around your PS-3.2 ML detector.

---

## The one course to do: IBM RAG and Agentic AI Professional Certificate
**https://www.coursera.org/professional-certificates/ibm-rag-and-agentic-ai**
✅ Included with Coursera Plus · Python · Advanced level · 10 courses (~100 h total, but see the shortcut below)

This is the single best match for what you will actually implement: agents, tool
calling, MCP, and RAG — all in Python, all hands-on labs, matching your data-science
background.

**Time-boxed shortcut (~45 h instead of ~100 h).** Coursera Plus lets you enroll in the
individual courses directly, so do only these four, in this order:

| Order | Course | Hours | Maps to project |
|---|---|---|---|
| 1 | Fundamentals of Building AI Agents | 11 | Agent loop, tool calling — what our sample agents do |
| 2 | **Build AI Agents using MCP** | 10 | The core of the project: MCP servers, clients, secure agent–tool workflows — our WAF *is* an MCP gateway |
| 3 | Build RAG Applications: Get Started | 7 | RAG + embeddings — powers the optional semantic-scope check |
| 4 | RAG and Agentic AI Capstone Project | 14 | End-to-end production-style build |

Skip (for this project): multimodal course, CrewAI/AutoGen/BeeAI course, vector-DB
deep-dives — good content, not on our critical path.

## AWS from zero — do this FIRST (you have no AWS background)

**AWS Cloud Technical Essentials** — offered by **Amazon Web Services**
https://www.coursera.org/learn/aws-cloud-technical-essentials
✅ Included with Coursera Plus · ~20 h · Beginner (no prerequisites) · hands-on labs

This is the right starting point. It's AWS's own beginner course and it covers *exactly*
the services this project uses, with guided labs so you actually click through the
console instead of just watching:

| Course topic | Where it's used in the project |
|---|---|
| Compute: **EC2, Lambda, ECS** | Our detection/proxy service runs on **Lambda** |
| Storage: **S3**, EBS | Policy docs / RAG corpus / audit evidence on **S3** |
| Databases: RDS, **DynamoDB** | Baseline, session state, audit log in **DynamoDB** |
| Security: **IAM**, shared-responsibility model | Least-privilege roles for every component |
| Monitoring: **CloudWatch** | Logs, metrics, health checks |

Labs: Intro to IAM, Creating a VPC, Configuring a Web Application, High Availability.
After this, the AWS console stops being scary and the serverless course below makes sense.

*(Optional pre-step if you feel totally lost: "AWS Cloud Practitioner Essentials"
https://www.coursera.org/learn/aws-cloud-practitioner-essentials — also in Coursera Plus,
gentler and more conceptual, ~ a few hours. Only if the Technical Essentials course feels
too fast. For a data scientist who codes, you can likely skip straight to Technical
Essentials.)*

## Then: Python for Serverless Applications and Automation on AWS
**https://www.coursera.org/learn/aws-python-serverless**
✅ Included with Coursera Plus · Offered by **Amazon Web Services** itself · ~10 h · Beginner

Covers **exactly our deployment stack**: Lambda, API Gateway, DynamoDB, and AWS SAM
deployment, in Python. Ten hours, official AWS content — this is the deployment half of
the project that the IBM certificate doesn't cover. Given the evaluators are ex-AWS,
being able to say "deployed with SAM per AWS's own best practices" is worth the 10 hours.

## Alternative (if you prefer a Claude-centric path)
**AI Agents with Model Context Protocol Specialization — Vanderbilt University (Dr. Jules White)**
https://www.coursera.org/specializations/ai-agents-model-context-protocol
✅ Included with Coursera Plus · ~31 h · Beginner

Contains "AI Agents with Model Context Protocol" (7 h), "Prompt Engineering for
ChatGPT" (19 h), and **"Claude Code: Software Engineering with Generative AI Agents"
(5 h)** — the only Coursera content on Claude Code itself, which is your build tool.
Caveat: the MCP course is TypeScript, our build is Python (concepts transfer 1:1).
If short on time, take just the 5-hour Claude Code course from this specialization as
a supplement.

## Not recommended as primary
**Hands-on Agentic AI: Building Intelligent Agents** (8-course specialization,
https://www.coursera.org/specializations/hands-on-agentic-ai-building-intelligent-agents)
✅ In Coursera Plus and topically the closest to "AI governance" (MCP + governance +
risk courses), but it is Coursera-instructor-network content (not IBM/AWS/university),
GPT/LangGraph-centric, and shallower per course (3–4 h each). Use only as skim material
for governance vocabulary for the PDF write-up.

## Suggested sequencing against the build plan
0. **Before anything, since you have no AWS background:** AWS "Cloud Technical
   Essentials" (~20 h) — do the IAM, S3, DynamoDB, Lambda, CloudWatch labs. This is the
   confidence-builder.
1. **Before Phase 1–2** (agent + detector core): IBM "Fundamentals of Building AI
   Agents" + "Build AI Agents using MCP".
2. **Before Phase 4** (AWS deployment): AWS "Python for Serverless Applications and
   Automation on AWS" (~10 h) — Lambda + API Gateway + DynamoDB + SAM specifically.
3. **In parallel / evenings:** Vanderbilt Claude Code course (5 h) to sharpen the
   dev workflow; IBM RAG course only if you implement the RAG/semantic scenario.

## Realistic AWS time budget for this project
~30 hours of AWS coursework total (20 + 10). You do **not** need to become an AWS expert:
- You need to understand IAM roles, Lambda, DynamoDB, S3, CloudWatch, and `sam deploy` —
  enough to explain your architecture in the video and answer "why this service?"
- **Claude Code will write nearly all the AWS/IaC (SAM templates, IAM policies, Lambda
  handlers) for you.** Your job is to *understand and defend* it, not memorize syntax.
- The interview risk is being unable to explain what you deployed — the two AWS courses
  close exactly that gap. That's a ~30-hour investment against a job. Worth it.

## Honest note
Not knowing AWS is normal for a data scientist and it is not a blocker here. Every
service in these plans is beginner-tier and serverless (no servers to manage, generous
free tier). The learning curve is real but shallow, and building the project hands-on
with Claude Code *is* the fastest way to actually learn it — the courses give you the
mental model, the build gives you the muscle memory.
