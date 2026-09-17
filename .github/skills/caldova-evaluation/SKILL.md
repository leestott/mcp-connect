---
name: caldova-evaluation
description: 'Preserve and diagnose Caldova golden7 evaluation evidence. Use when: reviewing seven golden cases, empty hosted responses, nonnumeric judges, reference evaluator mapping, evaluator-generation unsupported HTTP 400, Model Router capability, or truthful evaluation reporting.'
---

# Caldova Evaluation

## Non-Negotiable Baseline

Preserve all seven [golden cases](../../../caldova-recall-control/tests/golden.jsonl), their expected behavior, and existing evaluator thresholds. Do not replace them with generated samples, omit failing cases, lower criteria, or alter the rubric to obtain a green result. Preserve the [generation configuration](../../../caldova-recall-control/src/agent-framework-workflows-responses/eval.yaml) and [rubric dimensions](../../../caldova-recall-control/src/agent-framework-workflows-responses/evaluators/caldova-golden-smoke/rubric_dimensions.json) unless a separately approved task explicitly changes them.

## Workflow

1. Identify the request: offline evidence review, evaluator generation diagnosis, or an explicitly approved new evaluation. Begin with existing sanitized artifacts and the [historical checklist](../../../caldova-recall-control/TODO.md). Historical deployments, pass counts, and traces are not current verification. Do not dump credential-bearing environment files or private response content.
2. Run the local baseline contract check below and inspect the seven rows. Confirm the expected-behavior field is retained. Compare any proposed patch against the original dataset/rubric; do not silently normalize or rewrite them.
3. Trace the reference evaluation mapping in [run_reference_eval.py](../../../caldova-recall-control/scripts/run_reference_eval.py): `item.query`, `sample.output_text`, and `item.expected_behavior` must reach the evaluator. Inspect [upsert_reference_evaluator.py](../../../caldova-recall-control/scripts/upsert_reference_evaluator.py) for rubric/version semantics, and [download_eval_results.py](../../../caldova-recall-control/scripts/download_eval_results.py) for result extraction. Reuse these scripts rather than creating another runner.
4. Separate failure classes. Empty or partial agent output is a generation/runtime failure; nonnumeric or invalid judge output is not a valid passing score; an ordinary scored failure is a quality result. Inspect each response, criterion, threshold, and correlated trace where available. Platform success or zero reported platform errors does not mean seven useful answers or seven passes.
5. For the recorded evaluator-generation failure, target resolution succeeded but the job returned HTTP 400, `The requested operation is unsupported.` Model Router support for that generation operation remains unconfirmed. Inspect existing job diagnostics and current model/API capability documentation before considering a retry. Do not conflate this with HTTP 429 throttling, local online-analysis cooldown, authentication errors, or evaluation scores. Backoff does not resolve an unsupported operation.
6. Before any separately approved cloud run, confirm the exact project endpoint, immutable agent version, judge deployment, evaluator version, supported API/operation, cost scope, and selected root azd environment. Discover these from approved configuration, not historical IDs. Changing the generation model requires explicit approval; successful evaluator generation and evaluation pass/fail are separate outcomes.
7. Report total rows, substantive versus empty outputs, pass/fail/error counts, invalid judge outputs, agent/evaluator versions, dataset identity, and available sanitized evidence references. State missing traces or unrun checks explicitly. Never claim all evaluations pass without per-item evidence from all seven unchanged cases.

## Offline Check

From the repository root in PowerShell, using the existing Python 3.13 environment:

```powershell
$Python = './caldova-recall-control/.venv/Scripts/python.exe'
if (-not (Test-Path $Python)) { throw 'Select the existing project Python 3.13 environment.' }
& $Python -m pytest caldova-recall-control/tests/test_caldova_workflow.py -k golden -q
git diff -- caldova-recall-control/tests/golden.jsonl caldova-recall-control/src/agent-framework-workflows-responses/eval.yaml caldova-recall-control/src/agent-framework-workflows-responses/evaluators
```

On macOS/Linux substitute `caldova-recall-control/.venv/bin/python`; invoke it directly in a POSIX shell. A passing dataset-contract test is not a hosted evaluation.

## Approved-Run Preparation

Do not execute these scripts as a side effect of review. Prepare arguments from approved configuration first:

| Existing script | Required inputs and side effects |
| --- | --- |
| Reference evaluator upsert | `--project-endpoint`; inspect `--dry-run` behavior first. Actual upsert changes the project evaluator catalog. |
| Reference evaluation runner | `--endpoint`, `--dataset` pointing to unchanged golden cases, `--agent-name`, `--agent-version`, `--evaluator`, explicit `--evaluator-version`, `--deployment`. Creates evaluation/run resources and invokes paid services. |
| Result downloader | `--endpoint`, `--eval-id`, `--run-id`, `--evaluator`, `--output`. Reads cloud evidence and writes a local artifact; select an ignored private evidence location. |

No automatic generation, evaluation rerun, model deployment, provisioning, spending, install, commit, or push. If installed, use the current official `microsoft-foundry` evaluation workflow after scope approval; otherwise consult [Foundry evaluation guidance](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-approach-gen-ai) and [official skill guidance](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/use-microsoft-foundry-skill). Inspect installed CLI help before proposing version-dependent syntax; do not assume a personal skill is available.