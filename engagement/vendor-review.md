# Vendor review: intake flow

The branch `vendor/intake` delivered `power-platform/flows/vendor-intake.flow.json`. It is not accepted.

- The SharePoint site is hardcoded to `contoso.sharepoint.com`. Environment variables exist so Dev, Test, and Prod do not share a URL.
- Approval starts for every request. Validation failure and a duplicate idempotency key must not start an approval.
- There is no Catch scope, so a connector failure has nowhere to go except a red run.
- The flow can mark the row approved and continue toward the client. Harbor records the decision and leaves the client update as a draft.

The replacement is `power-platform/flows/scope-change-approval.flow.json`. `tests/test_flows.py` locks the difference: the shipped flow catches `FAILED` and `TIMED_OUT`, and approval exists only on the valid branch.
