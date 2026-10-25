import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHIPPED = ROOT / "power-platform" / "flows" / "scope-change-approval.flow.json"
VENDOR = ROOT / "power-platform" / "flows" / "vendor-intake.flow.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_shipped_flow_separates_validation_approval_and_failure():
    flow = _load(SHIPPED)
    actions = flow["definition"]["actions"]
    assert actions["Catch"]["runAfter"]["Try"] == ["FAILED", "TIMED_OUT"]
    valid = json.dumps(actions["Try"]["actions"]["Is_valid"]["actions"])
    invalid = json.dumps(actions["Try"]["actions"]["Is_valid"]["else"]["actions"])
    assert "Start_and_wait_for_an_approval" in valid
    assert "Lookup_existing" in valid
    assert "Get_rate" in valid
    assert "Start_and_wait_for_an_approval" not in invalid
    assert "Record_validation_failure" in invalid
    assert "contoso.sharepoint.com" not in json.dumps(flow)
    assert flow["definition"]["actions"]["Try"]["actions"]["Is_valid"]["actions"]["Needs_approval"]["actions"]["Start_and_wait_for_an_approval"]["limit"]["timeout"] == "P3D"


def test_vendor_flow_is_the_pattern_the_review_rejects():
    raw = VENDOR.read_text(encoding="utf-8")
    flow = json.loads(raw)
    assert "contoso.sharepoint.com" in raw
    assert "Catch" not in flow["definition"]["actions"]
    assert "Lookup_existing" not in json.dumps(flow)
    assert flow["definition"]["actions"]["Start_and_wait_for_an_approval"]["type"] == "OpenApiConnectionWebhook"
