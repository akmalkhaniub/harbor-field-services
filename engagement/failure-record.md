# Failure record

Fill this in after the flow runs in Dev. Keep the run id. Do not paste secrets.

| Case | What you did | Run id | What the user saw | How you recovered |
|---|---|---|---|---|
| Invalid payload | Submit hours below 4 | | Failed run, no approval | Corrected the row and resubmitted the same correlation id |
| Duplicate | Submit the same correlation id again | | Second run did not open an approval | None. Replay is the success path |
| Connector timeout | Point `hf_RateApiUrl` at a closed port in Dev only | | Dead letter and a Teams message with the correlation id | Restored the URL and resubmitted that row |
| Approval expiry | Leave the approval until it times out | | Request stays pending | Coordinator records the decision |
| Recovery | Resubmit one dead-letter row | | One quote id, one approval | Confirmed the quote `replayed` flag |

| Eval run | Passed | Cost USD | Notes |
|---|---|---|---|
| Offline reference | 30/30 | 0 | `python -m pytest` |
| Foundry | | | `services/eval-harness/foundry_runner.py` |
