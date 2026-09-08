# Architecture and operations

CircuitCare separates generated language from business authority. The local FastAPI process verifies a Cognito session and derives the customer mapping from signed claims. It calls DynamoDB directly for orders, returns, cases, and audit records, and invokes AgentCore Runtime for conversational support. The browser never receives AWS credentials.

The identity stack contains an operator-seeded Cognito user pool, local public client, hosted sign-in domain, and staff group. The data stack contains the DynamoDB table, Bedrock Knowledge Base, S3 Vector index, and AgentCore Memory. The tools stack contains Lambda/API Gateway examples exposed through AgentCore Gateway. The runtime stack contains AgentCore Runtime, its endpoint, execution role, and error alarm. The bootstrap stack owns versioned deployment artifacts.

Business state uses a single DynamoDB table with customer collection records and canonical lookup records. Confirmed returns use a transaction that creates an idempotency record and customer return record together. Cases have canonical and customer-indexed records. Synthetic fixtures use a fixed scenario date, keeping expiry cases repeatable.

The application runs on `127.0.0.1`. Cognito uses authorization code with PKCE and redirects to the local API. The API stores signed identity claims in an HttpOnly, same-site session cookie and requires a separate CSRF token for changes.

The environment is designed for a bounded validation cycle. Deploy, seed, run acceptance checks, save sanitized aggregate results, and delete runtime, tools, data, bootstrap, and identity stacks. Empty and delete retained S3 versions and check service-created log groups separately.
