# Validation criteria

CircuitCare is complete when local checks pass and a bounded AWS cycle demonstrates these portal journeys:

1. The signed-in customer sees and tracks only their orders.
2. A troubleshooting answer is supported by an approved source.
3. An eligible return is proposed, confirmed, persisted, and safe to retry.
4. An expired return changes no state and explains the rule.
5. A safety issue becomes a support case that staff resolves and the customer revisits.

Negative checks cover cross-customer access, customer attempts at staff actions, duplicate and changed idempotent requests, invalid input, expired sessions, prompt injection, missing knowledge, and unavailable AWS services.

The evaluation catalog contains 30 versioned scenarios. Automated tests enforce the deterministic application invariants, while a bounded AWS smoke cycle exercises representative managed-service paths. A future scored model evaluation should require at least 90% correct task outcomes and supported citations for answerable knowledge questions; every authorization and transaction invariant remains mandatory.

## Latest bounded AWS cycle

The 2026-09-08 cycle ran the uncommitted working tree based on revision `1071497` in `us-east-1`. Local tests covered the deterministic domain and API invariants and verified the complete 30-scenario catalog structure. Live smoke checks concentrated on the cross-service paths and the high-risk authorization and transaction invariants; this was not represented as a statistically scored 30-prompt model evaluation.

All five primary journeys passed against Cognito, DynamoDB, Bedrock Knowledge Bases, AgentCore Runtime, Gateway, Memory, Browser, and Code Interpreter. Live negative checks also passed for customer isolation, expired-return rejection, changed idempotent input, prompt injection, unsupported product facts, and attempted browser transactions. Preference memory became available across sessions after the managed asynchronous extraction interval.

Live validation exposed two integration defects that local mocks did not: DynamoDB's resource client was receiving already-serialized transaction attributes, and the API admitted runtime session identifiers shorter than AgentCore's 33-character minimum. Both contracts were corrected and retested successfully.

The cycle used only fictional identities and synthetic business records. It recorded no customer data, credentials, account identifiers, or raw model transcripts in the repository. Precise cost attribution was not yet available during the short-lived cycle; execution remained within the authorized USD 25 ceiling by scope, and all project resources were removed immediately afterward. The residual audit found zero project stacks, buckets, tables, functions, APIs, roles, alarms, knowledge bases, AgentCore resources, and matching log groups. The tagging API briefly retained a stale reference to the already-deleted Cognito pool.
