# ProofLoop Track E2 Release-Blocker Repair Design

**Date:** 2026-07-18
**Status:** Approved by the product owner's Track E2 instruction

## Scope

Close only the Codex-owned portions of RUFF-01, BANDIT-01, and AUDIT-01. Do not
edit Claude-owned agent files, implement observations O1/O2, add a caller run
key, deploy, invoke Bedrock, create cloud or GitHub resources, or mutate Git.

## Considered approaches

1. **Nested typed named functions (selected).** Replace each assigned lambda in
   `build_invoice_runner` with a branch-local named function and assign that
   function to the typed `provider_factory` variable. This preserves the
   existing closure over the fake model version or Bedrock client/config and
   preserves creation of a fresh Bedrock provider for every request.
2. **`functools.partial`.** This would remove E731 but make the required named
   factory behavior less explicit and would not improve reviewability.
3. **Top-level callable factory classes.** This would be testable but would add
   new types and state for a two-line composition-root repair.

## Design

- Add focused assertions that fake and Bedrock composition expose named
  factories. Retain the existing identity assertion proving that two Bedrock
  requests receive distinct provider instances.
- Define `fake_provider_factory(request: InvoiceRunRequest) -> ModelProvider`
  and `bedrock_provider_factory(_request: InvoiceRunRequest) -> ModelProvider`
  inside the existing provider-mode branches. Assign the selected function to
  the already typed `provider_factory` variable.
- Keep `EvidenceOutcome.PASS = "PASS"` unchanged and add a line-level
  `# nosec B105` annotation whose explanation states that this is a public
  assurance enum value, not a credential.
- Create a disposable Python 3.12 environment, install the project with
  `pytest>=9.0.3,<10` plus the configured tools, and run the complete gate. Only
  after pytest 9 compatibility is demonstrated will the project dev constraint
  change to `pytest>=9.0.3,<10`.
- Re-scan Claude-owned files without editing them. Any remaining agent-layer
  Ruff or Bandit finding is reported as pending Claude ownership.
- Update release-status documentation with exact fresh evidence. Correct only
  the stale AWS-payment statement: the account is active and Lambda is
  accessible in `ap-south-1`; SAM, CI, deployment, and Bedrock remain unclaimed.

## Acceptance criteria

- Named provider factories preserve fake behavior, Bedrock configuration, and
  request-scoped Bedrock provider construction.
- `EvidenceOutcome.PASS` serializes exactly as `"PASS"`.
- Ruff, Bandit, and strict dependency audit exit zero for the combined tree, or
  any not-yet-arrived Claude-owned finding is isolated and reported precisely.
- The complete user-specified local gate is executed from the disposable
  pytest 9 environment, with unavailable tooling reported without inference.
- Documentation distinguishes code-blocker closure from deployment readiness.

