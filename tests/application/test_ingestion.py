from __future__ import annotations

from datetime import timedelta

import pytest

from .conftest import make_agent, make_evidence, make_scope
from proofloop.application.errors import ApplicationError, ErrorCode
from proofloop.application.models import EvidenceIngestStatus
from proofloop.domain.models import AssuranceStatus, EvidenceAttribute, EvidenceOutcome, ReasonCode


def test_valid_evidence_is_persisted_once(system) -> None:
    service, store, _, agent = system
    event = make_evidence(agent, "pii-redaction")

    result = service.ingest_evidence(agent.scope, event)

    assert result.status is EvidenceIngestStatus.ACCEPTED
    assert store.evidence_count == 1


def test_identical_source_event_is_an_idempotent_duplicate(system) -> None:
    service, store, _, agent = system
    event = make_evidence(agent, "pii-redaction", evidence_id="first", source_event_id="same")
    duplicate = event.model_copy(update={"evidence_id": "retry"})

    service.ingest_evidence(agent.scope, event)
    result = service.ingest_evidence(agent.scope, duplicate)

    assert result.status is EvidenceIngestStatus.DUPLICATE
    assert result.canonical_evidence_id == "first"
    assert store.evidence_count == 1


def test_conflicting_source_event_is_rejected_without_overwrite(system) -> None:
    service, store, _, agent = system
    passing = make_evidence(agent, "pii-redaction", evidence_id="pass", source_event_id="same")
    failing = passing.model_copy(update={"evidence_id": "fail", "outcome": EvidenceOutcome.FAIL})
    service.ingest_evidence(agent.scope, passing)

    with pytest.raises(ApplicationError) as captured:
        service.ingest_evidence(agent.scope, failing)

    assert captured.value.code is ErrorCode.EVIDENCE_CONFLICT
    assert "payload" not in captured.value.message.lower()
    assert store.evidence_count == 1


def test_conflicting_source_event_quarantines_assurance_as_amber(system) -> None:
    service, _, _, agent = system
    passing = make_evidence(
        agent,
        "pii-redaction",
        evidence_id="pii-original",
        source_event_id="pii-source-event",
    )
    for control in agent.controls:
        event = (
            passing
            if control.control_id == "pii-redaction"
            else make_evidence(agent, control.control_id)
        )
        service.ingest_evidence(agent.scope, event)
    assert (
        service.sync(agent.scope).compliance.overall_compliance_status
        is AssuranceStatus.GREEN
    )

    conflicting = passing.model_copy(
        update={"evidence_id": "pii-conflict", "outcome": EvidenceOutcome.FAIL}
    )
    with pytest.raises(ApplicationError) as captured:
        service.ingest_evidence(agent.scope, conflicting)

    assert captured.value.code is ErrorCode.EVIDENCE_CONFLICT
    compliance = service.sync(agent.scope).compliance
    assert compliance.overall_compliance_status is AssuranceStatus.AMBER
    assert ReasonCode.EVIDENCE_CONFLICT in compliance.reason_codes
    assert set(compliance.supporting_evidence_ids) >= {
        "pii-original",
        "pii-conflict",
    }


def test_reused_evidence_id_for_another_source_event_is_ambiguous(system) -> None:
    service, _, _, agent = system
    for control in agent.controls:
        service.ingest_evidence(
            agent.scope,
            make_evidence(
                agent,
                control.control_id,
                evidence_id=f"{control.control_id}-reference",
                source_event_id=f"{control.control_id}-source",
            ),
        )
    assert (
        service.sync(agent.scope).compliance.overall_compliance_status
        is AssuranceStatus.GREEN
    )
    reused = make_evidence(
        agent,
        "pii-redaction",
        evidence_id="pii-redaction-reference",
        source_event_id="different-source-event",
    )

    with pytest.raises(ApplicationError) as captured:
        service.ingest_evidence(agent.scope, reused)

    assert captured.value.code is ErrorCode.EVIDENCE_CONFLICT
    compliance = service.sync(agent.scope).compliance
    assert compliance.overall_compliance_status is AssuranceStatus.AMBER
    assert ReasonCode.EVIDENCE_CONFLICT in compliance.reason_codes


