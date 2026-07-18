"""Prompt value types, isolated to avoid an import cycle with the loader."""

from __future__ import annotations

import hashlib
import json

from proofloop.agents._base import AgentModel, Identifier


class PromptDefinition(AgentModel):
    """One versioned, single-purpose prompt."""

    prompt_id: Identifier
    version: Identifier
    purpose: Identifier
    trusted_instructions: str
    output_contract: str
    autonomy_boundary: str
    untrusted_data_policy: str
    escalation_behavior: str


class LoadedPrompt(AgentModel):
    """A prompt definition plus its content hash for pinning/auditing."""

    definition: PromptDefinition
    content_hash: Identifier


def prompt_content_hash(definition: PromptDefinition) -> str:
    canonical = json.dumps(
        definition.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
