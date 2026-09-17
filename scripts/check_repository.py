"""Check public repository candidates without printing sensitive matching values."""

from __future__ import annotations

import argparse
import io
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[1]
LEGACY_DIRECTORY = "cord" + "ova-recall-control"
PRIVATE_PARTS = {
    ".azure", ".foundry", ".agent_configs", ".venv", ".venv-mcp", ".venv-foundry",
    "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".playwright-mcp",
}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "storage account key": re.compile(r"AccountKey=[A-Za-z0-9+/]{40,}={0,2}"),
    "SAS signature": re.compile(r"[?&]sig=[A-Za-z0-9%+/]{30,}"),
    "JWT credential": re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
    "credential assignment": re.compile(
        r"(?i)(?:api[_-]?key|client[_-]?secret|password)\s*[:=]\s*['\"][A-Za-z0-9+/=_-]{24,}['\"]"
    ),
}
PERSONAL_PATH = re.compile(r"(?:[A-Za-z]:[\\/]+Users[\\/]+(?!<)[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+/)")


def git(*arguments: str) -> bytes:
    return subprocess.check_output(["git", *arguments], cwd=ROOT)


def text_findings(label: str, content: str) -> list[str]:
    findings = []
    for number, value in enumerate(content.splitlines(), start=1):
        if LEGACY_DIRECTORY in value.lower():
            findings.append(f"{label}:{number}: legacy project reference")
        if PERSONAL_PATH.search(value):
            findings.append(f"{label}:{number}: machine-specific user path")
        for category, pattern in SECRET_PATTERNS.items():
            if pattern.search(value):
                findings.append(f"{label}:{number}: potential {category} (value redacted)")
    return findings


def file_findings(name: str, data: bytes) -> list[str]:
    path = PurePosixPath(name)
    findings = []
    if LEGACY_DIRECTORY in name.lower():
        findings.append(f"{name}: legacy project path")
    if PRIVATE_PARTS.intersection(path.parts):
        findings.append(f"{name}: local-only directory included")
    if (path.name.startswith(".env") and path.name != ".env.example") or path.suffix in {".pem", ".key", ".pfx", ".p12", ".publishsettings"}:
        findings.append(f"{name}: credential file included")
    if name == "infra/main.json" or "/presentation/renders/" in name:
        findings.append(f"{name}: generated build output included")
    if path.suffix == ".pptx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for member in archive.namelist():
                    if member.endswith((".xml", ".rels")):
                        findings.extend(text_findings(f"{name}!{member}", archive.read(member).decode("utf-8")))
        except (zipfile.BadZipFile, UnicodeDecodeError):
            findings.append(f"{name}: unreadable presentation package")
    elif b"\x00" not in data:
        try:
            findings.extend(text_findings(name, data.decode("utf-8-sig")))
        except UnicodeDecodeError:
            pass
    return findings


def check(staged: bool = False) -> list[str]:
    arguments = ["ls-files", "-z", "--cached"]
    if not staged:
        arguments.extend(["--others", "--exclude-standard"])
    names = sorted(set(git(*arguments).decode("utf-8").strip("\x00").split("\x00")) - {""})
    findings = []
    checked = 0
    for name in names:
        path = ROOT / name
        if staged:
            data = git("show", f":{name}")
        elif path.is_file():
            data = path.read_bytes()
        else:
            continue
        findings.extend(file_findings(name, data))
        checked += 1
    print(f"Checked {checked} {'staged' if staged else 'working-tree'} files; {len(findings)} finding(s).")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="Inspect index contents instead of the working tree.")
    arguments = parser.parse_args()
    findings = check(arguments.staged)
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())