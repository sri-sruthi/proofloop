# Final Claude Data-Science Independent Review

**Final local verdict: PASS — repaired and safe to enter the private-CI gate.**

The original independent verdict was **FAIL**. Six contract failures were
reproduced before implementation and are preserved below as audit history.
The product owner then explicitly superseded the review-only restriction and
authorized test-first repairs across the Claude-owned evaluation files and the
Codex-owned packaging boundary. All six findings now have regression coverage,
and every authoritative local gate is green. Commit, private CI, and integration
remain Phase 3 actions; this local PASS is not a deployment or production-readiness
claim.

## Repair outcome

| Original blocker | Repair | Fresh evidence |
|---|---|---|
| DS-RECORD-01 | Defensive copy, immutable mapping proxies, versioned scalar allow-list, bounded PII/credential/content guards | 34 record tests pass; caller and nested mutation tests pass |
| DS-METRIC-02 | Replaced the misleading metric with `numeric_prediction_parse_availability_rate` | Missing expected numeric prediction reports 0; non-applicable record is excluded |
| DS-DECISION-03 | Incomplete/unjudgeable records always route to review | High-confidence adversarial sweep test passes |
| DS-EVIDENCE-04 | Report sufficiency derives from expected evidence, not record count | Wholly unjudgeable dataset returns `INSUFFICIENT_EVIDENCE` with no supported claim |
| DS-COST-05 | Direct/config/CLI boundaries reject negative and non-finite costs/prices | Negative, NaN, infinity, and zero cases pass |
| DS-CLI-06 | Preflighted sibling temporary files, atomic replacement, backup/rollback, safe errors | Directory-target and injected second-replace failures leave no partial output |
| PKG-BOUNDARY-01 | Bounded copy helper and built-artifact verifier exclude evaluation/caches/bytecode | Clean SAM artifacts contain none; both handlers import |

## Phase A — G2A evidence finalization

Phase A passed. The AWS Free Plan identity advice was corrected in the isolated
G2A worktree to avoid AWS Organizations/IAM Identity Center enrollment, which
would upgrade the account to the paid plan and expire free-plan credits. The
document now recommends a one-time MFA-protected root bootstrap, a named
console-only IAM user with the AWS-managed `SignInLocalDevelopmentAccess`
policy, browser-based `aws login` temporary credentials, an MFA-protected
ProofLoop deployment role, separate runtime roles, and removal of temporary
bootstrap administration. No policy or AWS resource was created.

- File committed: `codex/handovers/FINAL_G2A_READONLY_AWS_PREFLIGHT.md`
- Commit: `67eec0fa81a5065c4d5798b6e81fadf95024db94`
- Parent: `39a00cb6d954569bff9d2ff35c8e56b93f004cec`
- Remote branch: `origin/codex/track-g2a-readonly-preflight`
- Commit scope: exactly the one handoff file
- Verification: `277 passed in 1.79s`; secret/account scan had no matches;
  remote visibility was re-read as `PRIVATE` / `isPrivate=true`
- Canonical main remained `ad87c31e8a880be183d69a94add6f3103d774893`.
  `AWSCLIV2.pkg` remained untracked and unchanged, SHA-256
  `c7538dbc6b61ed70774c53e35d4bd2b530cbc40a3bc702a64aa01a9513b4db15`.

## Phase B — independent data-science audit

### Exact review boundary

- Review worktree: `.worktrees/review-claude-offline-data-science`
- Review branch: `codex/review-claude-offline-data-science`
- Exact reviewed head: `967e05c055c732789720fd5b79042123c10b23b0`
- Implementation parent: `0faad459f29c55aa2857b67d717b0ab9851d1e3d`
- Main parent: `ad87c31e8a880be183d69a94add6f3103d774893`
- Claude's original branch/worktree was not modified.
- Claude's original branch/worktree was not edited. After explicit product-owner
  authorization, repairs were made only in this isolated Codex review worktree.
  Agent/privacy/runtime behavior and the SAM template were not changed.

## Historical blocking findings

The following text records the exact pre-repair state and reproducers. Each
required repair is now fulfilled as summarized in **Repair outcome** above.

### DS-RECORD-01 — records are neither deeply immutable nor structurally content-safe

**Owner: Claude.** `src/proofloop/evaluation/records.py:37-40` freezes the
Pydantic model but `expected_fields` and `predicted_fields` remain mutable
dictionaries at lines 87-88. The guard at lines 67-77 and 98-99 scans only
field values for an email shape or a 13-digit run. It does not cover record
identifiers, tags, configuration identifiers, `run_id`, field names, or the
prohibited raw-content categories.

