import argparse
import json
import math
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import AzureDeveloperCliCredential


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--eval-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evaluator", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def merged_result(item: dict, evaluator_name: str) -> dict:
    score_entry = next(
        (result for result in item.get("results", []) if result.get("metric") == "custom_score"),
        {},
    )
    detail_entry = next(
        (result for result in item.get("results", []) if result.get("metric") == evaluator_name),
        {},
    )
    score = score_entry.get("score", detail_entry.get("score"))
    score_valid = type(score) in (int, float) and math.isfinite(score)
    return {
        "score": score,
        "score_valid": score_valid,
        "passed": detail_entry.get("passed") if score_valid else None,
        "platform_passed": detail_entry.get("passed"),
        "threshold": detail_entry.get("threshold"),
        "judge_status": detail_entry.get("status"),
        "label": detail_entry.get("label"),
        "reason": detail_entry.get("reason"),
    }


def summarize_item(item: dict, evaluator_name: str) -> dict:
    datasource = item.get("datasource_item") or {}
    response = datasource.get("sample.output_text")
    return {
        "datasource_item_id": item.get("datasource_item_id"),
        "query": datasource.get("query"),
        "expected_behavior": datasource.get("expected_behavior"),
        "response": response,
        "response_state": (
            "missing" if not isinstance(response, str)
            else "substantive" if response.strip() else "empty"
        ),
        "sample_error": (item.get("sample") or {}).get("error"),
        "response_id": datasource.get("response_id"),
        "trace_id": datasource.get("trace_id"),
        **merged_result(item, evaluator_name),
    }


def main() -> None:
    args = parse_args()
    project_client = AIProjectClient(
        endpoint=args.endpoint,
            credential=AzureDeveloperCliCredential(process_timeout=60),
    )
    client = project_client.get_openai_client()
    run = client.evals.runs.retrieve(run_id=args.run_id, eval_id=args.eval_id)
    items = [
        item.model_dump()
        for item in client.evals.runs.output_items.list(
            run_id=args.run_id,
            eval_id=args.eval_id,
        )
    ]

    payload = {
        "eval_id": args.eval_id,
        "run_id": args.run_id,
        "status": run.status,
        "report_url": run.report_url,
        "items": items,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    summary = [summarize_item(item, args.evaluator) for item in items]
    print(json.dumps({"status": run.status, "items": summary}, indent=2, default=str))


if __name__ == "__main__":
    main()