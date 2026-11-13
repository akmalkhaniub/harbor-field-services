# Google Cloud Professional Agentic Architect: Production Improvement Plan
## Repository: harbor-field-services
**Audit Date:** November 6, 2026  
**Target Standard:** Google Cloud Professional Agentic Architect (Domain 2: Low-Code/Connectors & Domain 5: Security Governance)

---

### Current Assessment
An enterprise commercial quoting and policy platform combining a Microsoft Copilot Studio delivery desk, Power Platform Custom Connectors (`harbor-rate-api.swagger.json`), and Power Automate approval flows with an Azure Functions MCP rate engine behind APIM token-limiting policies.

### Critical Gaps
1. **Unclean Git Working Tree:** Contains an untracked `uv.lock` file in the repository root.
2. **Missing Google Cloud Agent Gateway Configuration:** Relies strictly on Azure APIM XML policies for token quotas rather than providing a portable or GCP-compatible Agent Gateway policy definition.
3. **MCP Server Containerization:** The MCP rate engine is configured as an Azure Function; needs a standard containerized Cloud Run entrypoint for cross-cloud deployment.

---

### Actionable Implementation Steps

#### 1. Clean Git Working Tree
Commit the untracked dependency lockfile:
```bash
git add uv.lock
git commit -m "chore: track uv.lock for reproducible builds"
```

#### 2. Provide Google Cloud Agent Gateway Policy Definition
Author a companion policy (`config/agent-gateway-policy.yaml`) demonstrating how the rate-limiting and token quotas are enforced in Google Cloud:
```yaml
apiVersion: gateway.agent.google/v1
kind: AgentPolicy
metadata:
  name: harbor-rate-limits
spec:
  rateLimits:
    - target: "/rate-engine/*"
      maxRequestsPerMinute: 60
      maxTokensPerSession: 10000
```

#### 3. Standardize Dockerfile for Cloud Run Portability
Ensure `packages/rate-engine` can be deployed identically to Google Cloud Run via a lightweight Docker container exposing HTTP/SSE endpoints.