Reproducer results:

```text
nested_mutation_persisted=999.00
pii_like_identifier_accepted=person@example.com
raw_prompt_output_keys_accepted=[model_output, prompt, raw_invoice]
```

Required repair: make nested mappings genuinely immutable/copy-isolated and
enforce the H1 record boundary across every record field. Raw invoice text,
prompt text, model output, credentials, and PII must be unrepresentable or
rejected. Add adversarial tests for nested mutation, identifiers, tags, keys,
values, and configuration/run metadata. A regex backstop must not be described
as a DLP guarantee.

### DS-METRIC-02 — `schema_valid_rate` is numeric parseability, including vacuous success

**Owner: Claude.** `src/proofloop/evaluation/metrics.py:293-319` declares a
schema-valid rate but tests only whether predicted values whose names happen to
be in `NUMERIC_FIELD_NAMES` parse as amounts. It does not validate required
fields, unexpected fields, value types, or an extraction schema. `all()` also
returns true when no predicted numeric field exists.

Reproducer: a record whose expected fields include `total=10.00` but whose
prediction contains only `invoice_number` reports:

```text
missing_expected_numeric_schema_valid_rate=1
```

Required repair: either rename the metric and ID to an exact numeric-field
parseability measure with an explicit denominator, or implement a real,
versioned output-schema validation contract. Empty applicable-field sets must
not silently count as valid.

### DS-DECISION-03 — unjudgeable records can be auto-accepted at zero modeled error cost

**Owner: Claude.** `src/proofloop/evaluation/calibration.py:316-356` increments
`auto_accepted` solely from confidence. It increments `wrong_auto_accepts` only
when correctness is exactly `False`; `None` is therefore treated as accepted
but not wrong. This makes an unjudgeable record look free in the cost model.

Reproducer using empty expected and predicted mappings with confidence `1.0`
at threshold zero:

```text
unjudgeable_auto_accepted=1
unjudgeable_wrong_auto_accepts=0
unjudgeable_cost=0
```

Required repair: exclude unjudgeable samples with explicit counts and
`INSUFFICIENT_EVIDENCE`, or force them to review. They must never be
auto-accepted as known-good or priced as zero-error evidence.

### DS-EVIDENCE-04 — inadequate evidence receives `OK` and supported conclusions

**Owner: Claude.** `src/proofloop/evaluation/report.py:282-320` assigns two
supported claims whenever any record exists and sets status `OK` at line 313.
It does not require judgeable expected fields, applicable metrics, confidence,
or an evidence threshold.

The same one-record unjudgeable dataset produces:

```text
inadequate_report_status=OK
supported_claims=[deterministic metrics were computed, sample sizes reported]
```

Required repair: derive report sufficiency from judgeable evidence and metric
sufficiency, not tuple length. Empty or wholly unjudgeable evidence must yield
`INSUFFICIENT_EVIDENCE` and no affirmative supported conclusion.

### DS-COST-05 — negative caller costs are accepted

**Owner: Claude.** `src/proofloop/evaluation/report.py:81-88` accepts unconstrained
`Decimal` review/error costs, which are forwarded at lines 265-274.
`threshold_cost_sweep` in `calibration.py:303-372` performs no finite/nonnegative
validation.

Reproducer:

```text
negative_cost_accepted=-1
```

Required repair: reject negative and non-finite review costs, error costs, and
pricing inputs at the contract boundary; add zero, negative, infinity, and NaN
tests.

### DS-CLI-06 — multi-output failure leaves a misleading partial artifact

**Owner: Claude.** `scripts/evaluate_extraction.py:163-178` writes JSON and then
Markdown directly. Output I/O is outside the safe-error handler and there is no
preflight or atomic multi-file publication.

Reproducer:

```console
python scripts/evaluate_extraction.py dataset.json \
  --json-out partial.json --markdown-out EXISTING_DIRECTORY
```

Actual result: exit 1 with an `IsADirectoryError` traceback at line 170, while
`partial.json` remains present, valid, and says `status=OK` and
`claim_boundary=SYNTHETIC_ONLY`.

Required repair: validate both targets before publication; write temporary
files in the destination directories; publish only after all serialization and
writes succeed; clean up on error; emit a concise safe error without a raw
traceback. Add a two-target failure regression test proving no partial output.

