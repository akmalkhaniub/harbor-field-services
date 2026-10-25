import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_policy_document_matches_the_code_constants():
    from ratecard.policy import APPROVAL_THRESHOLD_USD, BRIGHTWATER_MONTHLY_HOURS, NORTHLINE_DISCOVERY_HOURS

    policy = (ROOT / "data" / "policy" / "services-policy.md").read_text(encoding="utf-8")
    assert f"{APPROVAL_THRESHOLD_USD:,}" in policy
    assert str(NORTHLINE_DISCOVERY_HOURS) in policy
    assert str(BRIGHTWATER_MONTHLY_HOURS) in policy


def test_release_workflow_uses_federated_credentials():
    workflow = (ROOT / ".github" / "workflows" / "deploy-solution.yml").read_text(encoding="utf-8")
    assert "id-token: write" in workflow
    assert "password-secret" not in workflow
    assert "client-secret" not in workflow


def test_bicep_keeps_expensive_resources_opt_in_and_disables_local_auth():
    main = (ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    assert "param deployFoundry bool = false" in main
    assert "param deployApim bool = false" in main
    assert "FlexConsumption" in main
    assert "disableLocalAuth: true" in main
    policy = (ROOT / "infra" / "policies" / "foundry-gateway.xml").read_text(encoding="utf-8")
    assert "llm-token-limit" in policy
    assert "x-harbor-gateway" in policy


def test_deployment_settings_template_has_no_live_secrets():
    template = json.loads((ROOT / "power-platform" / "settings" / "HarborDeliveryDesk.settings.template.json").read_text(encoding="utf-8"))
    assert template["EnvironmentVariables"]
    assert template["ConnectionReferences"]
    rendered = json.dumps(template)
    assert "client_secret" not in rendered.lower()
    assert "AccountKey=" not in rendered
