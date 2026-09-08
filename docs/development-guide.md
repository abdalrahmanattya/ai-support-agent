# Development and AWS validation

Run `./scripts/build.sh` from a clean checkout. It installs locked Python and Node dependencies, builds Python 3.13 ARM64 archives, and produces the web application.

For a live cycle, configure temporary AWS credentials in `us-east-1`, set optional expected account and role guards, and run `scripts/preflight.sh`. Review projected services before running `scripts/deploy.sh`. The deployment writes identifiers to ignored `.evidence` files.

Create demo records after deployment:

```bash
.venv/bin/python scripts/seed.py --user-pool-id <UserPoolId> --table-name <BusinessTableName>
```

The password is read from a hidden prompt or `CIRCUITCARE_SEED_PASSWORD` and is never written to the repository. Fill `.env.local` from stack outputs, generate a random `SESSION_SECRET`, rebuild, and run `scripts/dev.sh`.

Run the five browser journeys and the live evaluation manifest in `evals/scenarios.json`. Capture only sanitized aggregate results tied to the tested commit. Never publish tokens, account IDs, runtime ARNs, customer memory, raw sensitive prompts, or credentials.

Delete stacks in this order: runtime, tools, data, bootstrap, identity. Empty and delete the retained versioned artifact bucket after confirming its artifacts are no longer needed. Remove matching service-created log groups and audit project-tagged resources.
