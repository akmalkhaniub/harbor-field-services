# License and cost sheet

| Item | Needed for the demo | Leave it |
|---|---|---|
| Microsoft 365 developer tenant | Yes | Renew before it expires |
| Power Platform managed environments Dev, Test, Prod | Yes | |
| Copilot Studio trial or pay-as-you-go | Yes, for the Teams agent | Shut off unused agents |
| Microsoft 365 Copilot user licenses | No | Adoption note only |
| Key Vault, Log Analytics, Function Flex Consumption | Yes, small | |
| Foundry model deployment | Only during the eval week | Delete the deployment after |
| Azure AI Search basic | Only while indexing the three policy files | Delete after |
| API Management Basic v2 | Only while proving token limits | Delete after. This is the costly line |
| Azure SQL Basic | Only if you want the quote table off the in-memory store | |
| Power BI | One workspace for the operating report | |

The resource-group budget in `infra/main.bicep` is the alarm. The sample amount is 50 USD a month. Change `budgetAmount` before you turn on API Management.
