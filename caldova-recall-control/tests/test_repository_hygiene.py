import io
import json
from pathlib import Path
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.check_repository import check, file_findings


def test_control_tower_task_uses_selected_interpreter_and_localhost() -> None:
    configuration = json.loads((ROOT / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
    task = next(task for task in configuration["tasks"] if task["label"] == "Run Caldova Control Tower")
    assert task["type"] == "process"
    assert task["command"] == "${command:python.interpreterPath}"
    assert task["args"][task["args"].index("--host") + 1] == "127.0.0.1"
    assert task["options"]["cwd"] == "${workspaceFolder}/caldova-recall-control"


@pytest.mark.parametrize(
    "name",
    [
        ".env", "src/.env.local", "private.pem", ".azure/config.json", "infra/main.json",
        "src/.venv-foundry/config.json", "venv/config.json", "env/config.json",
        ".mypy_cache/data.json", ".ruff_cache/data.json",
    ],
)
def test_rejects_private_and_generated_paths(name: str) -> None:
    assert file_findings(name, b"example")


def test_allows_environment_template_and_role_id() -> None:
    assert not file_findings("src/.env.example", b'API_KEY="<your-key>"')
    assert not file_findings("infra/roles.bicep", b"7f951dda-4ed3-4680-a7ca-43fe172d538d")


def test_rejects_legacy_path_and_reference() -> None:
    legacy = "cord" + "ova-recall-control"
    assert file_findings(f"{legacy}/README.md", b"example")
    assert file_findings("README.md", legacy.encode())


def test_redacts_secret_values() -> None:
    token = "ghp_" + "a" * 36
    findings = file_findings("sample.txt", token.encode())
    assert len(findings) == 1
    assert "GitHub token" in findings[0]
    assert token not in findings[0]


def test_scans_powerpoint_notes_and_relationships() -> None:
    token = "ghp_" + "a" * 36
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("ppt/notesSlides/notesSlide1.xml", token)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", token)
    findings = file_findings("sample.pptx", buffer.getvalue())
    assert len(findings) == 2
    assert all(token not in finding for finding in findings)


def test_rejects_unreadable_presentation() -> None:
    assert file_findings("sample.pptx", b"not a zip archive")


def test_staged_scan_reads_index_instead_of_working_tree(monkeypatch, tmp_path) -> None:
    from scripts import check_repository

    token = "ghp_" + "a" * 36
    (tmp_path / "sample.txt").write_text("safe working copy", encoding="utf-8")
    monkeypatch.setattr(check_repository, "ROOT", tmp_path)

    def fake_git(*arguments: str) -> bytes:
        if arguments[0] == "ls-files":
            return b"sample.txt\x00"
        assert arguments == ("show", ":sample.txt")
        return token.encode()

    monkeypatch.setattr(check_repository, "git", fake_git)
    assert not check()
    findings = check(staged=True)
    assert len(findings) == 1
    assert token not in findings[0]