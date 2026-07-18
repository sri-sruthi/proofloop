"""ProofLoop agent foundation (isolated from the domain evidence contracts).

This package contains the invoice extraction/reconciliation agents, the
replaceable ModelProvider seam, versioned prompts, business tool specifications,
and the deterministic policy boundary. It must not import
`proofloop.domain.*` or construct any ProofLoop evidence object.
"""