### PKG-BOUNDARY-01 — the offline evaluation package is deployed in both Lambdas

**Owner: Codex (infrastructure packaging).** `infra/lambda/Makefile:9-12`
copies the entire `src/proofloop` tree into each function. A clean SAM build
contains all six `proofloop/evaluation/*.py` files in both artifacts.

- Exact evaluation source bytes per function: `47,092`
- Allocated size per function from `du -sk`: `60 KiB`
- Duplicate evaluation source across both functions: `94,184` bytes
- Total allocated artifact size at inspection: `7,272 KiB` per function
- Runtime reverse-import scan: no `proofloop.evaluation` import outside the
  evaluation package
- Built-handler imports: both pass
- Built-artifact secret scan: no credential/private-key pattern found

The immediate performance impact is small, and the code is not executed by the
handlers. It nevertheless expands the deployed attack surface and contradicts
`claude/DATA_SCIENCE_INTERVIEW_GUIDE.md:115-116`, which says the evaluation
layer is not deployed anywhere. Exclusion is required before AWS deployment,
not because of an observed runtime import but to preserve the approved
offline-only boundary and make reviewer-facing statements true.

Required repair in a separately authorized Codex packaging track: package an
explicit runtime allow-list or exclude `proofloop/evaluation`, then add a SAM
artifact structural test that fails if it appears in either function. Claude
should update the interview statement only if the packaging boundary is not
fixed. No infrastructure file was edited in H1.

## Checks that passed

- Versioned top-level contracts, duplicate detection, and split-leakage checks
- Runtime-to-evaluation reverse import scan (no matches)
- Evaluation import isolation and absence of AWS/Bedrock/runtime imports
- Exact/normalized match behavior under the documented normalization policy
- Decimal missing/zero-denominator accounting
- Brier target, calibration bins/ECE, and selective-risk calculations for
  judgeable inputs covered by the test suite
- Synthetic provenance blocks production performance claims
- GREEN/AMBER/RED isolation checks
- Deterministic JSON and Markdown output for identical ordered input/config
- Wheel discovery includes `proofloop.evaluation`
- Strict SAM lint/build and both built-handler imports
- Built-artifact credential/private-key scan

## Authoritative command evidence

Disposable environment:

```text
Python 3.13.7 (arm64)
pytest 9.1.1
Pydantic 2.13.4
pip 26.1.2
pip check: No broken requirements found
```

Results:

```text
python -m pytest -q
  401 passed in 3.91s

python -m pytest -q tests/evaluation
  117 tests collected; focused evaluation/package gate: 124 passed in 2.05s

python -m pytest -q tests/integration/test_lambda_packaging_isolation.py
  7 passed in 0.03s

python -m mypy src/proofloop tests
  Success: no issues found in 106 source files

python -m ruff check src tests scripts infra/scripts
  All checks passed!

python -m bandit -q -r src/proofloop scripts/evaluate_extraction.py infra/scripts
  exit 0

python -m pip_audit --strict
  No known vulnerabilities found

python -m compileall -q src tests scripts infra/scripts
  exit 0

python scripts/demo_proofloop.py
  exit 0; expected GREEN -> AMBER -> RED -> AMBER -> GREEN sequence

python scripts/demo_agent_to_compliance.py
  exit 0; expected guardrail/conflict/canary/recovery sequence

python infra/scripts/validate_template.py
  SAM package guardrails passed

node --check dashboard/app.js
  exit 0

two independent evaluate_extraction.py runs
  JSON identical; SHA-256 1fa7a08a8bf4466463717993ca006264ed8bac82c3d7d730215d6ae7a5acdc4f
  Markdown identical; SHA-256 84637feb3baea55f89b8ff4c1e1cf7131bc1958e2c2b518feead9cf4197143e9

sam validate --lint --template-file infra/template.yaml
  valid SAM template; SAM CLI 1.163.0

sam build --template-file infra/template.yaml
  Build Succeeded (Python 3.13.7; local PyPI access only)

python infra/scripts/verify_built_handlers.py <api-artifact> <api-handler> <scheduled-artifact> <scheduled-handler>
  Verified 2 built Lambda handlers.

built-artifact evaluation/cache/bytecode scans
  no matches; 7,212 KiB per function; credential/private-key scan no matches
```

