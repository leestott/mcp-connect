# Caldova Recall Control Tower

A developer demonstration of MCP tool contracts, approval policy, idempotent inventory changes, and a separate Microsoft Agent Framework workflow. Caldova is a fictional pharmaceutical retailer. This is educational software, not a clinical or production recall system.

> Fictional scenario. Synthetic operational data. Recall batch `B-2408-AX7`, 2,196 units across four locations.

## Two execution paths

- **Local Control Tower:** a browser UI and FastAPI service call MCP tools in process. Python builds the analysis summary and enforces approval and quarantine. No model or cloud account is needed.
- **Hosted agent:** four model-backed agents run in a fixed sequence: triage, inventory, supplier/compliance, then a tool-free supervisor summary. Read-only MCP calls use an isolated subprocess bridge. Hosting requires your own configuration and resources.

These paths reuse domain code and synthetic fixtures, but do not share live state. The browser does not call the hosted agent. The supervisor summarizes; it does not dynamically route agents.

## Run locally

Install Python 3.13, then run from the repository root:

```powershell
python -m venv caldova-recall-control/.venv
./caldova-recall-control/.venv/Scripts/python.exe -m pip install -r caldova-recall-control/requirements-ui.txt
./caldova-recall-control/.venv/Scripts/python.exe -m uvicorn control_tower_api:app --app-dir caldova-recall-control/src --host 127.0.0.1 --port 8091
```

On macOS/Linux, use `caldova-recall-control/.venv/bin/python` instead of the Windows executable path.

Open [the Control Tower](http://127.0.0.1:8091), run analysis, approve quarantine, then replay it to confirm no additional stock changes. Keep the service on localhost: an entered approver name is not authenticated identity, and all state is in memory.

### VS Code

Open the repository root and install the Microsoft Python extension. After creating the environment and installing the local dependencies above, run **Python: Select Interpreter** and choose the Python executable inside `caldova-recall-control/.venv`. Run **Tasks: Run Task > Run Caldova Control Tower**. The task uses the selected interpreter on Windows, macOS, and Linux; stop it with **Tasks: Terminate Task**.

The separate Agent Inspector tasks require the Foundry Toolkit extension and hosted-agent configuration. They are not prerequisites for the local Control Tower.

## Validate

```powershell
./caldova-recall-control/.venv/Scripts/python.exe -m pip install -r caldova-recall-control/requirements-test.txt
./caldova-recall-control/.venv/Scripts/python.exe -m pytest caldova-recall-control/tests -q
./caldova-recall-control/.venv/Scripts/python.exe scripts/check_repository.py
```

CI runs local tests, deck builds, repository hygiene checks, and dependency audits. These are not a production certification or a live hosted-agent evaluation.

## Repository layout

| Path | Purpose |
| --- | --- |
| [caldova-recall-control/](caldova-recall-control/README.md) | The application, MCP server, Hosted Agent workflow, Control Tower UI, tests, and presentation |
| [Presenter runbook](caldova-recall-control/presentation/RUNBOOK.md) | Event speaker deck, timings, rebuild commands, and demo limitations |
| [infra/](infra/) | Bicep infrastructure for the Foundry project, Model Router, ACR, and observability |
| [scripts/setup_azd_env.py](scripts/setup_azd_env.py) | Idempotent azd environment bootstrap (detects the principal, sets non-secret values) |
| [azure.yaml](azure.yaml) | Canonical azd manifest that owns the infrastructure and the Hosted Agent lifecycle |
| [scripts/check_repository.py](scripts/check_repository.py) | Redacting checks for public file candidates and staged contents |

## Optional hosting

See the [application README](caldova-recall-control/README.md) for the hosted-agent setup. Run deployment commands from the repository root. Review model availability, costs, identity permissions, and configuration before provisioning. Nothing is deployed by cloning this repository or running the local demo.

## Security and sharing notes

Read [SECURITY.md](SECURITY.md) before exposing a service or publishing a fork. Local credentials, deployment state, generated renders, and old generated decks are ignored. Review the exact staged snapshot before publishing; ignore rules do not remove previously tracked content.

The sharing checker detects selected high-signal patterns, not every secret. It does not audit Git history or inspect pixels in screenshots. Enable GitHub secret scanning and push protection where available, and review screenshots and deck notes manually.

## Contributing

Keep changes focused and use only synthetic data. Include a regression test for behavior changes, run the validation commands above, and describe what was tested in the pull request. Cloud deployment is not required for local-only changes; clearly identify any hosted behavior that was not verified.

Edit presentation generators rather than generated decks; see the [presenter runbook](caldova-recall-control/presentation/RUNBOOK.md) for rebuild instructions. Do not force-add ignored environments, credentials, deployment state, or render output. After selecting files to stage, run `python scripts/check_repository.py --staged` using your project interpreter and review the diff. Follow [SECURITY.md](SECURITY.md) for private vulnerability reports instead of opening a public issue.

## License

Repository code is released under the [MIT License](LICENSE). Event artwork and third-party trademarks remain subject to their owners' rights; see [asset attribution](caldova-recall-control/presentation/assets/README.md).
