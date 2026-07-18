# ProofLoop PS-6.2 — Submission ZIP Allowlist & Exclusion Plan (Track F1)

**Read-only plan.** Nothing here was executed. The candidate runs the packaging
step. Goal: a ZIP the evaluator can independently verify — code, README, docs,
deployment scripts, PDF, video — with **zero** secrets, caches, transcripts, or
internal scratch. The ZIP is shared as a link-host URL (e.g., Google Drive
"anyone with the link"); **not** a public GitHub/LinkedIn/social post.

## ✅ INCLUDE (evaluator needs these)

| Path | Why |
|---|---|
| `src/**` | the implementation |
| `tests/**` | reproducible verification |
| `README.md` | required; setup + status + claims |
| `pyproject.toml` | build/deps (`pytest>=9.0.3,<10`, dev tools) |
| `infra/template.yaml` | SAM deployment definition |
| `infra/scripts/**` (`validate_template.py`, `verify_built_handlers.py`) | documented automated deploy/verify scripts |
| `infra/lambda/**`, `infra/README.md` | Lambda build + deploy docs |
| `scripts/**` (`demo_*.py`, `smoke_bedrock_invoice.py`) | demos + gated smoke |
| `dashboard/**` | static assurance UI |
| `docs/submission/**` | PDF write-up, DEMO_RUNBOOK, MANUAL_QA_EVIDENCE, DEPLOYMENT checklist |
| `docs/submission/evidence/proofloop_dashboard_green.png` | **only after visually re-confirming the API-key field is cleared** |
| `docs/PROJECT_RULES.md` | canonical architecture invariants (reviewer-useful, no secrets) |
| `.env.example` | documents required env vars — **confirm placeholders only** (verified 1.6 KB, no real values) |
| `.github/workflows/**` | CI definition (documents the verify pipeline; contains no secrets) |
| **`VIDEO.mp4`** (added at packaging time) | required 5–8 min video, demo-first |
| **`PROOFLOOP_PS6_2_FINAL_WRITEUP.pdf`** | already in `docs/submission/`; ensure it's the final PDF |

## ❌ EXCLUDE (never ship)

| Path / pattern | Reason |
|---|---|
| `.git/` | VCS history; not needed; may leak branches/refs |
| `.venv/`, `venv/`, `env/` | virtual environments (none present, but exclude by rule) |
| `__pycache__/`, `*.pyc` | build artifacts |
| `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/` | tool caches |
| `build/` | build artifacts |
| `.DS_Store` | macOS junk |
| `.claude/` | Claude Code local config/session state |
| **`claude/`** | internal reviews, handovers, DECISIONS, interview prep — **Claude scratch/AI-assist artifacts**; the evaluator-facing rationale is in the PDF write-up |
| **`codex/`** (incl. `codex/.analysis/` ~10 MB) | internal Codex handovers + research renders — **AI-conversation-adjacent scratch** |
| `docs/superpowers/**` | internal specs/plans (process artifacts, not deliverables) |
| `docs/PROOFLOOP_BUILD_AND_INTERVIEW_GUIDE.md` | candidate interview prep, not an evaluator deliverable *(candidate's call; lean exclude to avoid confusion with the PDF)* |
| any `.env`, `*.env` (non-example), `*.pem`, `*.key`, `credentials`, `secrets*` | **secrets** (none found — keep it that way) |
| screenshots showing an API key / token / account id | **secret leakage** — re-check every image |
| any `PROOFLOOP_API_KEY` / ARN / account-number in a file or slide | secret leakage |

## Secret pre-flight (run before zipping)

```bash
cd "/Users/srisruthi/Aivar Project"
# 1) no real secrets in text you plan to ship (expect: only .env.example placeholders / test fixtures)
grep -rIiE "AKIA|aws_secret|api[_-]?key\s*[:=]|PROOFLOOP_API_KEY=|BEGIN (RSA|EC|OPENSSH) PRIVATE KEY" \
  src tests docs infra scripts dashboard README.md pyproject.toml .env.example .github
# 2) confirm no real account id / bedrock ARN is hard-coded (expect: none; ARNs come from SAM params)
grep -rIiE "arn:aws:bedrock|[0-9]{12}" src infra docs/submission | grep -v "BedrockModelArn\|example\|000000000000"
# 3) eyeball the screenshot — the API-key field MUST be blank
open docs/submission/evidence/proofloop_dashboard_green.png
```

If any command returns a real value, remove/redact it before packaging.

## Suggested packaging recipe (candidate runs this — not executed here)

Copy only the allowlist into a clean staging dir so excludes can't sneak in:

```bash
STAGE="/tmp/proofloop_submission"
rm -rf "$STAGE" && mkdir -p "$STAGE"
cd "/Users/srisruthi/Aivar Project"
rsync -a \
  --exclude '.git' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.mypy_cache' --exclude '.pytest_cache' --exclude '.ruff_cache' \
  --exclude 'build' --exclude '.DS_Store' --exclude '.claude' \
  --exclude 'claude' --exclude 'codex' --exclude 'docs/superpowers' \
  --exclude 'docs/PROOFLOOP_BUILD_AND_INTERVIEW_GUIDE.md' \
  src tests dashboard scripts infra docs README.md pyproject.toml .env.example .github \
  "$STAGE/"
# add the deliverables the evaluator opens first:
cp docs/submission/PROOFLOOP_PS6_2_FINAL_WRITEUP.pdf "$STAGE/"
cp /path/to/VIDEO.mp4 "$STAGE/"
# final sanity: list what's going in, then zip
find "$STAGE" -name '.DS_Store' -delete
( cd /tmp && zip -r proofloop_ps6_2_submission.zip proofloop_submission -x '*/__pycache__/*' )
```

Then **unzip the result into a fresh folder and re-run** `python -m venv … &&
pip install -e ".[dev]" && pytest -q` to prove the ZIP is self-contained before
uploading. Upload the ZIP to a link host; paste that link in the Google Form.

## Final exclusion checklist

- [ ] no `.git`, venvs, caches, `build/`, `.DS_Store`
- [ ] no `claude/`, `codex/`, `.claude/`, `docs/superpowers/`
- [ ] no `.env` (only `.env.example` placeholders)
- [ ] no API keys / ARNs / account ids in any file or image
- [ ] screenshot key field blank
- [ ] video (demo-first) + final PDF included
- [ ] ZIP re-verified from a clean extract
