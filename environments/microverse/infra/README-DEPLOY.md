# Deploying the MircoVerse platform (once you have an AWS account)

> Do not run this for the seed run. The 25-agent science run is local. This is the 1000-agent
> platform target. Everything below is intentionally **not** executed yet.

## Prerequisites
1. An AWS account + credentials (`aws configure` or SSO).
2. Terraform ≥ 1.6.
3. The Lambda deployment package built (see step 2 below) — `terraform apply` will fail until
   `build/mircoverse_lambda.zip` exists. This is deliberate: the IaC references the real engine
   code, not a stub.

## Step 1 — Lambda handlers (one code change still required)
The IaC references handlers that the local seed run does not need:
- `mircoverse/server/lambda_handlers.py` — thin adapters mapping API Gateway proxy events to the
  same FastAPI route logic (registration, state_reader, action_receiver). Use Mangum or hand-map.
- `mircoverse/resolution/lambda_handlers.py` — `step(event)` dispatches on `event["step"]` to the
  corresponding tick-resolution stage; `fov_batch(event)` does the Step-8 batched FOV precompute.

These are the ONLY platform-specific code; they wrap the shared engine so local and platform run
identical logic. They were left out of the local build on purpose (the seed run calls
`resolution.resolve_tick` directly, no Lambda).

## Step 2 — Build the deployment package
```bash
cd <repo>
pip install -t build/pkg .            # install mircoverse + deps into build/pkg
cd build/pkg && zip -r ../mircoverse_lambda.zip . && cd ../..
```
(For psycopg/asyncpg native wheels, build on an Amazon Linux image or use a Lambda layer.)

## Step 3 — Apply
```bash
cd infra
terraform init
terraform plan      # REVIEW: ~30 resources, no provisioned concurrency (var defaults to 0)
terraform apply
```

## Step 4 — Initialize the schema
The DDL lives in `mircoverse/persistence/schema.sql` (same file the local run uses). Apply it to
Aurora once, via a one-off `migrate` invocation or a bastion:
```bash
psql "$(aurora connection string from outputs)" -f ../mircoverse/persistence/schema.sql
```

## Step 5 — Run the experiment
- `POST /api/v1/admin/simulation/start` (IAM-signed) spawns agents, initializes `world_cells`,
  creates tick 0, and **enables** the EventBridge schedule.
- The tick clock now fires; Step Functions resolves each tick.
- `POST /api/v1/admin/simulation/end` forces final snapshots and disables the schedule.

## Cost discipline (Architecture.md §Scale Demonstration)
- Provisioned concurrency stays at **0** until the load test's p99 graph shows a cold-start tail.
- The expensive part of "1000 agents" is LLM inference — and that runs participant-side, NOT here.
- Tear down with `terraform destroy` between runs; Aurora Serverless v2 scales toward its floor
  between experiments but does not auto-pause under a live tick clock.

## What is NOT here yet (honest gaps)
- Admin routes (IAM-authed) are described in Architecture.md but only the agent routes are wired in
  `apigateway.tf`. Add the admin integrations + an `aws_iam`-authorized route group before a real run.
- The agent-key Lambda authorizer points at a placeholder function; ship a dedicated authorizer
  handler that hashes the bearer token and checks `agents.api_key_hash`.
- No CloudWatch dashboards/alarms or SNS operator alerts yet (Architecture.md error-handler path
  publishes to SNS — add the topic + subscription).
