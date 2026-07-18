# ProofLoop Final Offline AWS Execution-Readiness Review

**Date:** 2026-07-18  
**Track:** G1.5 - documentation-only AWS execution-readiness review  
**Decision:** **G1.5 COMPLETE / INFRASTRUCTURE HARDENING REQUIRED BEFORE A
FINAL CHANGE SET / AWS EXECUTION NOT AUTHORIZED**  
**Production readiness:** not claimed  
**AWS boundary:** no AWS API call, change set, resource, deployment, or Bedrock
request was made in this track

## Executive verdict

The private CI, Python 3.13, and SAM packaging gates remain green. The current
SAM template is nevertheless not yet an acceptable input to the final
non-executed CloudFormation change set. Three genuine deployment blockers must
first be implemented under a separately approved Track G1.6 and revalidated in
private CI:

1. make the browser origin an explicit deployment parameter and inject it as
   `PROOFLOOP_ALLOWED_ORIGIN`;
2. make reconciliation schedule activation explicit and default it to disabled
   for the first deployment; and
3. define the essential development-stack alarms as infrastructure as code,
   with product-owner-approved thresholds and notification ownership.

The recommended rollout is **backend smoke first with no hosted dashboard, then
the existing dashboard served locally for the controlled assignment demo**.
The API-key boundary remains a controlled development/demo control, not
customer-production identity.

This review changes documentation only. It deliberately does not repair the
template, contact AWS, create a change set, deploy, or invoke Bedrock.

## Evidence carried forward from Track F2

| Evidence | Carried-forward result |
|---|---|
| Canonical repository | `/Users/srisruthi/Aivar Project` |
| Strictly private remote | `sri-sruthi/proofloop-aivar-private`; REST and GraphQL visibility checks recorded `private`/`PRIVATE` |
| Baseline commit | `b42c3dfe786d2201fe010d3718097556f1dd93a5` |
| Passing code-gate commit | `41a5229d1488d0040ca3dea94318bcb800b00a6b` |
| F2 documentation head | `95681ce14e54325e54793b625a2381a35c002d04` |
| Private CI | run `29640732187`, overall success; Python 3.12 and Python 3.13 jobs succeeded |
| Python 3.13 target evidence | CPython 3.13.14 on native `ubuntu-24.04-arm`; 266 tests; both built handlers imported |
| Local Python 3.13 | CPython 3.13.7, pytest 9.1.1, 266 tests; complete tool gate green |
| SAM | CLI 1.163.0; local validate/build and two handler imports passed; native ARM64 Linux CI build passed |
| Security/tooling | mypy 88 files, Ruff, Bandit, strict dependency audit, compile/import and dashboard syntax all passed |
| AWS/change set/deployment | not run; no evidence claimed |
| Bedrock | stub-client coverage only; no real request, latency, accuracy, or cost evidence |

The detailed source is `codex/handovers/FINAL_CI_AND_SAM_GATE.md`. G1.5 does not
reinterpret a passing package/CI gate as proof that the packaged infrastructure
is ready to execute.

## Current template and application facts

The application reads `PROOFLOOP_ALLOWED_ORIGIN` and otherwise silently falls
back to `http://localhost:8000`. The API applies an exact-origin CORS policy.
`infra/template.yaml` neither declares an origin parameter nor injects that
environment variable.

The template hard-codes the five-minute EventBridge schedule as enabled. A
successful first stack creation would therefore start scheduled reconciliation
before health, authentication, persistence, canary, DLQ, alarm, and rollback
checks have been completed and assigned to operators.

The template defines no `AWS::CloudWatch::Alarm` resources and no notification
destination. It does create, or causes SAM to generate, two Lambdas, an HTTP
API, a DynamoDB table, log groups, an EventBridge rule, two distinct SQS failure
queues, permissions, and execution roles. It does not deploy the static
dashboard.

