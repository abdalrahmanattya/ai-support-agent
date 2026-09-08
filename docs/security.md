# Security model

The browser is untrusted. The local API verifies Cognito identity and owns the AWS credential chain. The agent and all model output are untrusted for authorization and transaction decisions. DynamoDB records and deterministic domain rules are authoritative.

Customers may list only records bound to their Cognito `sub` and mapped customer ID. Staff group membership permits case review and resolution. Missing and unauthorized customer resources return the same not-found response to avoid enumeration.

Returns require a fresh eligible proposal followed by explicit confirmation. Confirmation includes an idempotency key; retries return the first result and reuse with a changed payload fails. Audit records omit tokens, prompts, and raw memory.

Knowledge retrieval provides source identifiers. Memory improves continuity but never supplies identity or authoritative facts. Code Interpreter performs bounded explanatory calculations; deterministic decimal code determines policy and monetary values. Browser use is limited to allowlisted public informational sources and must not log in or transact.

This short-lived environment omits real payment, shipment, notification, privacy-erasure, and enterprise ticketing integrations. Production use would require a formal retention policy, centralized audit retention, abuse controls, recovery objectives, operational ownership, and security review.
