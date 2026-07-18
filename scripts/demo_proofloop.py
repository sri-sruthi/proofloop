#!/usr/bin/env python3
"""Print ProofLoop's deterministic customer-readable PS-6.2 demo."""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "src"))

from proofloop.infrastructure.demo import run_demo  # noqa: E402


def main() -> None:
    report = run_demo()
    statuses = " -> ".join(
        scene.compliance.overall_compliance_status.value for scene in report.scenes
    )
    print("ProofLoop — deterministic runtime-to-compliance demo")
    print(f"Status path: {statuses}")
    for scene in report.scenes:
        compliance = scene.compliance
        reasons = ", ".join(reason.value for reason in compliance.reason_codes)
        evidence = ", ".join(compliance.supporting_evidence_ids) or "none"
        print(
            f"\n[{compliance.evaluated_at.isoformat()}] {scene.label}\n"
            f"  Status: {compliance.overall_compliance_status.value}\n"
            f"  Reasons: {reasons}\n"
            f"  Supporting evidence: {evidence}\n"
            f"  Next safe action: {compliance.next_safe_action}"
        )

    print("\nTimeline (last seven days)")
    for item in report.timeline:
        previous = item.previous_status.value if item.previous_status else "UNSET"
        reasons = ", ".join(reason.value for reason in item.reason_codes)
        evidence = ", ".join(item.supporting_evidence_ids) or "none"
        print(
            f"  {item.evaluated_at.isoformat()}  {previous} -> "
            f"{item.current_status.value}  [{reasons}]  evidence={evidence}"
        )

    print("\nIncidents")
    if not report.incidents:
        print("  None")
    for incident in report.incidents:
        print(
            f"  {incident.incident_id}: {incident.status.value}; "
            f"resolution evidence={len(incident.resolution_evidence_ids)}\n"
            f"    Customer impact: {incident.customer_impact}\n"
            f"    Remediation: {incident.remediation_steps}\n"
            f"    Resolution evidence: "
            f"{', '.join(incident.resolution_evidence_ids) or 'none'}"
        )


if __name__ == "__main__":
    main()
