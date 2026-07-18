# Final G2A read-only AWS identity and Bedrock preflight

**Date:** 2026-07-18  
**Track:** G2A — read-only AWS identity and Bedrock discovery  
**Branch:** `codex/track-g2a-readonly-preflight`  
**Worktree:** `/Users/srisruthi/Aivar Project/.worktrees/track-g2a-readonly-preflight`  
**Branch base before the H1 evidence commit:** `39a00cb6d954569bff9d2ff35c8e56b93f004cec`  
**Canonical main observed during the track:** `ad87c31e8a880be183d69a94add6f3103d774893`, a descendant of the G1.6 base  
**Verdict:** **READ-ONLY DISCOVERY COMPLETE / G2B NOT READY — ROOT CALLER MUST BE REPLACED**  
**Production readiness:** not claimed

## Executive result

The configured profile resolves to `ap-south-1`, and the account currently
authorizes several Bedrock text models from that region. The caller is,
however, the AWS account **root user**. In accordance with the product-owner
stop condition, no change-set work may follow from this session. Root was used
only for the authorized read-only discovery; it must not be the deployment or
CloudFormation operator.

For the current ProofLoop template, the recommended direct regional model is:

- primary ID: `mistral.ministral-3-3b-instruct`
- primary invocation ARN:
  `arn:aws:bedrock:ap-south-1::foundation-model/mistral.ministral-3-3b-instruct`
- fallback ID: `google.gemma-3-4b-it`
- fallback invocation ARN:
  `arn:aws:bedrock:ap-south-1::foundation-model/google.gemma-3-4b-it`

Both paths were reported by this account as agreement available, authorization
authorized, entitlement available, and region available. Both are active,
direct `ON_DEMAND` models in Mumbai and support the Converse API. The direct
foundation-model ARN fits the template's deliberately narrow single-resource
`bedrock:InvokeModel` policy.

An APAC Amazon Nova inference profile is not recommended for the current
template. AWS requires permission for the inference-profile ARN and every
foundation-model ARN to which cross-region inference can route. The current
template accepts exactly one `BedrockModelArn`; using that profile would need a
separately approved, test-first IAM/template change.

No AWS resource, CloudFormation change set, deployment, model invocation,
schedule activation, IAM identity, role, policy, access key, budget, alarm, or
subscription was created, modified, tagged, or deleted.

## Task

Perform the separately authorized read-only G2A identity, region, Bedrock
catalog, availability, compatibility, ARN, and pricing preflight using profile
`srisruthi-dev` in `ap-south-1`. Stop before G2B if the caller is root and
produce a least-privilege bootstrap plan without implementing it.

## Customer outcome

The product owner now has an account-verified, region-specific model choice and
an exact least-privilege runtime ARN without incurring model charges or
creating infrastructure. The root-caller finding prevents a high-impact
deployment from being attributed to an unsafe everyday identity. The recovery
path is explicit: bootstrap a temporary-credential human identity and bounded
CloudFormation roles in a separately authorized track, prove the caller is no
longer root, then reconsider G2B.

The account is on the AWS Free Plan with credits. Do **not** enable an IAM
Identity Center organization instance for this submission: AWS states that
creating or joining an AWS Organization automatically upgrades a Free Plan
account to the Paid Plan and immediately expires its Free Tier credits. The
free-plan-compatible controlled-development path is a narrowly scoped IAM
console user with MFA and no access keys, browser-based `aws login`, and a
separate MFA-protected deployment role.

## Preconditions and ownership boundaries

- The isolated branch was created from integrated G1.6 head
  `39a00cb6d954569bff9d2ff35c8e56b93f004cec`.
- Canonical `main` later advanced to `ad87c31e8a880be183d69a94add6f3103d774893`;
  the G1.6 commit remains its ancestor.
- The isolated worktree was clean before this handoff was added.
- The remote is `sri-sruthi/proofloop-aivar-private`, with GitHub reporting
  `isPrivate=true` and `visibility=PRIVATE`.
- The canonical worktree was not used for G2A and its unrelated user/Claude
  state was not staged, discarded, overwritten, committed, or pushed.
- No agent, prompt, privacy, provider, domain, or infrastructure implementation
  file was edited. This Codex-owned handoff is the only G2A file change.

