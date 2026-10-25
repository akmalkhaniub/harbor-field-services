# Harbor Field Services

Two systems for one fictional 40-person project firm.

**Delivery Desk** answers policy questions in Teams and turns a scope change into a validated, idempotent quote that waits for a person. **Control Plane** is the Foundry evaluation path, the Azure AI gateway, and the release process around that desk.

The commercial rules live in one place: `services/rate-api/ratecard/policy.py`. The policy page, the eval set, and the quote math all use those values.

## Run the tests

```powershell
python -m pytest
```

The suite covers quotes, account permissions, idempotency, the MCP tool list, the 25-case eval set, the shipped flow's failure path, and the rejected vendor flow. No Azure subscription is required.

## What is already in the repo

| Piece | Path |
| --- | --- |
| Rate rules, quotes, MCP tools | `services/rate-api` |
| Offline eval harness and Foundry prompt | `services/eval-harness` |
| Flex Consumption, Key Vault, Monitor, optional Foundry, Search, SQL, API Management | `infra/main.bicep` |
| Gateway policy: managed identity, model routing, token limit | `infra/policies/foundry-gateway.xml` |
| Permission-filtered search index | `infra/search/harbor-knowledge.index.json` |
| Scope-change flow and the rejected vendor flow | `power-platform/flows` |
| Custom connector | `power-platform/connectors/harbor-rate-api.swagger.json` |
| Deployment settings template | `power-platform/settings` |
| GitHub Actions for tests, Azure, and Power Platform | `.github/workflows` |
| Operating review model and report | `bi/HarborOperatingReview.pbip` |
| Entra group baseline | `platform/entra-baseline.ps1` |

Foundry, Search, API Management, and SQL are off unless you pass `deployFoundry`, `deploySearch`, `deployApim`, or `deploySql`. A default deployment creates the function, Key Vault, log workspace, and a USD 50 budget alert.

## What still happens in a tenant

Copilot Studio, SharePoint permission breaks, Dataverse tables, and the managed solution export are created in a Microsoft 365 developer tenant. After that export exists at `out/HarborDeliveryDesk.zip`, `deploy-solution.yml` checks it and imports it with federated credentials. No client secret is stored in GitHub.

The Teams agent uses the same policy and the same two tools as `POST /api/mcp`: `get_rate` and `create_quote`. It has no send-mail tool. The cloud flow owns approval.

## Local function

Copy `services/rate-api/local.settings.json.example` to `local.settings.json` and start the Functions host from `services/rate-api`. `HARBOR_ALLOW_DIRECT=true` is for that local host only. The Bicep app setting leaves it false, and the API then requires the `x-harbor-gateway: apim` header that the gateway policy sets.

## Cost

Turn model deployments off when the eval week ends. API Management Basic v2 and Azure AI Search Basic are the expensive switches, which is why they default to off.
