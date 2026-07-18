from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_renders_api_controls_and_each_controls_own_state() -> None:
    javascript = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "dashboard" / "styles.css").read_text(encoding="utf-8")

    assert "apiControls.length ? apiControls : fallbackControls" in javascript
    assert "control-dot-${controlState.toLowerCase()}" in javascript
    assert ".control-dot-green" in styles
    assert ".control-dot-amber" in styles
    assert ".control-dot-red" in styles
    assert ".AMBER .control-dot" not in styles
    assert ".RED .control-dot" not in styles
