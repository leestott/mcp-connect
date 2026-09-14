from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Any


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    executable = shutil.which(command[0]) or command[0]
    return subprocess.run(
        [executable, *command[1:]],
        check=check,
        capture_output=True,
        text=True,
    )


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required command is not installed or not on PATH: {name}")


def azure_account() -> dict[str, Any]:
    result = run(["az", "account", "show", "--output", "json"])
    return json.loads(result.stdout)


def resolve_principal(account: dict[str, Any]) -> tuple[str, str]:
    account_user = account.get("user", {})
    account_type = str(account_user.get("type", "")).lower()

    if account_type == "user":
        result = run(
            ["az", "ad", "signed-in-user", "show", "--query", "id", "--output", "tsv"]
        )
        return result.stdout.strip(), "User"

    if account_type == "serviceprincipal":
        client_id = str(account_user.get("name", ""))
        result = run(
            ["az", "ad", "sp", "show", "--id", client_id, "--query", "id", "--output", "tsv"]
        )
        return result.stdout.strip(), "ServicePrincipal"

    raise RuntimeError(
        "Unable to infer the Azure principal. Pass --principal-id and --principal-type explicitly."
    )


def set_azd_value(name: str, value: str) -> None:
    run(["azd", "env", "set", name, value])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or update the local azd environment for Caldova Recall Control."
    )
    parser.add_argument("--environment", default="caldova-recall-demo")
    parser.add_argument("--subscription-id")
    parser.add_argument("--location", default="northcentralus")
    parser.add_argument("--model-deployment", default="caldova-model-router")
    parser.add_argument("--principal-id")
    parser.add_argument(
        "--principal-type",
        choices=("User", "ServicePrincipal", "Group", "ForeignGroup", "Device"),
    )
    args = parser.parse_args()

    require_command("az")
    require_command("azd")

    account = azure_account()
    subscription_id = args.subscription_id or str(account["id"])

    if bool(args.principal_id) != bool(args.principal_type):
        parser.error("--principal-id and --principal-type must be supplied together")
    principal_id, principal_type = (
        (args.principal_id, args.principal_type)
        if args.principal_id
        else resolve_principal(account)
    )

    selected = run(["azd", "env", "select", args.environment], check=False)
    if selected.returncode != 0:
        run(
            [
                "azd",
                "env",
                "new",
                args.environment,
                "--subscription",
                subscription_id,
                "--location",
                args.location,
                "--no-prompt",
            ]
        )

    values = {
        "AZURE_SUBSCRIPTION_ID": subscription_id,
        "AZURE_LOCATION": args.location,
        "AZURE_AI_DEPLOYMENTS_LOCATION": args.location,
        "AZURE_AI_MODEL_DEPLOYMENT_NAME": args.model_deployment,
        "AZURE_PRINCIPAL_ID": str(principal_id),
        "AZURE_PRINCIPAL_TYPE": str(principal_type),
        "ENABLE_MONITORING": "true",
        "ENABLE_HOSTED_AGENTS": "true",
        "ENABLE_CAPABILITY_HOST": "true",
        "USE_EXISTING_AI_PROJECT": "false",
        "AZD_AGENT_SKIP_ACR": "false",
    }
    for name, value in values.items():
        set_azd_value(name, value)

    print(
        f"Configured azd environment '{args.environment}' for {principal_type} deployment."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, json.JSONDecodeError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Environment setup failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None