# MircoVerse — AWS Infrastructure (Phase-2 platform)

> **Status: write-first, not yet applied.** This Terraform encodes the production platform
> described in [`Architecture.md`](../Architecture.md). It is the 1000-agent target, **not** a
> seed-run requirement — the 25-agent science run is local (Postgres in Docker, FastAPI). None of
> this is testable before you create an AWS account and run `terraform plan`. Every resource here
> maps to a load-bearing requirement in `Architecture.md`; nothing speculative.

## What this provisions (and why — Architecture.md §AWS Architecture)

| Resource | Architecture.md rationale |
|---|---|
| **API Gateway** (HTTP API) | Agent routes (per-key auth, throttling, validation) + admin routes (IAM/SigV4). Cheaper than ALB at this request volume (§Why No ALB). |
| **Lambda** ×4 (registration, state-reader, action-receiver, tick-resolver steps) | The HTTP contract + tick resolution. The server is a game API, not an agent runner. |
| **Step Functions (Standard)** | The 10-step tick resolver. Standard, not Express — full execution history per tick for debugging (§Step Functions: Standard Workflow). |
| **Aurora Serverless v2 + RDS Proxy** | Relational schema with FKs + JOINs for analytics; bursty load; RDS Proxy prevents connection exhaustion under concurrent Lambdas (§Why Aurora). |
| **EventBridge Scheduler** | The 30s tick clock; enabled/disabled by lifecycle admin endpoints. |
| **Provisioned concurrency on the Step-8 fan-out ONLY** | Load-test-gated hedge (Architecture.md §Lambda Provisioned Concurrency) — wired but defaulted to 0; raise only if the p99 graph shows a cold-start tail. |
| **VPC + subnets + SGs** | Aurora/RDS Proxy/Lambda all in-VPC. |
| **Secrets Manager** | DB credentials; Lambda reads at init. |

## Layout
```
infra/
├── README.md            ← this file
├── versions.tf          ← provider + backend pins
├── variables.tf         ← all knobs (region, agent scale, tick interval, provisioned-conc)
├── network.tf           ← VPC, subnets, security groups
├── database.tf          ← Aurora Serverless v2 + RDS Proxy + Secrets Manager
├── lambda.tf            ← the function definitions (+ packaging note)
├── stepfunctions.tf     ← the tick-resolution state machine (Steps 0-9)
├── apigateway.tf        ← HTTP API + routes + authorizers
├── scheduler.tf         ← EventBridge Scheduler tick clock
├── outputs.tf           ← API URL, DB endpoint, etc.
└── README-DEPLOY.md     ← step-by-step once you have an account
```

## NOT deployable yet — read `README-DEPLOY.md` before touching `terraform apply`.
The Lambda packaging (`lambda.tf`) references zips that a build step must produce from the
`mircoverse/` package; that build step is documented but intentionally not run here.
