# Runbook

## A request fails

1. Read the Teams message in Harbor Operations. It contains the correlation id, which is the idempotency key.
2. Open the `hf_deadletter` row with that key.
3. Fix the cause. Do not submit a new key for the same business request.
4. Set the dead-letter row to reprocessed only after one successful replay of the original key.

## A release fails

1. Stop. Prod stays on the previous managed solution.
2. Re-import that previous zip with the same deployment settings file.
3. Run one valid quote and one invalid quote in Prod before calling the release done.

## Spend

The resource-group budget alerts at 80 percent of USD 50. Model deployments and API Management are the first resources to turn off. The function plan can stay.
