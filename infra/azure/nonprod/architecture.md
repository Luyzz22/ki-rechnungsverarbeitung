# FlowCheck Azure Non-Production Architecture

## Transitional Non-Production Path

```text
FlowCheck FastAPI on Hetzner
        |
Azure Arc system-assigned Managed Identity
        |
Azure OpenAI + Azure Document Intelligence
        |
Default Deny network rules with exact static Hetzner egress CIDR allowlist
```

The transitional mode keeps FlowCheck running on Hetzner while preparing Azure
OpenAI and Azure Document Intelligence for governed non-production validation.
It is not the production target and must not be described as equivalent to
Private Endpoint isolation.

## Production Target

```text
Azure Worker or Azure Container App in a VNet
        |
Private Endpoints
        |
Azure OpenAI + Azure Document Intelligence
```

For production, the application worker should run inside Azure networking, or
Hetzner must connect through an explicitly approved private connectivity design.
This repository only prepares the parameter contracts for that target state.

## Identity

The non-production bridge uses Azure Arc with a system-assigned managed identity.
Role assignments are scoped to the Azure AI service accounts and receive the
managed identity principal ID as a deployment parameter.

No developer identity, Azure CLI credential, service principal credential, or
client secret is part of this IaC contract.

## Network Controls

`TRANSITIONAL_STATIC_EGRESS` keeps public network access enabled only for the
non-production transition and requires Azure AI Services network ACLs with
`DefaultAction = Deny` plus exact static Hetzner egress CIDRs.

`PRIVATE_VNET_TARGET` disables public network access and carries parameter
contracts for Private Endpoint, subnet, and private DNS resources. Those
parameters are mandatory deployment inputs for the target contract. The
contract does not claim Hetzner can reach those private endpoints without VPN
or an Azure-hosted worker.

## Governance Boundary

Code and IaC can enforce logical constraints such as parameter presence,
Default Deny intent, model pinning, and RBAC shape. Region, ZDR, no-training
status, DPA terms, network isolation, and actual private routing require
separate provider, procurement, and infrastructure evidence.