The API authenticates protected routes by comparing one `X-API-Key` value with
one configured secret. `NoEcho` protects parameter display but does not turn a
Lambda environment variable into a production secret-management or identity
system. There is no customer IAM federation, JWT/OIDC validation, role model,
tenant-specific authorization, managed rotation, or edge protection.

## Blocker classification

The classification is by the **earliest gate at which the item must be closed**.
An item closed before the change set remains a prerequisite for execution.

| Finding | Must fix before creating the final non-executed change set | Must fix before executing the change set | Safe to defer until after the development deployment |
|---|---|---|---|
| `PROOFLOOP_ALLOWED_ORIGIN` not injected | **Yes.** Add a visible template parameter, inject the environment variable, test it, and select the exact initial origin before the template is used for the final change set. | The reviewed value must still match the controlled client at execution time. | Multi-origin policy, a hosted HTTPS origin, and production edge identity may defer; explicit origin wiring may not. |
| Essential alarms absent | **Yes.** The final change set must show the approved minimal alarm resources and their action strategy; otherwise reviewers cannot assess resources, cost, or operational coverage. | A real notification destination and named response owners must be valid before execution. | Alarm-state tests, synthetic notification tests, and production-scale extensions may run after deployment; the essential alarm definitions may not defer. |
| Schedule starts immediately | **Yes.** Add an explicit activation parameter/condition with a disabled default and test the rendered resource before the final change set. | The reviewed first-deployment value must be disabled. | Enabling the schedule is intentionally deferred to a reviewed post-smoke stack update. |

### Other release gates exposed by the review

Before the final non-executed change set, the product owner must also freeze the
stack name, region, model/inference-profile identifier and least-privilege ARN,
dashboard hosting choice, table deletion/replacement policy, log/data retention,
alarm-default decision, and notification design. Track G1.6 must pass the full
private CI/SAM gate before any AWS preflight or change-set work begins.

Before execution, the AWS account/deployment identity, model access, API-key
delivery, budget, owners, smoke plan, rollback authority, and exact change-set
contents must be verified. Those are operational approvals, not template-test
substitutes.

After the controlled deployment, while the schedule remains disabled, the team
may run bounded health/authentication/input/persistence/canary/DLQ/rollback and
alarm checks. A real Bedrock smoke requires its own explicit authorization.

## Finding 1 - explicit browser origin

### Options

| Option | Trade-off and cost | Failure risk | Recommendation |
|---|---|---|---|
| **A. Required `AllowedOrigin` parameter, injected as `PROOFLOOP_ALLOWED_ORIGIN`** | No additional AWS resource or recurring cost. Every environment must supply a deliberate value. | A typo blocks browser calls, but it is visible in parameter review and testable. Avoid a permissive wildcard and validate the expected URL shape. | **Recommended.** Use `http://localhost:8000` only for the controlled initial local-dashboard demo. Prefer no template default so omission fails visibly. |
| B. Hard-code `http://localhost:8000` in the template | No resource cost and a smaller patch. | Couples every deployment to one development origin, makes later hosted use an implementation edit, and can be mistaken for an intentional universal policy. | Reject for the final design. It is visible but not safely configurable. |
| C. Configure CORS only in API Gateway | No material resource cost. Centralizes edge CORS configuration. | The application already enforces exact-origin behavior. Two policies can diverge, and changing only the gateway does not satisfy the application's environment contract. | Do not use as a replacement. Gateway CORS can be an additional layer only if both layers are tested as one policy. |

### Recommended G1.6 behavior

- Add an explicit string parameter named `AllowedOrigin`.
- Do not hide the deployment decision behind the application's localhost
  fallback. Prefer a required parameter with no default.
- Inject `PROOFLOOP_ALLOWED_ORIGIN: !Ref AllowedOrigin` into the API function.
- Add structural tests proving the parameter exists, the environment injection
  is exact, and the template does not use `*`.
- For the controlled assignment deployment, approve
  `http://localhost:8000`; any hosted-dashboard choice requires a separate
  approved HTTPS origin.

## Finding 2 - schedule activation