## Safely redacted caller and region findings

| Check | Safely recorded result |
|---|---|
| CLI profile | `srisruthi-dev` |
| Configured/target region | `ap-south-1` |
| AWS CLI | `aws-cli/2.36.2` |
| Caller classification | AWS account root user |
| Account | redacted as `********9204` |
| Caller ARN | root ARN confirmed; account and session details withheld |
| Credential material | not printed or recorded in this file |
| Root consequence | discovery may be documented, but G2B must stop pending a non-root identity |

The initial STS request found an expired cached login. Authentication was
refreshed with `aws login --profile srisruthi-dev` while stdout/stderr were
suppressed. No login URL, token, credential, API key, or session material is
included here.

## Commands executed

All AWS result-producing commands were read-only. Outputs were projected
through JMESPath or `jq` so sensitive identity fields were not retained in the
handoff.

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse main
git merge-base --is-ancestor 39a00cb6d954569bff9d2ff35c8e56b93f004cec main
gh repo view sri-sruthi/proofloop-aivar-private --json nameWithOwner,isPrivate,visibility
pytest -q
python -m pytest -q

aws --version
aws configure get region --profile srisruthi-dev
aws login --profile srisruthi-dev                     # output suppressed
aws sts get-caller-identity --profile srisruthi-dev   # result filtered/redacted

aws bedrock list-foundation-models \
  --profile srisruthi-dev --region ap-south-1 \
  --by-output-modality TEXT
aws bedrock list-inference-profiles \
  --profile srisruthi-dev --region ap-south-1 \
  --type-equals SYSTEM_DEFINED
aws bedrock get-foundation-model-availability \
  --profile srisruthi-dev --region ap-south-1 \
  --model-id <screened-model-id>
aws bedrock get-foundation-model \
  --profile srisruthi-dev --region ap-south-1 \
  --model-identifier <shortlisted-model-id>
