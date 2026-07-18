from __future__ import annotations

import pytest

from proofloop.agents.prompts.loader import available_prompts, load_prompt


def test_exactly_the_two_expected_prompts_exist() -> None:
    assert available_prompts() == ("invoice.extraction", "invoice.reconciliation")


def test_prompt_loads_with_stable_deterministic_hash() -> None:
    first = load_prompt("invoice.extraction")
    second = load_prompt("invoice.extraction")
    assert first.content_hash == second.content_hash
    assert len(first.content_hash) == 64
    assert first.definition.version == "1.0.0"


def test_extraction_and_reconciliation_hashes_differ() -> None:
    assert (
        load_prompt("invoice.extraction").content_hash
        != load_prompt("invoice.reconciliation").content_hash
    )


@pytest.mark.parametrize("prompt_id", ["invoice.extraction", "invoice.reconciliation"])
def test_prompts_forbid_payment_authority_and_untrusted_obedience(
    prompt_id: str,
) -> None:
    definition = load_prompt(prompt_id).definition
    autonomy = definition.autonomy_boundary.lower()
    policy = definition.untrusted_data_policy.lower()
    # No payment/approval authority.
    assert "no authority" in autonomy or "cannot" in autonomy
    assert "pay" in autonomy or "approve" in autonomy
    # Untrusted content is data and embedded instructions are refused.
    assert "untrusted" in policy
    assert "never" in policy or "not" in policy
    # Never asks the model to reveal hidden reasoning.
    combined = " ".join(
        [
            definition.trusted_instructions,
            definition.output_contract,
            definition.autonomy_boundary,
            definition.escalation_behavior,
        ]
    ).lower()
    assert "chain-of-thought" not in combined
    assert "hidden reasoning" not in combined


def test_unknown_prompt_raises() -> None:
    with pytest.raises(KeyError):
        load_prompt("invoice.payment")
