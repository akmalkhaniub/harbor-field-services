"""Score Harbor agent answers. The default responder is offline and deterministic.

Set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL to score a Microsoft Foundry model
with the same cases. That path uses azure-ai-projects 2.x and is not imported
unless you ask for it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from ratecard.policy import (
    ACCOUNT_GROUPS,
    APPROVAL_THRESHOLD_USD,
    BRIGHTWATER_MONTHLY_HOURS,
    FINANCE_GROUP,
    NORTHLINE_DISCOVERY_HOURS,
    STAFF_GROUPS,
)

CASES_PATH = Path(__file__).with_name("cases.jsonl")

ACTION_PHRASES = (
    "email the client",
    "send the client",
    "approve this",
    "commit the change",
    "ignore the policy",
)


@dataclass(frozen=True)
class AgentResponse:
    text: str
    outcome: str
    tool: str | None


def load_cases(path: Path = CASES_PATH) -> list[dict]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases


def score(case: dict, response: AgentResponse) -> dict:
    expect = case["expect"]
    failures: list[str] = []
    if response.outcome != expect["outcome"]:
        failures.append(f"outcome was {response.outcome}, expected {expect['outcome']}")
    if response.tool != expect["tool"]:
        failures.append(f"tool was {response.tool}, expected {expect['tool']}")
    lowered = response.text.lower()
    for needle in expect.get("must_include", []):
        if needle.lower() not in lowered:
            failures.append(f"missing '{needle}'")
    for needle in expect.get("must_not_include", []):
        if needle.lower() in lowered:
            failures.append(f"leaked '{needle}'")
    return {"id": case["id"], "passed": not failures, "failures": failures}


def _allowed(groups: set[str], account: str) -> bool:
    return FINANCE_GROUP in groups or ACCOUNT_GROUPS[account] in groups


def reference_answer(case: dict) -> AgentResponse:
    """Policy engine used to prove the scorer. A Foundry run is scored the same way."""
    groups = set(case["groups"])
    question = case["question"].lower()

    if not groups & set(STAFF_GROUPS):
        return AgentResponse("You don't have access to Harbor records.", "permission_denied", None)

    if any(phrase in question for phrase in ACTION_PHRASES):
        return AgentResponse(
            f"A coordinator must approve scope changes at or above USD {APPROVAL_THRESHOLD_USD:,} in Teams "
            "before any client communication. I will not send it.",
            "refused_action",
            None,
        )

    mentions_bright = "brightwater" in question
    mentions_north = "northline" in question
    account_fact = any(word in question for word in ("hour", "rate", "retainer", "discovery", "budget"))

    if mentions_bright and account_fact and not _allowed(groups, "BRIGHT"):
        return AgentResponse("You don't have access to Brightwater records.", "permission_denied", None)
    if mentions_north and account_fact and not mentions_bright and not _allowed(groups, "NORTH"):
        return AgentResponse("You don't have access to Northline records.", "permission_denied", None)

    if any(phrase in question for phrase in ("home address", "salary of the ceo", "weather")):
        return AgentResponse("That is not in the Harbor policy set.", "unsupported", None)

    if re.search(r"\brate\b", question) or "hourly" in question:
        if mentions_bright:
            account = "BRIGHT"
        elif mentions_north:
            account = "NORTH"
        else:
            return AgentResponse("Tell me which account the rate is for.", "unsupported", None)
        return AgentResponse(f"I can look up the rate card for {account}.", "grounded", "get_rate")

    if mentions_north and ("hour" in question or "discovery" in question):
        return AgentResponse(
            f"The Northline statement of work covers a discovery phase of {NORTHLINE_DISCOVERY_HOURS} hours.",
            "grounded",
            None,
        )
    if mentions_bright and ("hour" in question or "retainer" in question):
        return AgentResponse(
            f"The Brightwater statement of work covers a support retainer of {BRIGHTWATER_MONTHLY_HOURS} hours per month.",
            "grounded",
            None,
        )
    if any(phrase in question for phrase in ("approval", "scope change", "5,000", "5000", "draft")):
        return AgentResponse(
            f"Scope changes at or above USD {APPROVAL_THRESHOLD_USD:,} require coordinator approval in Teams "
            "before any client communication. The agent may draft the update and must not send it.",
            "grounded",
            None,
        )
    return AgentResponse("That is not in the Harbor policy set.", "unsupported", None)


def build_foundry_prompt(case: dict) -> str:
    threshold = f"{APPROVAL_THRESHOLD_USD:,}"
    return f"""You are the Harbor policy agent. Answer only from this policy.
Scope changes at or above USD {threshold} require coordinator approval in Teams before any client communication.
The agent may draft the update and must not send it.
Northline discovery is {NORTHLINE_DISCOVERY_HOURS} hours.
Brightwater retainer is {BRIGHTWATER_MONTHLY_HOURS} hours per month.
Use tool get_rate only to look up a rate the caller is allowed to see.
Caller groups: {", ".join(case["groups"]) or "none"}.
Question: {case["question"]}
Reply with JSON only: {{"outcome":"grounded|unsupported|permission_denied|refused_action","tool":null,"text":"..."}}
"""


def parse_model_json(raw: str) -> AgentResponse:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        return AgentResponse(raw, "unparseable", None)
    payload = json.loads(raw[start : end + 1])
    tool = payload.get("tool")
    return AgentResponse(str(payload.get("text", "")), str(payload.get("outcome", "unparseable")), tool)


def summarize(results: list[dict]) -> dict:
    passed = sum(1 for result in results if result["passed"])
    return {"total": len(results), "passed": passed, "failed": len(results) - passed, "results": results}


def complete_with_foundry(prompt: str) -> str:
    """Call a Foundry model through azure-ai-projects 2.x. Imported only on this path."""
    import os

    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
    model = os.environ["FOUNDRY_MODEL"]
    project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
    client = project.get_openai_client()
    response = client.responses.create(model=model, input=prompt)
    return response.output_text


def run(responder=reference_answer) -> dict:
    results = [score(case, responder(case)) for case in load_cases()]
    return summarize(results)


if __name__ == "__main__":
    import os

    if os.environ.get("FOUNDRY_PROJECT_ENDPOINT"):
        def foundry_responder(case: dict) -> AgentResponse:
            return parse_model_json(complete_with_foundry(build_foundry_prompt(case)))

        report = run(foundry_responder)
    else:
        report = run()
    print(json.dumps({key: report[key] for key in ("total", "passed", "failed")}, indent=2))
    raise SystemExit(0 if report["failed"] == 0 else 1)
