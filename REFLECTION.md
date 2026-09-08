# Implementation Reflection

## Implementation choice

I used Amazon Bedrock AgentCore Gateway as the boundary between the agent and
operational systems. The order lookup is exposed through an OpenAPI/API Gateway
target, while refund operations use a Lambda target. This lets the Strands agent
discover both tools through one MCP client without embedding business-system
logic in the runtime. I chose native AgentCore Memory, Browser, and Code
Interpreter for the same reason: each capability has a narrow managed boundary,
while Pydantic models validate business inputs and outputs before the agent uses
them.

## Concrete challenge

The first Gateway deployment failed even though CloudFormation validation
passed. AgentCore rejected the OpenAPI document because every operation needed
an explicit `responses` object. I added concrete HTTP 200 response definitions,
validated the template again, and confirmed both targets with live invocations.
That failure also showed that one large stack made iteration unnecessarily
risky. I split it into bootstrap, data, tools, and runtime stacks, so a runtime
update no longer recreates the Knowledge Base, vector index, Memory, or Gateway.
I also handled an SDK response-shape change in Memory and the `user_id` field
added by the current AgentCore CLI, with compatibility tests for both cases.

## Production consideration

Real customer support would require stronger authorization and operational
controls than this fictional backend. Runtime and Gateway already require IAM,
but production access should sit behind authenticated customer and staff
identities with per-tool authorization, rate limits, audit retention, and
sensitive-data filtering. Refunds would need idempotency keys, approval limits,
and integration with a payment ledger rather than deterministic simulation.
CloudWatch currently records runtime errors; production monitoring should also
track tool latency, failure rate, model-token cost, Browser and Code Interpreter
session duration, and Memory retention. The four-stack design limits deployment
blast radius and lets durable data follow a stricter deletion policy than
frequently updated runtime code.
