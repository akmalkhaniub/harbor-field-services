# Delivery Desk solution

Create a publisher `Harbor` with prefix `hf`, then an unmanaged solution `HarborDeliveryDesk` in Dev.

## Tables

| Table | Columns that matter |
|---|---|
| Account | Account code, name |
| Project | Account, name |
| Service request | Account, role, hours, amount, correlation id, status, requested by |
| Approval decision | Request, outcome, decided by, decided at |
| Agent trace | Request, correlation id, tool name, grounded |

Unique key on Service request correlation id. That is the idempotency check the flow looks up before it opens an approval.

SharePoint library `Engagements`, with folders Northline and Brightwater. Break inheritance. `hf-acct-north` reads Northline. `hf-acct-bright` reads Brightwater. `hf-finance` reads both. Copy in `data/policy`.

## Agent

Copilot Studio, generative orchestration on, published to Teams.

- Knowledge: the Engagements library.
- Tools: `get_rate` and `create_quote` from `connectors/harbor-rate-api.swagger.json`, or the MCP route `POST /api/mcp` on the same Function.
- Do not add a tool that sends mail or completes an approval. The flow drafts and a person sends.

Use `flows/scope-change-approval.flow.json` as the code-view starting point for the cloud flow. Connection references and `hf_RateApiUrl` come from `settings/HarborDeliveryDesk.settings.template.json`. The GitHub workflow fills that template from environment variables at import time.

## Release

Dev stays unmanaged. Commit with Dataverse Git integration into `power-platform/src` so the file `power-platform/src/solutions/HarborDeliveryDesk/solution.yml` exists. Test and Prod receive the managed solution from `.github/workflows/deploy-solution.yml`.

The workflow authenticates with GitHub OIDC and an Entra federated credential. It does not store a client secret. The app registration needs the Dataverse user_impersonation permission and an application user on each environment.
