# API Gateway + Lambda Integration for Charlie Chat
# This configuration wires HTTP API to the Lambda function
# and deploys with $default route for FastAPI routing.

# Custom domain configuration (using existing certificate)
data "aws_acm_certificate" "charlesob" {
  domain   = "charlesob.com"
  statuses = ["ISSUED"]
  most_recent = true
}

# API Gateway custom domain for root domain (primary)
resource "aws_apigatewayv2_domain_name" "charlesob" {
  domain_name = "charlesob.com"
  
  domain_name_configuration {
    certificate_arn = data.aws_acm_certificate.charlesob.arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

# API Gateway custom domain for www subdomain
resource "aws_apigatewayv2_domain_name" "charlesob_www" {
  domain_name = "www.charlesob.com"
  
  domain_name_configuration {
    certificate_arn = data.aws_acm_certificate.charlesob.arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

# API Gateway domain mapping for root domain
resource "aws_apigatewayv2_api_mapping" "charlesob" {
  api_id      = aws_apigatewayv2_api.charlie_api.id
  domain_name = aws_apigatewayv2_domain_name.charlesob.id
  stage       = aws_apigatewayv2_stage.default.id
}

# API Gateway domain mapping for www subdomain
resource "aws_apigatewayv2_api_mapping" "charlesob_www" {
  api_id      = aws_apigatewayv2_api.charlie_api.id
  domain_name = aws_apigatewayv2_domain_name.charlesob_www.id
  stage       = aws_apigatewayv2_stage.default.id
}

# HTTP API Gateway
resource "aws_apigatewayv2_api" "charlie_api" {
  name          = "charlie-chat-api"
  protocol_type = "HTTP"
  description   = "Charlie Chat API Gateway"
}

# Lambda integration
resource "aws_apigatewayv2_integration" "charlie_lambda" {
  api_id           = aws_apigatewayv2_api.charlie_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.charlie_api.invoke_arn
  integration_method = "POST"
}

# Default route (catches all requests)
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.charlie_api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.charlie_lambda.id}"
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.charlie_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.charlie_api.execution_arn}/*/*"
}

# API Gateway stage
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.charlie_api.id
  name        = "$default"
  auto_deploy = true
}