At one run every five minutes, the enabled rule would nominally request 288
scheduled runs per day and about 8,640 in a 30-day month, before retries. That is
not automatically expensive, but it creates unattended writes, logs, failure
messages, and operational state before the stack has passed smoke checks.

### Options

| Option | Trade-off and cost | Failure risk | Recommendation |
|---|---|---|---|
| **A. Explicit activation parameter, disabled by default** | No new service or recurring charge. The rule can exist while disabled; scheduled Lambda, DynamoDB, log, and failure-path usage does not begin until an approved update enables it. | Operators can forget to enable it. Mitigate with a post-smoke checklist item and reviewed stack update, not a console edit. | **Recommended.** Add an `EnableReconciliationSchedule`-style parameter with constrained values and a disabled first-deployment default. |
| B. Deploy enabled, then disable manually | Minimal template work. | Race window during creation, console drift, unreviewed state, and possible invocations before alarms/owners are ready. | Reject. It preserves the accepted blocker. |
| C. Omit the schedule and add it in a second template revision | Guarantees no initial scheduled execution and avoids its rule until later. | The first change set cannot review the final schedule, DLQ, permissions, or costs; the later update is larger and easier to misconfigure. | Acceptable only if the product owner explicitly wants a backend-only first stack. Less complete than Option A for this assignment. |

### Recommended activation gate

Keep the schedule disabled until all of the following pass with reserved
synthetic data:

1. public health and protected-route authentication checks;
2. safe input rejection and metadata-only persistence checks;
3. deterministic canary and compliance-state checks;
4. both DLQ paths and their ownership/runbook checks;
5. essential alarm state and notification checks; and
6. rollback/containment readiness.

Enable it only through a reviewed CloudFormation stack update. Do not create
manual console drift.

## Finding 3 - essential alarms as infrastructure as code

### Minimal controlled-development set

The following is a **proposed default for product-owner approval**, not an
approved threshold or destination and not an implemented change. A conservative
starting pattern is one standard-resolution metric alarm per row, a 300-second
period, one evaluation period, threshold `>= 1`, and missing data treated as not
breaching. This favors immediate visibility in a low-volume development stack;
it may be noisy and must be deliberately accepted or changed in Track G1.6.

| Essential alarm | Metric/dimension intent | Proposed development default | Why essential before execution |
|---|---|---|---|
| API Lambda errors | `AWS/Lambda Errors`, API function | At least 1 in 5 minutes | Detects failed protected/API work. |
| API Lambda throttles | `AWS/Lambda Throttles`, API function | At least 1 in 5 minutes | Detects the reserved-concurrency boundary rejecting work. |
| Scheduled Lambda errors | `AWS/Lambda Errors`, scheduled function | At least 1 in 5 minutes | Detects failed reconciliation after activation. |
| Scheduled Lambda throttles | `AWS/Lambda Throttles`, scheduled function | At least 1 in 5 minutes | Detects scheduled work rejected at its concurrency boundary. |
| EventBridge delivery DLQ depth | `AWS/SQS ApproximateNumberOfMessagesVisible`, schedule DLQ | At least 1 visible message | Surfaces schedule delivery exhaustion. |
| Lambda async-destination DLQ depth | Same SQS metric, Lambda failure queue | At least 1 visible message | Surfaces exhausted asynchronous function processing. |
| EventBridge failed invocations | `AWS/Events FailedInvocations`, reconciliation rule | At least 1 in 5 minutes | Detects failed target delivery even before queue inspection. |
| HTTP API 5xx | `AWS/ApiGateway 5xx`, API/stage | At least 1 in 5 minutes | Detects server failures visible to callers. |
| DynamoDB read throttling | `AWS/DynamoDB ReadThrottleEvents`, table | At least 1 in 5 minutes | Detects failed or delayed assurance reads/reconciliation. |
| DynamoDB write throttling | `AWS/DynamoDB WriteThrottleEvents`, table | At least 1 in 5 minutes | Detects failed evidence/state persistence. |