```

The availability command was repeated for these screened IDs:

```text
google.gemma-3-4b-it
mistral.ministral-3-3b-instruct
mistral.mistral-7b-instruct-v0:2
amazon.nova-micro-v1:0
amazon.nova-lite-v1:0
openai.gpt-oss-20b-1:0
nvidia.nemotron-nano-9b-v2
```

One parallel local attempt could not reach AWS because of the execution
sandbox's network boundary. The same read-only availability checks were rerun
with the approved network permission and succeeded; this was a local-tooling
retry, not an AWS service failure.

During final verification, the unqualified `/opt/anaconda3/bin/pytest -q`
console entry point failed collection because it did not put the repository
root on `sys.path`; `pyproject.toml` intentionally adds `src`, while one guard
test imports the tracked top-level `scripts` namespace. A direct import from
the same interpreter succeeded, and the environment-correct invocation
`python -m pytest -q` passed all tests. No code or configuration was changed to
mask this runner-path difference.

## Actual results

- Initial isolated baseline: `277 passed in 2.93s`.
- Final environment-correct verification: `python -m pytest -q` returned
  `277 passed in 3.85s`.
- Diagnostic runner result: unqualified Anaconda `pytest -q` returned one
  collection error (`ModuleNotFoundError: scripts`); direct import and
  `python -m pytest` prove this is the console-entry-path difference described
  above, not a source or test regression.
- Branch base: exact final G1.6 head `39a00cb6d954569bff9d2ff35c8e56b93f004cec`.
- Private-remote evidence: `isPrivate=true`, `visibility=PRIVATE`.
- Configured and queried region: `ap-south-1`.
- Caller: root; full identity output is deliberately not reproduced.
- Every screened model above returned:
  - agreement availability `AVAILABLE`;
  - authorization `AUTHORIZED`;
  - entitlement `AVAILABLE`; and
  - regional availability `AVAILABLE`.
- No `bedrock-runtime` endpoint was contacted and no Converse request was made.

## Model comparison

### Viable current-template finalists

| Attribute | Primary | Fallback |
|---|---|---|
| Provider | Mistral AI | Google |
| Exact ID | `mistral.ministral-3-3b-instruct` | `google.gemma-3-4b-it` |
| Exact invocation ARN | `arn:aws:bedrock:ap-south-1::foundation-model/mistral.ministral-3-3b-instruct` | `arn:aws:bedrock:ap-south-1::foundation-model/google.gemma-3-4b-it` |
| Account access | agreement/entitlement available; authorized | agreement/entitlement available; authorized |
| Lifecycle | `ACTIVE` | `ACTIVE` |
| Invocation mode | direct regional `ON_DEMAND` | direct regional `ON_DEMAND` |
| Mumbai support | yes, no cross-region profile required | yes, no cross-region profile required |
| Converse | supported | supported |
| Native structured output | supported by the model/API | not listed for this model; retain prompt plus strict local validation |
| Current Mumbai price | $0.12/M input tokens; $0.12/M output tokens | $0.05/M input tokens; $0.09/M output tokens |
| Access prerequisite | current account reports authorized; runtime role needs `bedrock:InvokeModel` on the exact ARN | same |
| Invoice-extraction fit | small model, 128K context, direct regional access, native schema path available for a future provider change | small and cheaper; good bounded fallback when local schema validation remains authoritative |

Pricing is from the current [Amazon Bedrock pricing page](https://aws.amazon.com/bedrock/pricing/).
Model behavior and regional/API support are from the official
[Ministral 3B model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-mistral-ai-ministral-3b.html)
and [Gemma 3 4B model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-google-gemma-3-4b-it.html).

Illustrative—not guaranteed—cost for one call with 2,000 input and 2,000 output
tokens is approximately $0.00048 for Ministral and $0.00028 for Gemma. At the
current maximum of two calls that illustration becomes $0.00096 and $0.00056.
The application caps output at 2,000 tokens and calls at two by default; actual
input size and billed tokens still vary, so this is not a total-spend guarantee.

### Other account-authorized paths screened

| Path | Observed access/lifecycle | Why it is not the G2A recommendation |
|---|---|---|
| `amazon.nova-micro-v1:0` through `apac.amazon.nova-micro-v1:0` | account authorized; foundation model active; APAC profile active | profile-only catalog path; native structured output is not supported; cross-region IAM needs the profile and all routed foundation-model ARNs, which the current single-ARN template cannot express |
| `amazon.nova-lite-v1:0` through `apac.amazon.nova-lite-v1:0` | account authorized; foundation model and profile active | same IAM/template mismatch; larger than needed for the initial bounded extractor |
| `openai.gpt-oss-20b-1:0` | account authorized; active direct on-demand model in Mumbai; Converse and structured output supported | larger model; the current public pricing table did not provide a sufficiently clear Mumbai price for this review, so no cost claim or finalist recommendation is made |
| `mistral.mistral-7b-instruct-v0:2` | account authorized and region available | older/larger alternative; the newer 3B finalist has direct access, verified current pricing, long context, and native schema support |
| `nvidia.nemotron-nano-9b-v2` | account authorized; active direct on-demand model | no demonstrated advantage over the smaller, priced finalists for this bounded extraction task |

The APAC Nova Micro profile ARN has the form
`arn:aws:bedrock:ap-south-1:<ACCOUNT_ID>:inference-profile/apac.amazon.nova-micro-v1:0`.
It is intentionally not proposed as the template's lone invocation ARN. AWS's
[cross-region inference documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html)
and [inference-profile IAM prerequisites](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-prereq.html)
require authorization for both the profile and routed models.

## Structured-output compatibility caveat

The current `BedrockConverseProvider` sends `modelId`, `system`, `messages`, and
`inferenceConfig.maxTokens`. It does not send Converse
`outputConfig.textFormat`. Therefore Ministral's native structured-output
capability is available to the account but is **not currently enabled by
ProofLoop**. Today the trusted extraction prompt and strict Pydantic validation
remain the safety boundary.

Enabling native structured output would be a Claude-owned provider/agent
change, not part of G2A and not required to select the direct model. It must be
separately authorized and regression-tested. See AWS's
[structured outputs documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html)
and [Converse API guidance](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html).

## Least-privilege identity-bootstrap plan

This plan is documentation only and was not executed.

### Free Plan constraint

Do not create an AWS Organization or enable an IAM Identity Center
organization instance. AWS's current Free Tier FAQ states that creating or
joining an Organization automatically upgrades the account to the Paid Plan,
immediately expires Free Tier credits, and makes the account ineligible to earn
more credits. That cost/account-plan mutation is outside this submission's
authorization and is unnecessary for a single controlled-development account.

### Four identities must remain separate

| Identity | Purpose and boundary |
|---|---|
| Human login identity | A named IAM user with console access, MFA, and **no access keys**. Its durable permissions are limited to browser-based local sign-in and assumption of the exact deployment role. Its console password is a controlled Free Plan exception to AWS's general federation preference, not production identity architecture. |
| Deployment/operator role | A dedicated ProofLoop role assumed by the human through STS with MFA. It receives temporary credentials and only the CloudFormation preview/operator permissions later derived and approved for G2B. It is not a Lambda execution role. |
| CloudFormation service role | A separately scoped role trusted only by `cloudformation.amazonaws.com`, if the reviewed deployment design adopts one. The operator may pass only this exact role; its permissions are derived backward from `infra/template.yaml`. It is never assumed directly by the human. |
| Lambda runtime roles | SAM/CloudFormation-managed workload roles. The API role retains the exact direct-model `bedrock:InvokeModel` resource and required table/log actions; the scheduled role has no Bedrock permission. Humans and CloudFormation do not reuse these roles. |

### Separately authorized bootstrap sequence

1. Use root once, interactively, with MFA for the bootstrap only. Verify root
   has no access keys, protect recovery channels, and never configure root
   credentials in the CLI.
2. Create one named IAM user with console access, a strong password, and MFA.
   Do not create an access key for it.
3. Grant the user AWS-managed
   `arn:aws:iam::aws:policy/SignInLocalDevelopmentAccess`, whose current local
   sign-in actions are `signin:AuthorizeOAuth2Access` and
   `signin:CreateOAuth2Token`. Scope same-device authentication to the exact
   account/region `oauth2/public-client/localhost` resource if a reviewed
   customer-managed equivalent is chosen later. Do not invent that policy in
   H1.
4. Use `aws login --profile <human-login-profile>` in the browser. AWS CLI
   2.32.0+ exchanges the console session for cached temporary credentials and
   refreshes them only within the permitted session duration; no long-lived
   access key belongs in `~/.aws/credentials`.
5. Under a separately reviewed bootstrap permission, create a dedicated
   ProofLoop deployment/operator role whose trust and assumption path require
   the named user and MFA. The user's final non-sign-in permission should be
   only `sts:AssumeRole` on that exact role. The final policy/trust JSON must be
   designed and approved in the bootstrap track, not inferred here.
6. If G2B adopts a CloudFormation service role, create a distinct role trusted
   only by CloudFormation. Derive its actions/resources from the reviewed
   template, and constrain the operator's `iam:PassRole` and
   `cloudformation:RoleARN` to that exact role. Do not grant the human the
   service role's resource-creation permissions directly.
7. Configure a deployment profile with the exact `role_arn`, the browser-login
   profile as `source_profile`, and MFA enforcement as supported by the final
   trust/profile design. Before G2B, use a safely filtered
   `sts get-caller-identity` result to prove an
   `arn:aws:sts::<redacted>:assumed-role/<approved-role>/<session>` caller in
   `ap-south-1`; a root or direct IAM-user caller fails the gate.
8. Immediately remove all temporary bootstrap-administration permissions from
   the IAM user after the roles are created and independently reviewed. Retain
   only local-login, exact-role-assumption, console MFA/password-management, and
   any separately justified read-only account self-service. Sign root out and
   reserve it for root-only recovery tasks.

The G2A discovery-only permission set remains useful for policy design:
`sts:GetCallerIdentity`, `bedrock:ListFoundationModels`,
`bedrock:GetFoundationModel`, `bedrock:GetFoundationModelAvailability`,
`bedrock:ListInferenceProfiles`, and `bedrock:GetInferenceProfile` (plus
Bedrock Service Quotas read-only only if later required). It is a proposed
least-privilege inventory, not a policy created or authorized in this track.

This follows AWS's [Free Tier account-plan FAQ](https://aws.amazon.com/free/free-tier-faqs/),
[root-user best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html),
[IAM-user guidance](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users.html),
[local-development login guidance](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html),
[`SignInLocalDevelopmentAccess` policy reference](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/SignInLocalDevelopmentAccess.html),
[CLI role guidance](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-role.html),
[MFA-protected API guidance](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_configure-api-require.html),
and [CloudFormation service-role guidance](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-servicerole.html).

## Review findings resolved

- Confirmed the actual caller, region, account model availability, lifecycle,
  invocation mode, and inference-profile inventory rather than selecting from
  memory.
- Identified exact primary/fallback model IDs and least-privilege invocation
  ARNs that fit the existing IAM contract.
- Distinguished latent model-native structured output from the provider's
  currently implemented request shape.
- Identified root use as a hard G2B stop and supplied a non-executed recovery
  plan.
- Replaced the unsuitable IAM Identity Center organization recommendation with
  a Free Plan-compatible, no-access-key IAM console-login plus MFA-protected
  role path; no Organization, account-plan change, or final IAM policy is
  proposed.
- Identified why a cross-region profile is not interchangeable with the
  template's current single-ARN policy.

## Contract changes

None. No application, provider, domain, infrastructure, API, serialized, IAM,
or deployment contract changed.

## Migration instructions for Claude

None. Claude-owned provider/agent files were not edited. If the product owner
later authorizes native Converse structured outputs, Claude should assess
adding `outputConfig.textFormat` while preserving trusted/untrusted message
separation, strict local validation, token/call caps, and existing provider
error contracts. That is not implied authorization to make the change.

## Tests added

None; G2A is read-only discovery and documentation.

## Production risks checked

- root-user deployment risk: found; blocks G2B;
- Free Plan credit/account-plan risk: IAM Identity Center organization setup is
  explicitly prohibited because the underlying Organization would upgrade the
  account and immediately expire Free Tier credits;
- region mismatch: not found for the two direct finalists;
- marketplace/agreement surprise: no new agreement or subscription was
  requested; account reports finalists authorized and available;
- cross-region data/IAM expansion: avoided by recommending direct regional
  inference;
- hidden model charge: no invocation occurred; current public prices and an
  explicitly illustrative cost were recorded;
- overbroad runtime IAM: avoided by using the exact foundation-model ARN;
- unsupported structured-output claim: avoided; current provider limitation is
  explicit;
- credential disclosure: the handoff contains no credential, token, login URL,
  API key, or complete identity response;
- public disclosure: remote privacy was reverified; H1 authorizes publication
  of only this handoff to that private branch, never a public destination.

## Known limitations

- No real-model quality, latency, quota, token accounting, or structured-output
  behavior was tested because Bedrock invocation was forbidden.
- Account availability does not prove runtime-role permission, service quota,
  or successful inference.
- Prices can change and must be rechecked before deployment approval.
- The exact deployment operator and CloudFormation execution policy have not
  been created or verified.
- The bootstrap track must design and review the exact IAM user, trust,
  `sts:AssumeRole`, MFA, CloudFormation, `iam:PassRole`, and removal policies;
  H1 deliberately does not invent policy JSON.
- SAM CLI 1.163.0 still pins Click 8.1.8, which the current strict audit flags
  as `PYSEC-2026-2132`; select a fixed/audited SAM path or explicitly accept the
  isolated tooling risk before change-set creation.
- G2A does not resolve stack name, secrets, owner, budget, smoke, retention, or
  rollback decisions listed below.

## Human decisions still required

Before G2B can create a non-executed change set, the product owner must:

1. separately authorize and complete the Free Plan-compatible least-privilege
   identity bootstrap without creating an Organization or enabling an IAM
   Identity Center organization instance;
2. approve `mistral.ministral-3-3b-instruct` and its exact ARN, or explicitly
   choose the Gemma fallback;
3. approve the stack name and reaffirm `ap-south-1`;
4. choose a fixed/audited SAM path or explicitly accept the isolated Click
   advisory for a controlled preview;
5. approve a budget amount, thresholds, and recipients;
6. name the CloudWatch/alarm, both DLQ, replay, rollback, and retained-table
   cleanup owners;
7. record tenant, environment, assurance-boundary, synthetic-smoke, retention,
   and rollback-evidence values;
8. supply the API key and alarm email only through the approved secret-bearing
   deployment process—never Git or this handoff.

## Exact G2B recommendation

**G2B is not ready.** First run a separately authorized Free Plan-compatible
identity-bootstrap track: root with MFA for the one-time bootstrap, a named
console IAM user with no access keys, browser-based `aws login`, an
MFA-protected ProofLoop operator role, and—if adopted—a distinct
CloudFormation service role. Remove bootstrap administration, then repeat the
minimal STS/region/model read-only proof under the assumed-role profile. G2B
may be requested only if the caller is the exact approved non-root role, the
direct model/ARN and remaining human inputs are approved, and the SAM tooling
advisory is resolved or explicitly accepted.

When those gates are met, G2B should authorize only one non-executed
CloudFormation change set in `ap-south-1`, using:

```text
BedrockModelId=mistral.ministral-3-3b-instruct
BedrockModelArn=arn:aws:bedrock:ap-south-1::foundation-model/mistral.ministral-3-3b-instruct
BedrockRegion=ap-south-1
AllowedOrigin=http://localhost:8000
EnableReconciliationSchedule=false
```

The product owner must supply the remaining secret-bearing and operational
parameters at that time. G2B must use `--no-execute-changeset` (or equivalent),
inspect the exact diff/IAM/artifacts/costs, and stop without execution,
deployment, Bedrock invocation, or schedule activation.

## Five files the human should inspect

1. `codex/handovers/FINAL_G2A_READONLY_AWS_PREFLIGHT.md`
2. `infra/template.yaml`
3. `src/proofloop/agents/providers/bedrock.py`
4. `codex/handovers/FINAL_G1_6_INFRASTRUCTURE_HARDENING.md`
5. `docs/submission/DEPLOYMENT_AND_ROLLBACK_CHECKLIST.md`

## Concepts the human must understand

- root and console-login credentials versus short-lived assumed-role
  credentials, and why this Free Plan submission must not create an AWS
  Organization for IAM Identity Center;
- human login, deployment/operator, CloudFormation service, and Lambda runtime
  roles are four separate trust and permission boundaries;
- a direct regional foundation-model ARN versus an account-scoped cross-region
  inference-profile ARN;
- Converse API compatibility versus ProofLoop actually enabling native
  `outputConfig.textFormat`;
- model availability versus a successful billed runtime invocation;
- a non-executed change set versus CloudFormation execution/deployment;
- output/call caps versus total cost, which also depends on input tokens and
  retries.

## Recommended Claude review focus

Confirm only the provider-boundary analysis: the current Converse request does
not enable native structured output, and any future change remains Claude-owned
and must preserve prompt isolation and deterministic validation. Do not change
agent/privacy behavior as part of G2A.

## Files read

- `codex/handovers/FINAL_G1_6_INFRASTRUCTURE_HARDENING.md`
- `codex/handovers/FINAL_AWS_EXECUTION_READINESS_REVIEW.md`
- `docs/submission/DEPLOYMENT_AND_ROLLBACK_CHECKLIST.md`
- `infra/template.yaml`
- `infra/README.md`
- `docs/PROJECT_RULES.md`
- `src/proofloop/agents/providers/bedrock.py` (request-shape verification only)
- current Git status, branch ancestry, remote metadata, and relevant template
  references
- official AWS model, Converse, structured-output, pricing, inference-profile,
  Free Tier, local-login, IAM, root-user, MFA, role, and CloudFormation
  service-role documentation linked above

## Files changed

- `codex/handovers/FINAL_G2A_READONLY_AWS_PREFLIGHT.md` — added this redacted
  discovery record, model decision, bootstrap plan, and G2B gate.

## Documentation updated

Only this separate Codex-owned G2A handoff. Reviewer-facing deployment docs
were not changed because G2A did not alter their contracts. H1 authorizes a
commit and push of this file only to the already verified private remote.

## Git diff summary

The H1 branch diff is exactly this Markdown handoff. No source,
infrastructure, agent/privacy, customer-data, credential, or installer file
belongs to the diff. The exact commit SHA and private push result are reported
after the Git operation because a commit cannot embed its own final SHA.
