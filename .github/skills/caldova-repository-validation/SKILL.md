---
name: caldova-repository-validation
description: 'Validate Caldova changes for local correctness and sharing readiness. Use when: running focused tests, checking MCP and workflow regressions, scanning repository hygiene or staged contents, reviewing presentation/security evidence, or preparing a PR without deploying or publishing.'
---

# Caldova Repository Validation

## Workflow

1. Start at the repository root and inspect `git status --short` and the scoped diff. Read applicable instructions, the [contribution guide](../../../README.md), [security guidance](../../../SECURITY.md), and [CI workflow](../../workflows/ci.yml). Preserve dirty work from other contributors. Do not stage, revert, reset, commit, push, open a PR, or trigger CI/deployment unless separately requested.
2. Choose the smallest check matching the change: [domain tests](../../../caldova-recall-control/tests/test_caldova_domain.py) for approval/idempotency; [MCP tests](../../../caldova-recall-control/tests/test_caldova_mcp.py) for transport/schema/error contracts; [workflow tests](../../../caldova-recall-control/tests/test_caldova_workflow.py) for read-only tools and run isolation; [API tests](../../../caldova-recall-control/tests/test_control_tower_api.py) for local/online behavior; [hygiene tests](../../../caldova-recall-control/tests/test_repository_hygiene.py) for sharing checks. A new skill or documentation-only change needs frontmatter/link/content checks, not a cloud run.
3. Use the existing Python 3.13 environment below. Run a focused test immediately after behavior edits; repair only the touched slice. Before broader PR readiness claims, run the complete local suite and report actual totals. Keep MCP v2 isolated from the Foundry hosting dependencies. Do not install or upgrade dependencies automatically.
4. Run the existing [sharing checker](../../../scripts/check_repository.py) for working-tree candidates and `--staged` for actual index content. A staged scan does not include unstaged or untracked work. Inspect the exact proposed snapshot, including new files. Preserve credentials, deployment state, private evaluation output, environments, and generated renders outside source control; never force-add ignored artifacts.
5. Check changed JavaScript with `node --check` when Node is available and review desktop/mobile journeys for UI changes. For presentation changes, use the [rehearsal skill](../caldova-presentation-rehearsal/SKILL.md); deck builds write outputs and require matching scope. Inspect dependency audit requirements in CI; if dependencies change and no audit tool is installed, report that gate pending rather than installing tools without approval.
6. Review screenshots, PowerPoint notes/metadata, attribution, and relevant history manually as needed. Pattern scanning does not inspect image pixels, exhaustively audit history, or guarantee absence of secrets. Report suspected vulnerabilities privately under the security policy; do not paste secrets in findings. Rotation or history rewriting requires separate handling and authorization.
7. For a PR handoff, summarize changes, commands and results, unverified behavior, and remaining risks. Local SDK mocks do not prove deployed EasyAuth, managed identity, Blob concurrency, hosted quality, or a complete online demo. Preserve seven golden cases and thresholds; no all-pass evaluation claims without current evidence. CI's manifest-presence check is not infrastructure validation, and its protected deployment job is opt-in, not a routine test gate.

## Commands

Run from the repository root in PowerShell. Pick the relevant focused test first; use the full suite for broader readiness checks.

```powershell
$Python = './caldova-recall-control/.venv/Scripts/python.exe'
if (-not (Test-Path $Python)) { throw 'Select the existing project Python 3.13 environment.' }
& $Python -m pytest caldova-recall-control/tests -q
& $Python scripts/check_repository.py
& $Python scripts/check_repository.py --staged
git diff --check
git diff --cached --check
```

On macOS/Linux substitute `caldova-recall-control/.venv/bin/python`; invoke it directly in a POSIX shell. Check each command's exit status; do not describe later success as erasing an earlier failure. For a JavaScript change, use `node --check caldova-recall-control/src/control_tower_static/app.js`.

## Stop Conditions

Stop after the scoped checks and required gates are satisfied. Missing tooling, unrelated failing tests, cloud-only prerequisites, or unavailable renderers must be reported as limitations. No automatic generation/evaluation reruns, provisioning, deployment, paid operations, destructive actions, or publication. Use a separately approved current Azure/Foundry workflow for cloud readiness; these local validation steps remain useful without any personal skills installed.