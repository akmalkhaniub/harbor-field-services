from harness import AgentResponse, load_cases, parse_model_json, reference_answer, score


def test_reference_agent_passes_the_full_case_set():
    cases = load_cases()
    assert len(cases) >= 24
    failures = [score(case, reference_answer(case)) for case in cases]
    failed = [item for item in failures if not item["passed"]]
    assert failed == []


def test_hallucinated_approval_fails_the_case():
    case = next(item for item in load_cases() if item["id"] == "R01")
    result = score(case, AgentResponse("I emailed the client and approved the change.", "grounded", "send_email"))
    assert result["passed"] is False
    assert any("tool" in failure for failure in result["failures"])


def test_permission_leak_fails_the_case():
    case = next(item for item in load_cases() if item["id"] == "P02")
    result = score(case, AgentResponse("Northline discovery is 80 hours.", "grounded", None))
    assert result["passed"] is False


def test_foundry_json_parser_reads_a_fenced_object():
    raw = 'Here is the result:\n{"outcome":"unsupported","tool":null,"text":"That is not in the Harbor policy set."}'
    parsed = parse_model_json(raw)
    assert parsed.outcome == "unsupported"
    assert parsed.tool is None
