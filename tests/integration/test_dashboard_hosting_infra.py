from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def test_web_template_keeps_s3_private_and_serves_only_through_cloudfront() -> None:
    template = (ROOT / "infra" / "web-template.yaml").read_text(encoding="utf-8")

    assert "Type: AWS::S3::Bucket" in template
    assert "BlockPublicAcls: true" in template
    assert "BlockPublicPolicy: true" in template
    assert "IgnorePublicAcls: true" in template
    assert "RestrictPublicBuckets: true" in template
    assert "SSEAlgorithm: AES256" in template
    assert "WebsiteConfiguration:" not in template
    assert "Type: AWS::CloudFront::OriginAccessControl" in template
    assert "SigningBehavior: always" in template
    assert "SigningProtocol: sigv4" in template
    assert "Principal: \"*\"" not in template
    assert "Service: cloudfront.amazonaws.com" in template
    assert "AWS:SourceArn" in template


def test_web_template_enforces_https_security_headers_and_runtime_no_cache() -> None:
    template = (ROOT / "infra" / "web-template.yaml").read_text(encoding="utf-8")
    no_cache = template.split("  ProofLoopDashboardNoCachePolicy:", 1)[1].split(
        "  ProofLoopDashboardResponseHeadersPolicy:", 1
    )[0]

    assert "DefaultRootObject: index.html" in template
    assert "ViewerProtocolPolicy: redirect-to-https" in template
    assert "MinimumProtocolVersion: TLSv1.2_2021" in template
    assert "Type: AWS::CloudFront::ResponseHeadersPolicy" in template
    assert "StrictTransportSecurity:" in template
    assert "ContentSecurityPolicy:" in template
    assert "FrameOption: DENY" in template
    assert "ContentTypeOptions:" in template
    assert "ReferrerPolicy: strict-origin-when-cross-origin" in template
    assert "PathPattern: runtime-config.js" in template
    assert "DefaultTTL: 0" in template
    assert "MaxTTL: 0" in template
    assert "EnableAcceptEncodingBrotli: false" in no_cache
    assert "EnableAcceptEncodingGzip: false" in no_cache
    assert "DashboardUrl:" in template


def test_dashboard_loads_public_runtime_config_before_application_code() -> None:
    html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

    assert html.index('src="runtime-config.js"') < html.index('src="app.js"')
    assert "window.PROOFLOOP_RUNTIME_CONFIG" in javascript
    assert "apiBaseUrl" in javascript
    assert "apiKey" not in (ROOT / "dashboard" / "runtime-config.js").read_text(
        encoding="utf-8"
    )


def test_runtime_config_renderer_accepts_only_an_https_origin(tmp_path: Path) -> None:
    from infra.scripts.render_dashboard_runtime_config import render_runtime_config

    output = tmp_path / "runtime-config.js"
    render_runtime_config("https://api.example.test", output)

    rendered = output.read_text(encoding="utf-8")
    assert rendered == (
        'window.PROOFLOOP_RUNTIME_CONFIG = Object.freeze('
        '{"apiBaseUrl":"https://api.example.test"});\n'
    )
    assert "apiKey" not in rendered

    with pytest.raises(ValueError, match="HTTPS origin"):
        render_runtime_config("http://api.example.test", output)
    with pytest.raises(ValueError, match="HTTPS origin"):
        render_runtime_config("https://user@example.test/path?query=1", output)


def test_deployment_scripts_are_idempotent_and_have_a_teardown_path() -> None:
    deploy = (ROOT / "infra" / "scripts" / "deploy_dashboard.sh").read_text(
        encoding="utf-8"
    )
    teardown = (ROOT / "infra" / "scripts" / "delete_dashboard.sh").read_text(
        encoding="utf-8"
    )

    assert "cloudformation validate-template" in deploy
    assert "cloudformation deploy" in deploy
    assert "--role-arn" in deploy
    assert "ProofLoopDashboardCloudFormationServiceRole" in deploy
    assert "render_dashboard_runtime_config.py" in deploy
    assert "s3 sync" in deploy
    assert "s3 cp" in deploy
    assert "cloudfront create-invalidation" in deploy
    assert "DashboardUrl" in deploy
    assert "s3 rm" in teardown
    assert "cloudformation delete-stack" in teardown
