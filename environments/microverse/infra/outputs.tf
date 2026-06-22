output "api_base_url" {
  value       = aws_apigatewayv2_stage.default.invoke_url
  description = "Base URL agents call. The Protocol.md §5 paths hang off this unchanged from local."
}

output "aurora_endpoint" {
  value       = aws_rds_cluster.aurora.endpoint
  description = "Aurora writer endpoint (reached via RDS Proxy in-app, not directly)."
}

output "rds_proxy_endpoint" {
  value       = aws_db_proxy.main.endpoint
  description = "The connection-pooled endpoint Lambdas actually use."
}

output "tick_state_machine_arn" {
  value = aws_sfn_state_machine.tick.arn
}

output "db_secret_arn" {
  value     = aws_secretsmanager_secret.db.arn
  sensitive = true
}
