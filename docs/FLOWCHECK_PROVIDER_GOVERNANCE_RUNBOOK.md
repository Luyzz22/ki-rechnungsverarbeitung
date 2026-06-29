# FlowCheck+ Provider Governance Runbook

## Scope

This runbook describes the operational approval process for regional cloud
processing in FlowCheck Core. It does not claim that region, retention,
no-training, DPA/AVV, or private networking are proven by application code
alone.

## Provider Approval Process

Before a provider deployment is approved for `EU_REGIONAL_CLOUD`, the following
evidence must exist as internal reference IDs:

- AVV/DPA review.
- Subprocessor review.
- Region and endpoint evidence.
- Model or deployment pinning evidence.
- Retention evidence.
- No-training evidence.
- Approval by the accountable owner, DSB/privacy function, and engineering.

The application stores only reference IDs such as
`RETENTION-EVIDENCE-001` or `NO-TRAINING-EVIDENCE-001`. It must not store
contract contents, tenant IDs, subscription IDs, credentials, or private network
details in provider policy configuration.

## Infrastructure Check

Network egress control is outside the Python application and must be enforced
through firewall, proxy, cloud networking controls, or equivalent operational
controls.

The application enforces a logical endpoint host allowlist. This does not
technically prevent all other network egress by itself. Private Endpoint,
default-deny egress, or a documented static Hetzner egress IP allowlist must be
verified by infrastructure and operations before production activation.

## Activation Process

1. Deploy Azure OpenAI and Azure Document Intelligence resources in the approved
   non-production environment.
2. Configure Microsoft Entra RBAC for the runtime identity.
3. Run a non-production integration test against isolated resources.
4. Review `FLOWCHECK_PROVIDER_DEPLOYMENT_CONFIG`,
   `FLOWCHECK_PROVIDER_ENDPOINT_HOST_ALLOWLIST`, Azure endpoint allowlists, and
   model/deployment pins.
5. Attach internal evidence references for retention and no-training.
6. Enable a canary tenant.
7. Monitor policy decisions, provider errors, and latency using PII-free logs.
8. Roll back by disabling regional cloud enforcement or the provider deployment
   policy. Do not roll back to Direct OpenAI, Anthropic, or Gemini for
   `EU_REGIONAL_CLOUD`.

## Kanzlei Mode

`PROFESSIONAL_SECRECY` is not the FlowCheck Core default. It is reserved for a
future Kanzlei or tax-advisor tier.

A later Kanzlei tenant should use a KanzleiAI hybrid engine. FlowCheck Core must
not grow a second local redaction stack for this mode in this repository.
