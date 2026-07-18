"""Deterministic prompt registry and content-hash loader.

Prompts separate the trusted instruction channel from untrusted document/tool
data, forbid payment/approval authority, and refuse instructions embedded inside
invoice content. `load_prompt` returns the definition plus a stable SHA-256 hash
so a prompt version can be pinned and audited.
"""

from __future__ import annotations

from proofloop.agents.prompts.definition import (
    LoadedPrompt,
    PromptDefinition,
    prompt_content_hash,
)
from proofloop.agents.prompts.extraction_v1 import EXTRACTION_PROMPT
from proofloop.agents.prompts.reconciliation_v1 import RECONCILIATION_PROMPT

__all__ = ["LoadedPrompt", "PromptDefinition", "available_prompts", "load_prompt"]

_REGISTRY: dict[str, PromptDefinition] = {
    EXTRACTION_PROMPT.prompt_id: EXTRACTION_PROMPT,
    RECONCILIATION_PROMPT.prompt_id: RECONCILIATION_PROMPT,
}


def available_prompts() -> tuple[str, ...]:
    """Return the ids of all registered prompts."""

    return tuple(sorted(_REGISTRY))


def load_prompt(prompt_id: str) -> LoadedPrompt:
    """Return the prompt definition and its content hash, or raise KeyError."""

    definition = _REGISTRY[prompt_id]
    return LoadedPrompt(
        definition=definition,
        content_hash=prompt_content_hash(definition),
    )
