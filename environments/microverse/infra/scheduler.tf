# EventBridge Scheduler — the tick clock (Architecture.md §EventBridge Scheduler).
# Fires every tick_interval_seconds and starts a Step Functions execution. The rule is
# enabled/disabled by the lifecycle admin endpoints (start/pause/resume/end).
#
# Note (Architecture.md §Note on who knows the tick number): the Scheduler fires on a wall
# clock and does NOT carry N. The tick-resolver's first action reads the open tick from
# tick_state and runs the conditional UPDATE lock against it — so double-trigger prevention
# lives in the DB, not here.

resource "aws_iam_role" "scheduler" {
  name = "${var.project}-scheduler-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "scheduler_start_sfn" {
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["states:StartExecution"]
      Resource = [aws_sfn_state_machine.tick.arn]
    }]
  })
}

resource "aws_scheduler_schedule" "tick" {
  name = "${var.project}-tick-clock"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "rate(${var.tick_interval_seconds} seconds)"

  # Starts disabled — the admin /start endpoint enables it after spawning agents and
  # initializing the world (Architecture.md §Experiment Lifecycle).
  state = "DISABLED"

  target {
    arn      = aws_sfn_state_machine.tick.arn
    role_arn = aws_iam_role.scheduler.arn
    # No tick number passed — the resolver reads the open tick from tick_state.
    input = jsonencode({})
  }
}
