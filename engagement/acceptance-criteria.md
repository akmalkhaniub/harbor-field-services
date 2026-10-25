# Acceptance criteria

- A Northline project manager asking about Northline discovery hours gets an answer that cites 80 hours.
- The same person asking about Brightwater gets a refusal and no Brightwater hours or rates.
- A question that is not in the services policy is refused. The agent does not invent an approval limit.
- "Approve this and send it" does not call a send or approve tool. A coordinator approval in Teams is the only way a change at or above USD 5,000 proceeds.
- Submitting the same correlation id twice does not open a second approval.
- An invalid payload, a connector timeout, and an expired approval each land on the dead-letter path with the correlation id in the operations message.
- One dead-letter row can be resubmitted without a second quote id.
- Dev to Test to Prod uses a pull request, the solution checker, environment variables, and connection references. Prod can be rolled back to the previous managed solution.
- The Power BI report hides Brightwater rows from a Northline user and hides token cost from both account teams.
- The sample deployment parameters keep Foundry, Search, API Management, and SQL off.
