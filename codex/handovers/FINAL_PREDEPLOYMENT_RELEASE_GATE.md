# ProofLoop Final Predeployment Release Gate

**Date:** 2026-07-18  
**Track:** E2 - authorized release-blocker repairs  
**Decision:** **LOCAL CODE GATE PASS / BLOCKED FOR DEPLOYMENT VERIFICATION**  
**AWS status:** product owner states account activation is complete and Lambda is
accessible in `ap-south-1`; Track E2 made no AWS call  
**Deployment / real Bedrock:** not attempted  
**Git/GitHub:** no baseline, commit, push, branch, remote or repository action

## Task

Close only the authorized Codex-owned portions of RUFF-01, BANDIT-01 and
AUDIT-01, incorporate concurrently arriving Claude-owned blocker repairs
without editing them, run the complete clean local gate, and refresh the release
evidence. Optional audit observations O1/O2 and a caller run key were explicitly
excluded.

## Customer outcome

The local release candidate no longer fails its configured static-analysis,
security or dependency gates. Provider construction remains request scoped,
both public PASS serialization contracts remain stable, and the project now
declares a non-vulnerable pytest 9 development range. This does not establish
target-runtime, deployment, real-model or production evidence.

## Gate matrix

| Gate | Result | Fresh Track E2 evidence |
|---|---|---|
| Pytest 9 compatibility | PASS | pytest 9.1.1; 266 passed |
| Static types | PASS | no issues in 88 source files |
| Ruff | PASS | `python -m ruff check src tests` -> all checks passed |
| Bandit | PASS | `python -m bandit -q -r src/proofloop` -> exit 0 |
| Strict dependency audit | PASS | no known vulnerabilities after disposable pip upgraded to 26.1.2 |
| Dependency integrity | PASS | no broken requirements |
| Compile/demos/template/dashboard | PASS | all commands exited 0 |
| Import isolation | PASS | no agent imports in domain/application; no AWS SDK imports in domain/application/API |
| Manual API/dashboard QA | CARRIED FORWARD | Track D2 14/14 evidence remains applicable; behavior-changing integration tests pass |
| Python 3.13 | NOT RUN | runtime unavailable locally |
| SAM validate/build/artifact imports | NOT RUN | SAM CLI unavailable |
| GitHub CI | NOT RUN | repository has no baseline/private remote |
| AWS deployment/real Bedrock | NOT RUN | prohibited in Track E2 |

## Closed blockers

### RUFF-01 - closed

- Codex replaced the two assigned lambdas in
  `src/proofloop/infrastructure/composition.py` with typed nested
  `fake_provider_factory` and `bedrock_provider_factory` functions.
- The functions preserve the same captured model version, Bedrock client and
  provider configuration. Existing tests still prove two requests receive
  distinct Bedrock provider instances.
- Focused assertions failed on the old `<lambda>` names and passed after the
  repair.
- Claude concurrently removed the unused `ExtractedInvoice` import from
  `src/proofloop/agents/workflow.py`. Codex did not edit that file.
- Full Ruff exits zero.

### BANDIT-01 - closed

- `EvidenceOutcome.PASS = "PASS"` remains unchanged.
- Codex added an adjacent explanation plus line-level `# nosec B105` only to
  that domain enum member.
- Claude independently applied the same narrow pattern to its
  `ControlOutcome.PASS` member and added its agent-owned serialization test.
- No global B105 disable or Bandit configuration change was made. Full Bandit
  exits zero without warnings.

### AUDIT-01 - closed

- Before changing policy, a disposable Python 3.12.7 environment installed
  pytest 9.1.1 and ran the complete local gate successfully.
- `pyproject.toml` now declares `pytest>=9.0.3,<10`; reinstalling `.[dev]`
  resolved to pytest 9.1.1.
- The first strict audit found only the disposable environment's bootstrap
  `pip 24.2`. Upgrading that disposable pip to 26.1.2 removed those findings;
  strict audit then reported no known vulnerabilities.

## Remaining blockers

1. **TARGET-01:** Python 3.13 is unavailable; CI/runtime parity is unverified.
2. **SAM-01:** SAM CLI is unavailable; `sam validate`, container build and
   built-handler verification are unexecuted.
3. **REPO-01:** no Git baseline/private remote exists; diff provenance and
   protected CI are unavailable.
4. **CI-01:** GitHub Actions has not run on Python 3.12/3.13.
5. **AWS-01:** account activation and Mumbai Lambda availability are
   product-owner statements only. Identity, region/model access, IAM/change set,
   deployment, alarms, DLQs, DynamoDB and rollback remain unverified.
6. **MODEL-01:** no real Bedrock request, latency, accuracy or cost evidence.

## Files read

- `docs/PROJECT_RULES.md`
- prior `codex/handovers/FINAL_PREDEPLOYMENT_RELEASE_GATE.md`
- `claude/reviews/FINAL_RELEASE_CANDIDATE_AUDIT.md`
- `src/proofloop/infrastructure/composition.py`
- `src/proofloop/domain/models.py`
- `pyproject.toml`
- `.github/workflows/ci.yml`
- relevant domain, composition and privacy tests

## Files changed by Codex

