# Step Functions Standard Workflow — the tick resolver (Architecture.md §Tick Resolution).
# Standard (not Express): full execution history per tick is essential for debugging corrupt
# world state. ~11 transitions/tick × 1000 ticks ≈ 11k — well within limits, negligible cost.
#
# Context payload carries ONLY {"tick": N}; all inter-step data lives in tick_scratch in Aurora
# (the 256KB state-payload limit would otherwise be exceeded at 1000 agents). Each step has a
# Catch → error handler so the simulation never stalls (degrades to a no-op tick).

resource "aws_iam_role" "sfn" {
  name = "${var.project}-sfn-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "states.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "sfn_invoke" {
  role = aws_iam_role.sfn.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["lambda:InvokeFunction"]
      Resource = [
        aws_lambda_function.fn["tick_step"].arn,
        aws_lambda_function.fn["fov_precompute"].arn,
      ]
    }]
  })
}

locals {
  step_arn = aws_lambda_function.fn["tick_step"].arn
  fov_arn  = aws_lambda_function.fn["fov_precompute"].arn

  # The sequential steps 0-7b + 9 all invoke the single tick_step Lambda with a
  # {tick, step} payload; only the `step` name differs. Built programmatically so the
  # chain stays in lock-step with Architecture.md's Steps list and can't drift by hand.
  sequential_steps = [
    { name = "Step0_Cleanup", step = "cleanup", next = "Step1_Environment" },
    { name = "Step1_Environment", step = "environment", next = "Step2_Death" },
    { name = "Step2_Death", step = "death_status", next = "Step3_Movement" },
    { name = "Step3_Movement", step = "movement", next = "Step4_Attack" },
    { name = "Step4_Attack", step = "attack", next = "Step5_Trade" },
    { name = "Step5_Trade", step = "trade", next = "Step6_Conversation" },
    { name = "Step6_Conversation", step = "conversation", next = "Step7a_WorldWrite" },
    { name = "Step7a_WorldWrite", step = "world_write", next = "Step7b_Audit" },
    { name = "Step7b_Audit", step = "audit_write", next = "Step8_FOV" },
  ]

  sequential_states = {
    for s in local.sequential_steps : s.name => {
      Type       = "Task"
      Resource   = local.step_arn
      Parameters = { "tick.$" = "$.tick", step = s.step }
      ResultPath = "$.step_result"
      Next       = s.next
      Catch      = [{ ErrorEquals = ["States.ALL"], Next = "TickError" }]
    }
  }

  # Step 8: BATCHED fan-out — a Map over fov_batch_workers buckets, NOT 1000 per-agent branches.
  step8_state = {
    Step8_FOV = {
      Type           = "Map"
      ItemsPath      = "$.fov_buckets"
      MaxConcurrency = var.fov_batch_workers
      Iterator = {
        StartAt = "FOVBatch"
        States = {
          FOVBatch = {
            Type     = "Task"
            Resource = local.fov_arn
            End      = true
            Retry    = [{ ErrorEquals = ["States.ALL"], MaxAttempts = 2, IntervalSeconds = 1 }]
          }
        }
      }
      Next       = "Step9_Advance"
      ResultPath = "$.fov_results"
      Catch      = [{ ErrorEquals = ["States.ALL"], Next = "TickError" }]
    }
  }

  tail_states = {
    Step9_Advance = {
      Type       = "Task"
      Resource   = local.step_arn
      Parameters = { "tick.$" = "$.tick", step = "advance" }
      End        = true
      Catch      = [{ ErrorEquals = ["States.ALL"], Next = "TickError" }]
    }
    # The simulation never stalls — a failed step degrades to a no-op tick that still advances.
    TickError = {
      Type       = "Task"
      Resource   = local.step_arn
      Parameters = { "tick.$" = "$.tick", step = "error_recover" }
      End        = true
    }
  }

  tick_definition = jsonencode({
    Comment = "MircoVerse tick resolution — Steps 0-9 (Architecture.md)"
    StartAt = "Step0_Cleanup"
    States  = merge(local.sequential_states, local.step8_state, local.tail_states)
  })
}

resource "aws_sfn_state_machine" "tick" {
  name       = "${var.project}-tick-resolver"
  role_arn   = aws_iam_role.sfn.arn
  type       = "STANDARD"
  definition = local.tick_definition
}
