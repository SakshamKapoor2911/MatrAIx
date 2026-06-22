# Lambda functions — the HTTP contract + the Step Functions tick-resolution steps.
# Architecture.md §Lambda Functions. The server is a GAME API, not an agent runner:
# it accepts action intents, resolves ticks, fans out state. It NEVER calls the agent.
#
# PACKAGING NOTE (why this isn't apply-able yet): each function ships the `mircoverse/`
# package zipped with its deps. A build step (see README-DEPLOY.md) produces
# build/<fn>.zip from the same code the local seed run uses — the handler is a thin
# adapter over the shared engine, so local and platform run identical logic. Until that
# build runs, `filename` points at a placeholder and `terraform apply` will fail by design.

locals {
  lambda_zip = "${path.module}/build/mircoverse_lambda.zip" # produced by the build step
  runtime    = "python3.12"

  common_env = {
    DB_PROXY_ENDPOINT = aws_db_proxy.main.endpoint
    DB_SECRET_ARN     = aws_secretsmanager_secret.db.arn
    DB_NAME           = "mircoverse"
  }
}

# ── Execution role shared by the API + step Lambdas ──────────────────────────
resource "aws_iam_role" "lambda" {
  name = "${var.project}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_inline" {
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.db.arn]
      },
      {
        # Reflection path only — Bedrock embeddings for the cosine tripwire
        # (Architecture.md: operator-borne, off the tick-resolution critical path).
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = ["*"]
      },
      {
        Effect   = "Allow"
        Action   = ["states:StartExecution"]
        Resource = [aws_sfn_state_machine.tick.arn]
      }
    ]
  })
}

# Reusable function factory via a map. handler = module:fn in the mircoverse package.
locals {
  functions = {
    registration   = { handler = "mircoverse.server.lambda_handlers.registration",   timeout = 10, memory = 256 }
    state_reader    = { handler = "mircoverse.server.lambda_handlers.state_reader",    timeout = 10, memory = 256 }
    action_receiver = { handler = "mircoverse.server.lambda_handlers.action_receiver", timeout = 10, memory = 256 }
    # Tick-resolution steps (Step Functions invokes these). One deployable, many handlers.
    tick_step       = { handler = "mircoverse.resolution.lambda_handlers.step",        timeout = 120, memory = 1024 }
    fov_precompute  = { handler = "mircoverse.resolution.lambda_handlers.fov_batch",   timeout = 120, memory = 1024 }
  }
}

resource "aws_lambda_function" "fn" {
  for_each = local.functions

  function_name = "${var.project}-${each.key}"
  role          = aws_iam_role.lambda.arn
  runtime       = local.runtime
  handler       = each.value.handler
  timeout       = each.value.timeout
  memory_size   = each.value.memory

  filename         = local.lambda_zip
  source_code_hash = fileexists(local.lambda_zip) ? filebase64sha256(local.lambda_zip) : null

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = local.common_env
  }
}

# ── Provisioned concurrency — Step-8 fan-out ONLY, and only if var > 0 ────────
# Architecture.md §Lambda Provisioned Concurrency. The publish=true + alias is required
# because provisioned concurrency cannot target $LATEST.
resource "aws_lambda_function" "fov_versioned" {
  count = var.step8_provisioned_concurrency > 0 ? 1 : 0

  function_name    = "${var.project}-fov-precompute-pc"
  role             = aws_iam_role.lambda.arn
  runtime          = local.runtime
  handler          = "mircoverse.resolution.lambda_handlers.fov_batch"
  timeout          = 120
  memory_size      = 1024
  publish          = true
  filename         = local.lambda_zip
  source_code_hash = fileexists(local.lambda_zip) ? filebase64sha256(local.lambda_zip) : null

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }
  environment { variables = local.common_env }
}

resource "aws_lambda_provisioned_concurrency_config" "fov" {
  count                             = var.step8_provisioned_concurrency > 0 ? 1 : 0
  function_name                     = aws_lambda_function.fov_versioned[0].function_name
  qualifier                         = aws_lambda_function.fov_versioned[0].version
  provisioned_concurrent_executions = var.step8_provisioned_concurrency
}
