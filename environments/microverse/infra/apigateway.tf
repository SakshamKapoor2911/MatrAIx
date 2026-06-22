# API Gateway (HTTP API) — the agent-facing surface (Architecture.md §API Gateway).
# Agent routes use per-agent API-key auth via a Lambda authorizer (the key's SHA-256 is
# checked against agents.api_key_hash). Admin routes use IAM/SigV4 — a SEPARATE mechanism,
# because admin endpoints start/end the experiment and read any agent's drift history.

resource "aws_apigatewayv2_api" "http" {
  name          = "${var.project}-api"
  protocol_type = "HTTP"
}

# ── Lambda authorizer for agent API keys ─────────────────────────────────────
resource "aws_apigatewayv2_authorizer" "agent_key" {
  api_id                            = aws_apigatewayv2_api.http.id
  authorizer_type                   = "REQUEST"
  identity_sources                  = ["$request.header.Authorization"]
  name                              = "${var.project}-agent-key-authorizer"
  authorizer_uri                    = aws_lambda_function.fn["state_reader"].invoke_arn # placeholder: a dedicated authorizer fn in the build
  authorizer_payload_format_version = "2.0"
  enable_simple_responses           = true
}

# Integrations + routes for the three agent-facing functions.
locals {
  # route key  ->  backing function key  (Protocol.md §5 endpoints)
  agent_routes = {
    "POST /api/v1/agents/register"          = "registration"
    "GET /api/v1/world/observe"             = "state_reader"
    "GET /api/v1/agents/{id}/status"        = "state_reader"
    "GET /api/v1/simulation/status"         = "state_reader"
    "GET /api/v1/agents/{id}/memory/{file}" = "state_reader"
    "POST /api/v1/agents/{id}/action"       = "action_receiver"
    "POST /api/v1/agents/{id}/reflection"   = "action_receiver"
  }
}

resource "aws_apigatewayv2_integration" "fn" {
  for_each = toset(values(local.agent_routes))

  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.fn[each.value].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "agent" {
  for_each = local.agent_routes

  api_id    = aws_apigatewayv2_api.http.id
  route_key = each.key
  target    = "integrations/${aws_apigatewayv2_integration.fn[each.value].id}"

  # register is the only unauthenticated agent route (it issues the key).
  authorization_type = each.key == "POST /api/v1/agents/register" ? "NONE" : "CUSTOM"
  authorizer_id      = each.key == "POST /api/v1/agents/register" ? null : aws_apigatewayv2_authorizer.agent_key.id
}

resource "aws_lambda_permission" "apigw" {
  for_each = toset(values(local.agent_routes))

  statement_id  = "AllowAPIGW-${each.value}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fn[each.value].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  # Throttling at the entry point (Architecture.md §Why No SQS: API GW handles throttling).
  default_route_settings {
    throttling_burst_limit = 2000
    throttling_rate_limit  = 1000
  }
}
