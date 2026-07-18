# EXPLAINER — REFERENCE SET (the answer key)
*This is the CLEAN set (no "my words" space). Claude Code fills these explanations during
the build. It's your answer key + the "How it works" section of the required PDF.*
*Your closed-book practice lives in `EXPLAINER_workbook.md` — fill THAT from memory first,
then open THIS to self-check. Don't write your own-words version here; keep this pristine.*

**How to use:** for each item — (1) What it is in plain English, (2) an analogy,
(3) how OUR project uses it, (4) why it matters / what breaks without it.

---

## PART 1 — The problem domain
### Prompt injection (esp. indirect/behavioral)
- What it is:
- Analogy:
- How our project addresses it:
- Why it matters:

### Agentic AI / the agent loop (plan → act → observe)
- What it is:
- Analogy:
- How our project uses it:
- Why it matters:

### MCP (Model Context Protocol)
- What it is:
- Analogy: (e.g., "a USB-C standard for connecting agents to tools")
- How our project uses it:
- Why it matters:

## PART 2 — The ML / data-science core (my strength — explain confidently)
### Behavioral baseline / fingerprint
- What it is:  | Analogy:  | Our use:  | Why:

### Anomaly score (multi-signal)
- What it is:  | Analogy:  | Our use:  | Why:

### Calibration & threshold / false-positive tradeoff
- What it is:  | Analogy:  | Our use:  | Why:

### Drift (why "normal" changes over time)
- What it is:  | Analogy: (my IoT-IDS F1 0.999→0.387 story)  | Our use:  | Why:

## PART 3 — AWS / DevOps (the non-negotiables — explain what I deployed)
### Lambda  | ### API Gateway  | ### DynamoDB  | ### S3  | ### IAM  | ### CloudWatch
- (each) What it is | Analogy | Our use | Why this service over alternatives

### Infrastructure as Code (SAM / CloudFormation / CDK)
- What it is:  | Analogy: ("the blueprint that rebuilds the whole house identically")  | Our use:  | Why:

### CI/CD pipeline (GitHub Actions)
- What it is:  | Analogy:  | Our use:  | Why:

### Observability (OpenTelemetry / CloudWatch, health checks)
- What it is:  | Analogy:  | Our use:  | Why:

## PART 4 — The LLM bits
### Tokens / context window / temperature
### Prompting vs RAG vs fine-tuning
### LLM evaluation / hallucination
- (each) What it is | Analogy | Our use | Why

---
*Interview tip: for every item, be able to say it in ONE plain sentence + ONE analogy.
If you can't, you don't understand it yet — go back to the code with Claude Code.*
