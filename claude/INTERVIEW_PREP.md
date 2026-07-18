# Aivar AI-Interview Prep — for AFTER the task round
*This round is GATED: you only face it if you clear the task. So this is a POST-SATURDAY
plan, not a this-week one. Start light after you submit the task; ramp once you know you
cleared / have an interview date. TCS is Sunday 8am — nothing here happens before then.*

## Mindset
- You can't prep "everything," and the interviewer isn't grading trivia. AI interviews
  test **reasoning + depth on core topics + your own project**. Clear thinking > recall.
- **Your strongest material is the project you just built.** ~60% of likely questions
  (RAG, agentic AI, MCP, LLMs, prompt engineering, ML-in-production) you can answer from
  what you built and your existing projects. Anchor answers in real work you've done.

## What they'll likely probe (Aivar = governed agentic AI on AWS/Bedrock, RAG, MLOps)
1. **Your Aivar project** — deepest area. Every decision, tradeoff, "why". Rehearse the
   "can I explain it?" checklist in WEEK_PLAN.md.
2. **RAG** — chunking, embeddings, vector DBs, retrieval, reranking, grounding/citations,
   hallucination, RAG evaluation (faithfulness, context relevance).
3. **Agentic AI + MCP** — agent loop (plan/act/observe), tool use, memory, multi-agent,
   guardrails, failure modes, prompt injection (your PS-3.2 = direct talking point).
4. **LLMs** — tokens, context window, temperature/top-p, prompting vs RAG vs fine-tuning,
   hallucination, evaluation/evals.
5. **Prompt engineering** — few-shot, chain-of-thought, structured output, system prompts.
6. **ML in production / MLOps** — data & model drift, monitoring, evaluation, deployment,
   CI/CD, A/B testing (your detector's baseline/calibration/drift = direct talking point).
7. **Basic ML/DL fundamentals** — the one real gap to shore up (see below).

## Fundamentals to be able to explain crisply (you've USED all of these)
- Bias–variance, overfitting/underfitting, regularization (L1/L2, dropout).
- Train/val/test, cross-validation (you used stratified CV in the deepfake project).
- Metrics: precision, recall, F1, ROC-AUC, confusion matrix (you use these constantly).
- Gradient descent, backprop, loss functions (cross-entropy, MSE).
- Architectures: CNN (deepfake), ResNet (unlearning), Transformer/attention (HF clinical
  LLM), embeddings. You've touched each — just be able to say how/why they work.
- Class imbalance handling (you used imbalanced-learn/SMOTE in IoT-IDS).
- Anchor every fundamentals answer in YOUR project: "I saw this in my IoT-IDS work when…"

## Resources (free + your Coursera Plus)
- **Fundamentals:** Google Machine Learning Crash Course (free) — the one you mentioned.
  Fast, practical, exactly right for articulation polish.
- **ML in production / MLOps (the "blogs kind"):** Google "Rules of Machine Learning"
  (Zinkevich, free); Made With ML by Goku Mohandas (free); Chip Huyen's blog / "Designing
  ML Systems" concepts.
- **RAG:** IBM "Build RAG Applications" + "Vector Databases for RAG" (Coursera Plus), or
  faster: Anthropic docs + one solid blog.
- **Agentic AI + prompt engineering:** Anthropic's "Building effective agents" and the
  Prompt Engineering guide (both free, and Aivar is Anthropic/Bedrock-based — high signal);
  Vanderbilt MCP + Prompt Engineering courses (Coursera Plus).
- **LLMs overview:** Anthropic docs; any reputable "how LLMs work" primer.

## Suggested post-task sequence (only after Saturday submission)
1. First: re-derive and rehearse your OWN project cold (highest ROI, zero new learning).
2. Then: Google ML Crash Course + fundamentals articulation (your stated gap).
3. Then: Anthropic agents + prompt-engineering guides (free, directly on-target).
4. Then: RAG + MLOps concepts if interview date allows.
Depth order = project > fundamentals-articulation > agentic/prompt > RAG/MLOps.

## Note
Building the task well IS interview prep for topics 2–6. The task and this interview are
synergistic — understanding what you build now pays off directly in the interview later.
