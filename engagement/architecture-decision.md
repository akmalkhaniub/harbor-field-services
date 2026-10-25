# Decision: keep the channel in Copilot Studio

People who ask the questions already work in Teams. Copilot Studio can reach SharePoint with the user's permissions and can call the rate tool.

Microsoft Foundry runs the same 25 cases and holds the model deployment behind API Management. Move a live answer path to Foundry when the eval set shows the SharePoint answers failing the grounding cases, or when a client needs a channel outside Microsoft 365.

The rate API stays a small Python function either way. The approval flow stays in Power Automate either way.
