output "api_gateway_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
  description = "Base URL for the Charlie Chat API"
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.charlie_api.id
}