The exact metric dimensions and generated logical-resource references must be
covered by structural tests. If a metric's target-runtime semantics differ from
the proposal, G1.6 must report and correct the design rather than retain a
nonfunctional alarm.

### Alarm action options

| Option | Trade-off and cost | Failure risk | Recommendation |
|---|---|---|---|
| **A. Template alarms plus an approved existing notification topic ARN parameter** | Ten standard metric alarms create metric-alarm charges while present; the account's aggregate free-tier use must not be assumed. Reusing an owned topic avoids inventing subscriptions in this stack. | A wrong/unowned ARN produces silent operational gaps or deployment failure. The owner must verify delivery before execution. | **Recommended**, if an existing controlled topic and owner are approved. Make the destination explicit; do not insert a placeholder ARN. |
| B. Template alarms with no actions and active manual monitoring | Avoids notification-resource work but still incurs alarm metric charges. | Alarms can enter ALARM without reaching an operator. This is unsuitable for deployment execution, schedule activation, and rollback response. | Useful only for local/template review or the non-executed change set; reject as the execution design. |
| C. Create an SNS topic/subscription in this stack | Self-contained and reviewable; adds SNS requests/delivery and operational ownership, with subscription confirmation and endpoint handling. | Inventing an email/endpoint leaks or misroutes operational data; an unconfirmed subscription creates false confidence. | Viable only after explicit approval of resource, endpoint, and owner. Do not speculate it into G1.6. |

### Production-scale extensions safe to defer

For this controlled development deployment, the ten alarms above are the
essential minimum. The following are useful production extensions but should
not expand G1.6 without separate scope: latency/duration percentiles, concurrency
headroom, API 4xx rate, DynamoDB consumed-capacity trends and system errors, DLQ
oldest-message age, log metric filters, privacy-leak detectors, anomaly
detection, composite alarms, cross-account observability, SLO dashboards, and
load-derived multi-period thresholds.

