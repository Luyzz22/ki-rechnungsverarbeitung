# FlowCheck+ Azure Adapter Design

## Status

Azure OpenAI EU and Azure Document Intelligence EU are implemented as technical
provider adapters, but they are disabled by default:

```bash
FLOWCHECK_AZURE_ADAPTERS_ENABLED=false
FLOWCHECK_AZURE_AUTH_MODE=entra
FLOWCHECK_AZURE_IDENTITY_MODE=managed_identity
FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS=false
FLOWCHECK_AZURE_ENDPOINT_HOST_ALLOWLIST=
```

The adapters do not create Azure resources, do not set credentials, and do not
switch existing standard invoice flows to Azure automatically.

## Providers

- `AZURE_OPENAI_EU` handles guarded text/chat inference through Azure OpenAI.
- `AZURE_DOCUMENT_INTELLIGENCE_EU` handles guarded invoice document analysis
  through Azure Document Intelligence `prebuilt-invoice`.

Both adapters call the central inference policy guard before any provider
request. Policy-side allow is not the same as technical availability: adapters
must also be explicitly enabled and validly configured.

## Policy Routing

- `STANDARD` keeps existing direct provider behavior.
- `PROFESSIONAL_SECRECY` may use Azure OpenAI EU for text inference and Azure
  Document Intelligence EU for invoice document analysis.
- `SOVEREIGN` blocks Azure and remains reserved for local providers only.

On Azure configuration, authentication, or request failure, the adapters return
controlled PII-free error codes and never fall back to OpenAI Direct, Anthropic
Direct, or Gemini Direct.

## Configuration Boundaries

Configuration is server-side only. Endpoints must use HTTPS, must not contain
userinfo, query strings, fragments, or IP addresses, and must match
`FLOWCHECK_AZURE_ENDPOINT_HOST_ALLOWLIST`. The allowlist is empty by default,
which keeps adapters unavailable until infrastructure is explicitly configured.

Authentication is Entra-only. Production uses `ManagedIdentityCredential` only.
`DefaultAzureCredential` is allowed only for local development/tests when
`FLOWCHECK_AZURE_ALLOW_DEVELOPER_CREDENTIALS=true` and never in production. No
Azure API-key production path is introduced.

Code alone does not prove that Azure resources are in an EU region, that private
networking is active, or that Hetzner egress is restricted. Those controls must
be verified operationally before production activation.

## Productive Prerequisites

- Azure resource deployment for Azure OpenAI and Azure Document Intelligence.
- Microsoft Entra RBAC for the runtime identity.
- Azure Arc or an Azure-based worker with Managed Identity.
- Endpoint and region allowlist.
- Network default deny.
- Private Endpoint or clearly documented static Hetzner egress IP allowlist.
- Key Vault only for technical exception cases, not as standard authentication.
- Integration test against an isolated non-production Azure resource.
- Operating runbook and incident runbook.
