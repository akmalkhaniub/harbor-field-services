# Risks

| Risk | What we do |
|---|---|
| API Management Basic v2 cost | Flag defaults to off. The template rejects the sample `example.invalid` backend. Turn it on for a short test, then delete the instance. |
| A model deployment left running | Foundry deploys only when `foundryModelVersion` is set. Delete the deployment at the end of the eval week. |
| The agent sends mail or approves work | Those tools are absent. The flow stops at an approval. The eval set includes prompt-injection cases. |
| Cross-account answers | SharePoint inheritance plus the rate API group check plus the eval permission cases. |
| Secrets in GitHub | Azure and Power Platform workflows use federated credentials. Connection ids are GitHub environment variables, written to `out/` at deploy time. |
| Activity-monitoring employer tools | Not part of this build. Decide that separately before you accept a role that requires screenshots. |