CloudWatch alarms are billed by alarm metric-hour and logs by ingestion/storage;
current regional pricing should be checked in the target account before
execution. The public pricing reference is [Amazon CloudWatch
Pricing](https://aws.amazon.com/cloudwatch/pricing/).

## Dashboard deployment choice

| Option | Assignment impact, security, time, and cost | Verdict |
|---|---|---|
| **A. Deployed backend plus local dashboard** | Uses the existing reviewed static assets and no dashboard cloud resources. Keeps source/output in the private repository and on the controlled demo machine. Requires the explicit localhost origin and puts the development API key in the browser tab's `sessionStorage`; the machine/session must therefore be controlled. | **Recommended demo state after backend smoke.** Best balance of assignment impact, no-public-code restrictions, time, and cost. |
| B. Privately controlled hosted dashboard | Requires a deliberate private delivery/auth design, likely additional storage/CDN/identity resources, a hosted HTTPS origin, deployment and rollback work, and ongoing request/storage/transfer costs. Static browser code is necessarily delivered to authorized clients, and the current API-key model remains insufficient for customer production. | Defer. It adds risk and scope without being required to prove the assignment. |
| **C. No dashboard hosting until after backend smoke** | Smallest initial resource set and attack surface. Backend smoke can use controlled commands and safe response fields. It temporarily reduces visual impact. | **Recommended first-deployment sequence**, followed by Option A for the controlled demo. |

The combined recommendation is **C, then A**: create/review a backend-only stack,
keep the schedule disabled, complete backend smoke, then serve the existing
dashboard locally. Do not add hosted dashboard resources to the initial
development stack.

## Authentication classification

The current API-key check is acceptable only as a controlled development/demo
boundary when all of these conditions hold: synthetic data, a high-entropy key,
secure out-of-band delivery, a controlled browser/machine, no public
distribution, short lifetime, named rotation/revocation ownership, and bounded
access to the API URL.

It is not production IAM, user identity, tenant authorization, or secret
rotation. Customer production would require an explicitly designed identity
provider or signed workload identity, scoped authorization, rotation/audit,
rate controls, and appropriate edge protections. Those production extensions
may defer beyond the controlled development deployment; honest classification
and secure handling may not.

## Data, stack, region, retention, and rollback risks

- **DynamoDB replacement/deletion:** the current table has no explicit
  `DeletionPolicy` or `UpdateReplacePolicy`. CloudFormation normally deletes a
  resource when it is removed or when the stack is deleted; replacement
  protection is controlled separately. Retaining a resource can preserve data
  but leaves an orphaned, billable resource. See [CloudFormation
  `DeletionPolicy`](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-deletionpolicy.html).
- **Recommended controlled-dev policy:** decide this in G1.6. If the stack is
  guaranteed synthetic and disposable, an explicit delete-on-stack-removal
  policy plus retain-on-replacement is a reasonable low-cost balance. If audit
  evidence must survive stack deletion, retain policies and a cleanup owner are
  required instead. The choice blocks the final change set.
- **Stack name:** affects CloudFormation identity and named Lambda/log resources.
  A mistaken name can create a second billable stack instead of updating the
  reviewed one. Recommend one explicit name such as `proofloop-dev`, subject to
  product-owner approval.
- **Region:** the stack region controls most resources; `BedrockRegion` controls
  the model client and can diverge. Recommend one approved region only after
  G2 verifies caller identity and model/inference-profile availability. Product-
  owner testimony says Lambda is available in Mumbai (`ap-south-1`), but G1.5
  makes no AWS verification claim.
- **Retention:** log groups currently declare 30 days. Evidence/compliance
  records have bounded TTLs in the application model, while some state/registry
  records are not TTL-expiring. Owners must accept or change these rules before
  the final change set.
- **Rollback:** schedule disablement is the first containment control for
  reconciliation faults. API-key rotation/revocation, exact prior artifact
  recovery, safe evidence preservation, table policy, DLQ handling, and stack
  deletion authority must be assigned before execution.

## Low-cost resource and operation inventory

The current backend is serverless and contains no NAT Gateway, hosted dashboard,
OpenSearch, EKS, ECS, or always-on compute. Low-cost does not mean zero-cost.

| Cost-bearing resource/operation | Cost driver and control |
|---|---|
| API and scheduled Lambda | Requests and duration. Reserved concurrency caps concurrency; it is not provisioned-concurrency capacity. Keeping the schedule disabled prevents its normal invocation/duration usage before smoke. [Lambda pricing](https://aws.amazon.com/lambda/pricing/) |
| HTTP API | API calls and data transfer out; there is no minimum fee. [API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/) |
| DynamoDB on-demand table/GSI | Reads, writes, transactional unit multipliers, index activity, and storage. Schedule activation creates ongoing read/write activity. [DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/) |
| CloudWatch logs and proposed alarms | Log ingestion/storage/query and alarm metric-hours. Ten proposed alarms may or may not fit within the account-wide free tier; do not assume. [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/) |
| Two SQS failure queues | API requests, payload chunks, retention/storage, and any inspection/replay operations; mostly idle when no failures occur. [SQS pricing](https://aws.amazon.com/sqs/pricing/) |
| EventBridge scheduled rule | The rule triggers downstream Lambda/DynamoDB/log activity every five minutes after activation; retry/failure handling can add operations. The template uses a legacy scheduled rule, not EventBridge Scheduler. [Scheduled-rule documentation](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html) |
| Bedrock | Model/provider/region/inference-tier-specific input/output-token charges. The code's call/token caps bound a request but do not predict price. No request is authorized in G1.5. [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) |
| SAM deployment artifacts | S3 object storage and request operations for uploaded artifacts; the packaging bucket may be managed outside this stack. |
| CloudFormation/IAM | CloudFormation adds no charge for standard `AWS::*` resources; underlying services are billed. IAM roles/policies have no separate service charge. [CloudFormation pricing](https://aws.amazon.com/cloudformation/pricing/) |
| Hosted dashboard, if later added | Storage, requests, delivery/data transfer, DNS, identity, and monitoring depending on the approved design. None is in the current template. |

Exact currency estimates require the approved region, model/profile, traffic,
retention, alarm design, and account-wide free-tier state. G1.5 does not invent
those values.

## Product-owner decision table

| Question | Recommended default | Cost/security consequence | Deployment blocked without decision? |
|---|---|---|---|
| What browser origin is allowed? | `http://localhost:8000` for this controlled local-dashboard demo; no wildcard | No extra resource cost; exact origin limits browser access. HTTP localhost is not a hosted-production origin. | **Final change set: yes** |
| What is the initial schedule state? | Disabled; enable only by reviewed stack update after smoke | Avoids pre-smoke invocations/writes/logs and unattended failure state | **Final change set and execution: yes** |
| Are the proposed ten alarm defaults accepted? | 300-second period, one evaluation period, threshold at least one event/message, missing data non-breaching, subject to explicit approval | Faster detection with possible development noise; ten alarm metric-hours | **Final change set: yes** |
| Where do alarm actions go, and who owns them? | Approved existing SNS topic ARN and named responder; otherwise explicitly approve a stack-managed topic and subscription | Misrouting can expose metadata or create false confidence; SNS use may add small request/delivery cost | **Final change set design: yes; execution: yes** |
| Which dashboard option? | No hosted dashboard for backend smoke, then local dashboard (C then A) | Lowest resource cost and public-exposure risk; controlled machine holds the demo key | **Final resource set: yes** |
| What is the authentication boundary? | Controlled dev API key only, with high entropy, short lifetime, owner, secure channel, and rotation | Not customer-production identity; compromise grants protected-route access | **Execution: yes** |
| Which AWS account and deployment role? | One named least-privilege role verified in G2; never record credentials | Wrong identity can expose or create resources in the wrong account | **G2 and execution: yes** |
| What stack name? | `proofloop-dev`, if approved | Prevents accidental parallel stacks/cost and anchors rollback | **Final change set: yes** |
| What stack region? | `ap-south-1` only if G2 confirms the account and selected Bedrock path support it | Region affects availability, latency, ARNs, residency, and price | **Final change set: yes** |
| Which Bedrock model/profile and ARN? | Exact approved model or inference-profile ID and least-privilege invocation ARN discovered in G2 | Determines access, IAM, behavior, latency, and token price | **Final change set: yes** |
| What monthly budget and alerts apply? | Product-owner amount, thresholds, recipients, and anomaly policy; no invented amount | Limits surprise rather than technically stopping spend unless a separate control is designed | **Execution: yes** |
| Who owns logs, each DLQ, smoke, and rollback? | Named primary/backup owners with response and replay/containment runbooks | Unowned failures can accumulate and invalidate the demo | **Execution: yes** |
| What table deletion/replacement policy applies? | Synthetic-only dev: explicit delete on stack removal and retain on replacement; otherwise choose retain plus cleanup owner | Delete risks evidence loss; retain risks orphaned ongoing storage cost | **Final change set: yes** |
| Are current retention values accepted? | 30-day logs and current bounded evidence/timeline TTLs, unless the owner records a different requirement | Longer retention costs more and expands data exposure; shorter retention reduces diagnostics | **Final change set: yes** |
| What synthetic smoke and rollback sequence is approved? | Checklist order in this review; schedule remains disabled throughout initial smoke | Small bounded request cost; catches destructive or privacy failures before automation | **Execution: yes** |
| When may the schedule be enabled? | Only after all post-deploy gates pass and a reviewed update is approved | Starts recurring Lambda/DynamoDB/log activity and failure exposure | No for initial deployment; **yes for schedule activation** |
| May one bounded real Bedrock smoke run? | No by default; separate explicit authorization after model/access/cost review | Incurs model charges and processes the reserved synthetic request | No for stack creation; **yes for real-model evidence** |

## Exact gates by phase

### Must fix before the final non-executed change set

1. Complete approved Track G1.6 using TDD:
   - explicit `AllowedOrigin` parameter and API environment injection;
   - explicit schedule-activation parameter, disabled by default;
   - the approved essential alarm set and action/destination design;
   - explicit table deletion/replacement decision if approved for G1.6 scope.
2. Pass the complete local and private CI/SAM gate on Python 3.12 and 3.13,
   including template structural tests, SAM validation/build, and built-handler
   imports.
3. Freeze dashboard strategy, stack name, target region, model/profile ID and
   ARN, alarm defaults, notification design, origin, and retention policies.
4. Reinspect the complete proposed template/IAM/resource diff and private
   repository state.

### Must fix before executing the change set

1. Verify the exact caller account and least-privilege deployment role.
2. Verify region/model/inference-profile access and ARN semantics without
   invoking the model.
3. Confirm the first deployment keeps the schedule disabled.
4. Provide the real high-entropy API key through an approved secret channel;
   name its rotation/revocation owner.
5. Approve budget thresholds/recipients and alarm notification destination;
   name log, DLQ, smoke, and rollback owners.
6. Review the non-executed change set's exact resources, IAM, replacements,
   deletion/retention behavior, parameters, and cost implications.
7. Approve reserved synthetic smoke data, containment triggers, rollback
   artifact, and destructive rollback authority.

### Safe to perform after the controlled development deployment

While the schedule remains disabled:

1. run health, authentication, validation, persistence, canary, and metadata-
   only log/table smoke checks;
2. verify both DLQ paths, alarm states, notifications, and the replay/runbook;
3. exercise containment and rollback checks;
4. serve the existing dashboard locally and run the 30-45 second demo;
5. with separate authorization only, make one bounded real Bedrock smoke call;
6. enable the schedule only through a reviewed stack update after every
   prerequisite passes; and
7. defer hosted dashboard, customer-production identity, advanced alarms,
   WAF/rate policy, load testing, and multi-tenant production controls to a
   separately scoped track.

## Recommended Track G1.6 design

Track G1.6 should remain a narrow infrastructure-hardening implementation:

1. TDD structural tests first for a required `AllowedOrigin` parameter and exact
   API Lambda environment injection.
2. TDD structural tests first for an explicit schedule activation parameter
   whose default/rendered first-deployment state is disabled.
3. TDD structural tests first for the ten essential standard metric alarms,
   their resource dimensions, missing-data behavior, and an explicit approved
   notification strategy. Defaults remain proposals until the product owner
   approves them.
4. If explicitly approved, TDD the table deletion/replacement policy; otherwise
   record it as a remaining blocker rather than guessing.
5. Update deployment docs and parameter examples without placing keys, account
   IDs, real ARNs, or notification endpoints in Git.
6. Run the complete clean local gate and private Python 3.12/3.13 CI/SAM gate.
7. Stop before any AWS command or change-set creation.

Do not add a hosted dashboard, Cognito, WAF, Secrets Manager, NAT, new business
behavior, production identity, speculative services, or agent/privacy changes.

## Proposed Track G1.6 prompt

> **Track G1.6 - approved TDD infrastructure hardening for ProofLoop**
>
> Repository: `/Users/srisruthi/Aivar Project`.
>
> Start from `codex/handovers/FINAL_AWS_EXECUTION_READINESS_REVIEW.md` and the
> private passing F2 evidence. This track authorizes only the reviewed
> infrastructure-hardening implementation; do not call AWS, create a change
> set, deploy, invoke Bedrock, or create resources.
>
> Use test-driven development. First add failing focused structural tests, then
> make the narrowest changes to `infra/template.yaml`, validation scripts,
> infrastructure tests, and deployment documentation to:
>
> 1. add a required `AllowedOrigin` parameter with no invisible application
>    default and inject it as `PROOFLOOP_ALLOWED_ORIGIN` into the API Lambda;
>    preserve exact-origin behavior and prohibit a wildcard;
> 2. add an explicit schedule-activation parameter with the reconciliation
>    schedule disabled by default; it must be enabled only through a reviewed
>    stack update after smoke;
> 3. add the product-owner-approved minimal standard-resolution alarm set for
>    both Lambdas' errors/throttles, both DLQ visible-message depths,
>    EventBridge failed invocations, HTTP API 5xx, and DynamoDB read/write
>    throttling; use only approved thresholds, missing-data behavior, and
>    notification strategy—do not invent an ARN, endpoint, or owner; and
> 4. implement the separately approved DynamoDB deletion/update-replacement
>    policy, or report that exact decision as blocking if it has not been made.
>
> Keep dashboard hosting out of the stack. Preserve API-key authentication as
> an explicitly controlled development/demo boundary; do not implement
> production identity. Do not edit agent/privacy behavior or add speculative
> services.
>
> Run pytest, mypy, Ruff, Bandit, strict dependency audit, compileall, both
> demos, the structural template validator, dashboard syntax/import isolation,
> SAM validate/build, built-handler imports, and the complete private Python
> 3.12/3.13 CI matrix. Produce a G1.6 handoff with the exact template/resource/
> IAM/cost diff, test-first evidence, CI URL/conclusions, parameters and
> remaining product-owner decisions. Stop before AWS preflight or change-set
> creation.

## Proposed Track G2 prompt

> **Track G2 - AWS read-only preflight and non-executed change set for
> ProofLoop**
>
> Repository: `/Users/srisruthi/Aivar Project`.
>
> Start only after the approved Track G1.6 infrastructure changes are committed
> to the strictly private repository and the complete Python 3.12/3.13 CI/SAM
> gate is green. Verify that evidence before any AWS command. Do not modify
> infrastructure implementation in this track; if a defect is found, stop and
> return it to a new implementation track.
>
> With explicit product-owner authorization for the named AWS account and role,
> run only read-only identity, region, quota/access, and Bedrock model/inference-
> profile discovery. Do not invoke Bedrock. Record the caller account/role,
> approved stack name and region, exact model/profile ID and least-privilege
> ARN, explicit allowed origin, schedule-disabled value, alarm thresholds/topic
> and owners, API-key secure-delivery method, budget, tenant/environment/
> assurance boundary, retention, smoke, and rollback decisions without exposing
> credentials or secrets.
>
> Then package the already-reviewed private commit and create one CloudFormation
> change set using `--no-execute-changeset`. Do not execute it. Inspect and
> record every resource, IAM permission, parameter, replacement/deletion risk,
> schedule state, alarm action, artifact, and cost-bearing operation. Confirm no
> hosted dashboard or unexpected fixed-cost resource appears. If privacy,
> identity, model, parameter, IAM, replacement, alarm, or cost evidence is
> incomplete, do not create—or delete/recreate—the change set speculatively;
> report the precise blocker.
>
> Produce the exact change-set ID/URL-safe identifier, status, template digest,
> parameter manifest with secrets redacted, resource/IAM diff, estimated cost
> drivers, and a human execution/rollback decision packet. Do not execute the
> change set, deploy, invoke Bedrock, enable the schedule, create a public
> artifact, or claim production readiness.

## Files changed by Track G1.5

The intended G1.5 documentation-only change set is:

- `codex/handovers/FINAL_AWS_EXECUTION_READINESS_REVIEW.md`
- `README.md`
- `docs/submission/DEMO_RUNBOOK.md`
- `docs/submission/DEPLOYMENT_AND_ROLLBACK_CHECKLIST.md`
- `docs/superpowers/plans/2026-07-18-proofloop-track-g1-5-offline-readiness-review.md`

No template, source, test, workflow, agent/privacy, AWS resource, or cloud state
is changed by G1.5.

## Final boundary

ProofLoop has a strong local/private-CI application and SAM package baseline.
It is **not** ready for a final change set until G1.6 closes the three accepted
infrastructure blockers and CI revalidates the result. It is **not** ready to
execute a change set until the identity, model, security, budget, ownership,
smoke, retention, and rollback decisions are complete. It is not
production-ready.