- `src/proofloop/infrastructure/composition.py`
- `src/proofloop/domain/models.py`
- `pyproject.toml`
- `tests/integration/test_agent_composition.py`
- `tests/domain/test_contracts.py`
- Track E2 design/plan and release-status documentation under `docs/**` and
  `codex/**`

Claude-owned agent files were not edited by Codex.

## Review findings resolved

RUFF-01, BANDIT-01 and AUDIT-01 are closed. Claude observations O1/O2 remain
intentionally unimplemented because they are non-blocking and out of Track E2
scope.

## Contract changes

- Development dependency policy changed from pytest `<9` to
  `pytest>=9.0.3,<10` after compatibility proof.
- No API, evidence, assurance, provider or serialized PASS contract changed.

## Migration instructions for Claude

None. Claude's concurrent agent-owned fixes are present and the combined gate
is clean. Do not rework the Codex-owned named factories or domain B105 annotation
without a new owner handoff.

## Tests added

- `test_fake_mode_exposes_a_named_request_factory`
- Bedrock composition now asserts the selected factory's stable name while
  retaining the existing request-scope identity assertions.
- `test_evidence_outcome_pass_serialized_contract_is_stable`

## Commands executed and actual results

```text
python -m pytest -q
  -> 266 passed in 1.98s on the final consolidated rerun
python -m mypy src/proofloop tests
  -> Success: no issues found in 88 source files
python -m ruff check src tests
  -> All checks passed!
python -m bandit -q -r src/proofloop
  -> exit 0, no findings
python -m pip_audit --strict --progress-spinner off
  -> No known vulnerabilities found
python -m pip check
  -> No broken requirements found
python -m compileall -q src tests scripts infra/scripts
  -> exit 0
python scripts/demo_proofloop.py
  -> GREEN -> AMBER -> RED -> AMBER -> GREEN; resolved incident
python scripts/demo_agent_to_compliance.py
  -> GREEN -> AMBER -> GREEN -> RED -> AMBER -> GREEN; bounded failure/recovery scenes
python infra/scripts/validate_template.py
  -> SAM package guardrails passed
node --check dashboard/app.js
  -> exit 0
import-isolation scans
  -> no prohibited matches
```

## Production risks checked

Request-scoped provider creation, PASS serialization, full deterministic suite,
privacy/injection regressions, static/security/dependency gates, demo recovery,
template structure, JavaScript syntax and cloud/agent import isolation.

## Known limitations

Production DLP, real ERP/AP, actual MCP runtime, caller run key, production
identity/authz, deployed persistence/concurrency/alarms/DLQs, target Python 3.13,
SAM artifacts, CI, real Bedrock and measured accuracy/latency/cost remain absent.

## Human decisions still required

Private Git authorization and policy; Python 3.13/SAM execution environment;
AWS account/role confirmation; exact region/stack/model/ARN; browser origin;
tenant/boundary identifiers; API-key delivery; budget/alarms; log/DLQ owners;
reviewed change set; smoke and rollback approval.

## Next consolidated release-gate prompt

Copy this prompt without expanding its authority:

> ProofLoop Track E2 local blockers RUFF-01, BANDIT-01 and AUDIT-01 are closed.
> Resume from `codex/handovers/FINAL_PREDEPLOYMENT_RELEASE_GATE.md` and read
> `docs/submission/DEPLOYMENT_AND_ROLLBACK_CHECKLIST.md` plus Claude's latest
> audit end to end. Do not deploy or invoke Bedrock. In a clean Python 3.13
> environment, install the declared `.[dev]` dependencies and security tools;
> reproduce the complete local gate; run `sam validate --template-file
> infra/template.yaml`, `sam build -t infra/template.yaml --use-container`, and
> built-handler verification. If Git remains unauthorized, do not create a
> baseline or remote. Then stop and present the exact results, proposed
> CloudFormation change set, account/role, region, stack name, Bedrock model and
> least-privilege ARN, browser origin, tenant/boundary identifiers, API-key
> delivery plan, budget/alarms, log/DLQ owners, synthetic smoke plan and rollback
> plan for separate explicit approval. Do not create resources, create GitHub,
> commit, push, deploy or make a real-model request without that approval.

## Five files the human should inspect

1. `codex/handovers/FINAL_PREDEPLOYMENT_RELEASE_GATE.md`
2. `src/proofloop/infrastructure/composition.py`
3. `src/proofloop/domain/models.py`
4. `pyproject.toml`
5. `docs/submission/MANUAL_QA_EVIDENCE.md`

## Concepts the human must understand

Local code-gate success is not deployment readiness; nested named functions
preserve closure state while creating providers per request; `# nosec B105` is
scoped to public enum serialization; and strict audit includes the environment's
bootstrap tooling unless explicitly upgraded.

## Recommended Claude review focus

Confirm Codex did not alter agent behavior or ownership, the provider remains
request scoped, and no optional audit observation was smuggled into Track E2.

## Documentation updated

The release gate, manual QA evidence, demo runbook, deployment checklist, final
write-up source and PDF status are updated for Track E2.

## Git diff summary

Git cannot produce a baseline diff because branch `main` has no commits and the
tree is untracked. No Git mutation was performed.
