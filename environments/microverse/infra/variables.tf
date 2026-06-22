variable "region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region for the platform."
}

variable "project" {
  type    = string
  default = "mircoverse"
}

variable "tick_interval_seconds" {
  type        = number
  default     = 30
  description = "EventBridge Scheduler tick clock interval (Architecture.md: 30-60s)."
}

# ── Aurora Serverless v2 capacity (ACU) ──────────────────────────────────────
# Bursty profile: near-zero between ticks, bursts during Step Functions resolution.
variable "aurora_min_acu" {
  type        = number
  default     = 0.5
  description = "Floor. 0.5 is the practical warm floor under a 30-60s tick (never idles long enough to auto-pause)."
}

variable "aurora_max_acu" {
  type        = number
  default     = 16
  description = "Ceiling for the 1000-agent burst. Raise for the 10k breakage probe."
}

# ── Provisioned concurrency — DEFAULT 0 ──────────────────────────────────────
# Architecture.md §Lambda Provisioned Concurrency: a LOAD-TEST-GATED HEDGE, not a
# 24/7 default. Reserve it for the bounded Step-8 fan-out ONLY, and only after the
# p99 tick-latency graph shows a cold-start tail. Defaulted to 0 deliberately.
variable "step8_provisioned_concurrency" {
  type        = number
  default     = 0
  description = "Pre-warmed envs for the FOV-precompute fan-out. Keep 0 until the load test justifies it."
}

variable "fov_batch_workers" {
  type        = number
  default     = 8
  description = "Step-8 batch fan-out width (Architecture.md: ~5-10 set-based workers, NOT per-agent)."
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}