One initial editable-install command failed before pip ran because zsh treated
an unquoted `.[dev]` as a glob; quoting it succeeded. The first clean SAM build
attempt could not reach PyPI inside the network sandbox; rerunning the same
local build with approved PyPI access succeeded. Neither was a project defect,
and neither contacted AWS.

Independent semantic command:

```text
python /private/tmp/proofloop-h1-repro/semantic_repro.py
```

It produced all DS-RECORD-01 through DS-COST-05 values quoted above. The CLI
command quoted under DS-CLI-06 independently reproduced the partial-file
failure.

## Required handoff fields

**Task:** Finalize G2A evidence and independently audit Claude's offline
data-science branch.

**Customer outcome:** G2A identity guidance is safely finalized. The
data-science failures were stopped before integration, reproduced, repaired
under explicit authorization, and verified without weakening runtime safety.

**Files read:** The G2A/G1.6 handoffs, Claude DS handoff and implementation
plan; every file under `src/proofloop/evaluation/` and `tests/evaluation/`;
the CLI, DS documentation/interview guide, runtime evaluator, agent workflow,
composition/handlers/provider, `pyproject.toml`, CI, Makefiles, SAM template,
SAM validator/handler verifier, and project ownership rules.

**Files changed:** Evaluation records/metrics/calibration/report, the offline
CLI, focused evaluation tests, Lambda copy/verifier/Makefile packaging,
packaging tests, DS documentation/interview/handoff, this review, and the
approved repair plan. Phase A changed only its separately committed G2A
handoff.

**Review findings resolved:** DS-RECORD-01, DS-METRIC-02, DS-DECISION-03,
DS-EVIDENCE-04, DS-COST-05, DS-CLI-06, and PKG-BOUNDARY-01.

**Contract changes:** Record mappings are deeply immutable and field names are
allow-listed for schema 1.0.0. The misleading schema-validity metric was
replaced by `numeric_prediction_parse_availability_rate`. Incomplete evidence
routes to review; wholly unjudgeable reports are insufficient. Costs/prices
must be finite and non-negative. CLI paired outputs are transactional.

**Migration instructions for Claude:** Use only `INVOICE_SCALAR_FIELDS_V1`
keys in evaluation fixtures. Use the new numeric parse/availability metric
name and do not describe it as schema validation. Preserve immutable mappings,
review routing, and transactional publishing in future DS changes.

**Tests added:** 52 tests beyond the original 349-test branch result, including
deep mutation, bounded content, metric semantics, evidence sufficiency,
invalid costs, CLI rollback, and Lambda package isolation. Full result: 401.
Independent pre-repair reproducers remain only under `/private/tmp` with
synthetic data.

**Commands executed / actual results:** Recorded above with exact results.

**Production risks checked:** PII/raw-content entry, immutability, metric
semantics, inadequate evidence, decision/cost safety, deterministic output,
atomic failure, runtime isolation, dependency security, secret patterns, SAM
validity, handler importability, and Lambda package contents.

**Known limitations:** No real customer data, AWS call, model invocation,
deployment, change set, or production performance measurement occurred.

**Human decisions still required:** None for the local repair. Phase 3 private
CI/integration is authorized by the master track and must still pass. AWS work
remains gated on the named non-root profile and later literal `DEPLOY` response.

**Five files the human should inspect:**

1. `src/proofloop/evaluation/records.py`
2. `src/proofloop/evaluation/metrics.py`
3. `src/proofloop/evaluation/calibration.py`
4. `scripts/evaluate_extraction.py`
5. `infra/lambda/Makefile`

**Concepts the human must understand:** Pydantic frozen models are not deep
immutability; parseability is not schema validity; unjudgeable examples cannot
prove correctness; multi-file outputs need atomic publication; import
isolation is distinct from deployment-package isolation.

**Recommended Claude review focus:** Confirm the allow-list covers only the
approved scalar extraction contract; review guard false-positive/false-negative
trade-offs; confirm no DS output can affect runtime verdict/HITL/payment; and
review the transaction rollback and package-exclusion tests.

**Documentation updated:** DS evaluation guide, interview guide, original DS
handoff, this independent review, and the repair plan.

**Git diff summary:** The isolated review worktree contains only the approved
DS, test, packaging, and documentation repairs. Phase 3 commit/push/private CI
has not yet occurred at this document checkpoint.

## Safety statement

No AWS API was called. No Bedrock model was invoked. No resource, deployment,
change set, schedule change, branch merge, or repository visibility change
occurred.
