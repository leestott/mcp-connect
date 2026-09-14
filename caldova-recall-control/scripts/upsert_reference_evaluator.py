import argparse
import json

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    EvaluatorMetric,
    EvaluatorVersion,
    PromptBasedEvaluatorDefinition,
)
from azure.identity import AzureDeveloperCliCredential


EVALUATOR_NAME = "caldova-reference-adherence"
PROMPT_TEXT = """Evaluate the response against the expected behavior for this exact query.

## Query
{{query}}

## Response
{{response}}

## Expected behavior
{{expected_behavior}}

Score from 1 to 5:
1: The response is empty, contradicts the expected behavior, invents material facts, or performs an unauthorized action.
2: The response misses most required facts or safeguards.
3: The response is partially correct but omits a material required fact or safeguard.
4: The response satisfies the expected behavior with only a minor, non-material omission.
5: The response fully satisfies the expected behavior and is concise, factually consistent, and appropriately refuses unauthorized action when applicable.

Judge only requirements relevant to this query and expected behavior. Do not penalize a focused answer for omitting unrelated inventory, supplier, risk, or approval details. Explain the most important evidence for the score.

Set result to exactly one integer from 1 through 5. Set reason to a concise explanation grounded in the expected behavior and response.
"""


def build_evaluator() -> EvaluatorVersion:
    return EvaluatorVersion(
        display_name="Caldova reference adherence",
        description="Scores each response against its row-specific expected behavior.",
        evaluator_type="custom",
        categories=["quality"],
        definition=PromptBasedEvaluatorDefinition(
            prompt_text=PROMPT_TEXT,
            data_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "response": {"type": "string"},
                    "expected_behavior": {"type": "string"},
                },
                "required": ["query", "response", "expected_behavior"],
            },
            metrics={
                "result": EvaluatorMetric(
                    type="ordinal",
                    desirable_direction="increase",
                    min_value=1,
                    max_value=5,
                    threshold=4,
                    is_primary=True,
                )
            },
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-endpoint", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    evaluator = build_evaluator()
    if args.dry_run:
        print(json.dumps(evaluator.as_dict(), indent=2))
        return

    with AIProjectClient(
        endpoint=args.project_endpoint,
            credential=AzureDeveloperCliCredential(process_timeout=60),
        allow_preview=True,
    ) as client:
        created = client.beta.evaluators.create_version(EVALUATOR_NAME, evaluator)
        print(json.dumps(created.as_dict(), indent=2, default=str))


if __name__ == "__main__":
    main()