def test_foreign_tenant_or_boundary_is_rejected(system) -> None:
    service, store, _, agent = system
    foreign_scope = make_scope(tenant_id="tenant-b", assurance_boundary_id="tenant-b-test")
    foreign_agent = make_agent(foreign_scope)
    event = make_evidence(agent, "audit-logging", workflow=foreign_agent.workflow)

    with pytest.raises(ApplicationError) as captured:
        service.ingest_evidence(agent.scope, event)

    assert captured.value.code is ErrorCode.BOUNDARY_MISMATCH
    assert store.evidence_count == 0


def test_raw_invoice_or_pii_shaped_attributes_are_rejected(system) -> None:
    service, store, _, agent = system
    event = make_evidence(
        agent,
        "audit-logging",
        attributes=(EvidenceAttribute(key="raw_invoice", value="secret"),),
    )

    with pytest.raises(ApplicationError) as captured:
        service.ingest_evidence(agent.scope, event)

    assert captured.value.code is ErrorCode.UNSAFE_EVIDENCE_PAYLOAD
    assert store.evidence_count == 0


@pytest.mark.parametrize(
    "attribute",
    (
        EvidenceAttribute(key="control_active", value="SSN 123-45-6789"),
        EvidenceAttribute(key="synthetic", value=1),
        EvidenceAttribute(key="audit_recorded", value="true"),
    ),
)
def test_allowlisted_attributes_reject_free_text_and_non_boolean_values(
    system,
    attribute,
) -> None:
    service, store, _, agent = system
    event = make_evidence(
        agent,
        "audit-logging",
        attributes=(attribute,),
    )

    with pytest.raises(ApplicationError) as captured:
        service.ingest_evidence(agent.scope, event)

    assert captured.value.code is ErrorCode.UNSAFE_EVIDENCE_PAYLOAD
    assert store.evidence_count == 0


@pytest.mark.parametrize(
    ("field_name", "unsafe_value"),
    (
        ("evidence_id", "123-45-6789"),
        ("source_event_id", "person@example.com"),
        ("evidence_id", "x" * 129),
    ),
)
def test_untrusted_evidence_identifiers_are_bounded_opaque_values(
    system,
    field_name,
    unsafe_value,
) -> None:
    service, store, _, agent = system
    event = make_evidence(agent, "audit-logging").model_copy(
        update={field_name: unsafe_value}
    )

    with pytest.raises(ApplicationError) as captured:
        service.ingest_evidence(agent.scope, event)

    assert captured.value.code is ErrorCode.UNSAFE_EVIDENCE_PAYLOAD
    assert store.evidence_count == 0


@pytest.mark.parametrize(
    "attributes",
    (
        (),
        (
            EvidenceAttribute(key="synthetic", value=True),
            EvidenceAttribute(key="side_effects_absent", value=False),
        ),
    ),
)
def test_generic_canary_evidence_requires_safe_synthetic_attestation(
    system,
    attributes,
) -> None:
    service, store, _, agent = system
    event = make_evidence(
        agent,
        "guardrails",
        attributes=attributes,
    )

    with pytest.raises(ApplicationError) as captured:
        service.ingest_evidence(agent.scope, event)

    assert captured.value.code is ErrorCode.UNSAFE_CANARY_EVIDENCE
    assert store.evidence_count == 0


def test_ingestion_time_is_stamped_by_the_service_clock(system) -> None:
    service, store, clock, agent = system
    event = make_evidence(agent, "audit-logging").model_copy(
        update={"ingested_at": clock.now() + timedelta(days=30)}
    )

    service.ingest_evidence(agent.scope, event)

    stored = store.list_for_workflow(agent.scope, agent.workflow)
    assert stored[0].ingested_at == clock.now()


def test_unknown_control_is_rejected_before_persistence(system) -> None:
    service, store, _, agent = system
    event = make_evidence(agent, "audit-logging").model_copy(
        update={"control_id": "undeclared-control"}
    )

    with pytest.raises(ApplicationError) as captured:
        service.ingest_evidence(agent.scope, event)

    assert captured.value.code is ErrorCode.EVIDENCE_NOT_DECLARED
    assert store.evidence_count == 0
