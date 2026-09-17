import argparse
import json
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import AzureDeveloperCliCredential


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--agent-version", required=True)
    parser.add_argument("--evaluator", required=True)
    parser.add_argument("--evaluator-version", default="1")
    parser.add_argument("--deployment", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines()]
    client = AIProjectClient(
        endpoint=args.endpoint,
            credential=AzureDeveloperCliCredential(process_timeout=60),
    ).get_openai_client()

    evaluation = client.evals.create(
        name=f"{args.evaluator}-agent-v{args.agent_version}",
        metadata={
            "azd_agent": args.agent_name,
            "azd_agent_version": args.agent_version,
        },
        data_source_config={
            "type": "custom",
            "schema": {
                "item": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "expected_behavior": {"type": "string"},
                    },
                    "required": ["query", "expected_behavior"],
                },
                "sample": {
                    "type": "object",
                    "properties": {"output_text": {"type": "string"}},
                },
            },
            "include_sample_schema": True,
        },
        testing_criteria=[
            {
                "type": "azure_ai_evaluator",
                "name": args.evaluator,
                "evaluator_name": args.evaluator,
                "evaluator_version": args.evaluator_version,
                "initialization_parameters": {
                    "deployment_name": args.deployment,
                    "model": args.deployment,
                    "threshold": 4,
                },
                "data_mapping": {
                    "query": "{{item.query}}",
                    "response": "{{sample.output_text}}",
                    "expected_behavior": "{{item.expected_behavior}}",
                },
            }
        ],
    )
    run = client.evals.runs.create(
        eval_id=evaluation.id,
        name=f"{args.evaluator}-agent-v{args.agent_version}",
        metadata={"azd_agent": args.agent_name},
        data_source={
            "type": "azure_ai_target_completions",
            "input_messages": {
                "type": "template",
                "template": [
                    {
                        "role": "user",
                        "content": "{{item.query}}",
                        "type": "message",
                    }
                ],
            },
            "source": {"type": "file_content", "content": rows},
            "target": {
                "type": "azure_ai_agent",
                "name": args.agent_name,
                "version": args.agent_version,
                "tool_descriptions": [],
            },
        },
    )
    print(json.dumps({"eval_id": evaluation.id, "run_id": run.id}, indent=2))


if __name__ == "__main__":
    main()