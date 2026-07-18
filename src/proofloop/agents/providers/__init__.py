"""Real-model adapter boundary for the cloud-neutral ModelProvider seam.

Adapters translate a specific vendor runtime into the vendor-neutral
``ModelProvider`` contract. They accept an already-constructed, structurally
typed client and never import a cloud SDK, model id, region, or credential into
the agent core. Composition happens later in a composition root.
"""

from __future__ import annotations

from proofloop.agents.providers.bedrock import (
    BedrockConverseProvider,
    BedrockProviderConfig,
    BedrockRuntimeClient,
)

__all__ = [
    "BedrockConverseProvider",
    "BedrockProviderConfig",
    "BedrockRuntimeClient",
]
