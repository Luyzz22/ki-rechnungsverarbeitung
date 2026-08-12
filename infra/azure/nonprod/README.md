# FlowCheck Azure Non-Production IaC

This folder contains a local, reviewable Bicep contract for the FlowCheck
non-production Azure inference transition. It is not a deployment script and it
does not contain real tenant, subscription, resource, endpoint, network, or
credential values.

## Scope

The transitional architecture is:

```text
FlowCheck FastAPI on Hetzner
        |
Azure Arc system-assigned Managed Identity
        |
Azure OpenAI + Azure Document Intelligence
        |
Azure network rules: Default Deny + exact static Hetzner egress CIDR allowlist
```

This is explicitly Non-Production-only. The production target remains an
Azure-hosted worker in a VNet with Private Endpoints for Azure OpenAI and Azure
Document Intelligence.

## Files

- `main.bicep`: parameterized top-level contract.
- `modules/ai-services.bicep`: Azure OpenAI and Document Intelligence accounts.
- `modules/network-transition.bicep`: static-egress transition and private
  target network contracts.
- `modules/rbac.bicep`: role assignments for the Azure Arc managed identity.
- `nonprod.example.bicepparam`: placeholder-only example parameters.
- `architecture.md`: architecture notes and transition boundaries.

## Required local validation

Run without Azure access:

```bash
./.venv/bin/python scripts/validate_azure_nonprod_plan.py
```

The validator performs static checks only. It does not call Azure, instantiate
provider clients, fetch credentials, or inspect subscriptions.

## Before any future deployment

- Replace placeholders in a private, non-committed parameter file.
- Verify final Azure built-in inference role definition IDs in Azure Portal or
  via Azure CLI.
- Confirm Microsoft Entra RBAC for the Azure Arc system-assigned managed
  identity.
- Confirm the Hetzner egress IP is static and approved for non-production use.
- Confirm no rollback path enables Direct OpenAI, Anthropic, or Gemini.
