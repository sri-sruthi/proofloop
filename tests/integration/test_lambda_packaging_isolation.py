"""Lambda packages contain runtime code only, never offline evaluation code."""

from __future__ import annotations

from pathlib import Path

import pytest

from infra.scripts.copy_runtime_package import copy_runtime_package
from infra.scripts.verify_built_handlers import verify_artifact_isolation

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, content: str = "synthetic") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_runtime_copy_excludes_evaluation_caches_and_bytecode(tmp_path: Path) -> None:
    source = tmp_path / "source" / "proofloop"
    destination = tmp_path / "artifact" / "proofloop"
    _write(source / "__init__.py")
    _write(source / "api" / "app.py")
    _write(source / "evaluation" / "metrics.py")
    _write(source / "api" / "__pycache__" / "app.cpython-313.pyc")
    _write(source / "api" / "stale.pyc")
    _write(source / "api" / "optimized.pyo")

    copy_runtime_package(source, destination)

    assert (destination / "__init__.py").is_file()
    assert (destination / "api" / "app.py").is_file()
    assert not (destination / "evaluation").exists()
    assert not tuple(destination.rglob("__pycache__"))
    assert not tuple(destination.rglob("*.pyc"))
    assert not tuple(destination.rglob("*.pyo"))


def test_artifact_verifier_accepts_clean_runtime_tree(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact"
    _write(artifact / "proofloop" / "api" / "app.py")
    verify_artifact_isolation(artifact)


@pytest.mark.parametrize(
    "prohibited",
    (
        Path("proofloop/evaluation/metrics.py"),
        Path("proofloop/api/__pycache__/app.cpython-313.pyc"),
        Path("proofloop/api/stale.pyc"),
        Path("proofloop/api/optimized.pyo"),
    ),
)
def test_artifact_verifier_rejects_offline_or_cache_content(
    tmp_path: Path, prohibited: Path
) -> None:
    artifact = tmp_path / "artifact"
    _write(artifact / prohibited)
    with pytest.raises(RuntimeError, match="prohibited Lambda artifact content"):
        verify_artifact_isolation(artifact)


def test_makefile_uses_the_bounded_runtime_copy_helper() -> None:
    makefile = (REPOSITORY_ROOT / "infra" / "lambda" / "Makefile").read_text(
        encoding="utf-8"
    )
    assert "copy_runtime_package.py" in makefile
    assert "cp -R" not in makefile
