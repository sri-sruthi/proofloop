from __future__ import annotations

from pathlib import Path


def test_each_sam_function_build_context_contains_project_sources() -> None:
    repository = Path(__file__).resolve().parents[2]
    template = (repository / "infra" / "template.yaml").read_text(encoding="utf-8")
    root_makefile = repository / "Makefile"

    assert template.count("BuildMethod: makefile") == 2
    assert template.count("CodeUri: ../") == 2
    assert root_makefile.is_file()
    assert root_makefile.read_text(encoding="utf-8").strip() == (
        "include infra/lambda/Makefile"
    )


def test_sam_bedrock_configuration_is_parameterized_and_model_scoped() -> None:
    repository = Path(__file__).resolve().parents[2]
    template = (repository / "infra" / "template.yaml").read_text(encoding="utf-8")

    for parameter in (
        "BedrockModelId:",
        "BedrockModelArn:",
        "BedrockRegion:",
        "MaxModelCalls:",
        "MaxModelRetries:",
        "MaxOutputTokens:",
        "ModelTimeoutSeconds:",
    ):
        assert f"  {parameter}" in template
    assert "PROOFLOOP_BEDROCK_MODEL_ID: !Ref BedrockModelId" in template
    assert "PROOFLOOP_BEDROCK_REGION: !Ref BedrockRegion" in template
    assert "PROOFLOOP_MAX_MODEL_CALLS: !Ref MaxModelCalls" in template
    assert "PROOFLOOP_MAX_RETRIES: !Ref MaxModelRetries" in template
    assert "PROOFLOOP_MAX_OUTPUT_TOKENS: !Ref MaxOutputTokens" in template
    assert "PROOFLOOP_MODEL_TIMEOUT_SECONDS: !Ref ModelTimeoutSeconds" in template
    assert template.count("- bedrock:InvokeModel") == 1
    assert "Resource: !Ref BedrockModelArn" in template
    assert "bedrock:*" not in template
    assert "Resource: \"*\"" not in template


def test_sam_adds_no_always_on_or_out_of_scope_agent_platform() -> None:
    repository = Path(__file__).resolve().parents[2]
    template = (repository / "infra" / "template.yaml").read_text(encoding="utf-8")

    forbidden = (
        "AWS::EC2::NatGateway",
        "AWS::ECS::",
        "AWS::EKS::",
        "AWS::OpenSearchService::",
        "AWS::Cognito::",
        "AgentCore",
        "Strands",
    )
    assert all(value not in template for value in forbidden)
