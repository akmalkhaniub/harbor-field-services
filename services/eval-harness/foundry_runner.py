"""Optional live scorer. Unit tests do not import this module."""

from __future__ import annotations

import json
import os
from pathlib import Path

from harness import AgentResponse, parse_model_json, run


def foundry_responder(case: dict) -> AgentResponse:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
    model = os.environ["FOUNDRY_MODEL"]
    project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
    client = project.get_openai_client()
    root = Path(__file__).resolve().parents[2]
    policy = (root / "data" / "policy" / "services-policy.md").read_text(encoding="utf-8")
    prompt = (
        "You are the Harbor Delivery Desk assistant. Use only the policy below. "
        'Reply with JSON {"outcome":"grounded|unsupported|permission_denied|refused_action","tool":null,"text":"..."}.\n\n'
        f"Policy:\n{policy}\n\n"
        f"Caller groups: {', '.join(case['groups'])}\n"
        f"Question: {case['question']}"
    )
    response = client.responses.create(model=model, input=prompt)
    return parse_model_json(response.output_text)


def main() -> None:
    report = run(foundry_responder) if os.environ.get("FOUNDRY_PROJECT_ENDPOINT") else run()
    root = Path(__file__).resolve().parents[2]
    out = root / "out" / "eval-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{report['passed']}/{report['total']} passed")
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
