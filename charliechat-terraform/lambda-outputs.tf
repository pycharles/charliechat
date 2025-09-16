# API Lambda outputs
output "api_lambda_function_name" {
  description = "API Lambda function name (FastAPI + Mangum)"
  value       = aws_lambda_function.charlie_api.function_name
}

output "api_lambda_function_arn" {
  description = "API Lambda function ARN"
  value       = aws_lambda_function.charlie_api.arn
}

output "api_lambda_function_url" {
  description = "API Lambda function URL (direct access)"
  value       = try(aws_lambda_function_url.charlie_api_url.function_url, null)
}

# Legacy outputs for backward compatibility
output "lambda_function_name" {
  description = "API Lambda function name (legacy)"
  value       = aws_lambda_function.charlie_api.function_name
}

output "lambda_function_arn" {
  description = "API Lambda function ARN (legacy)"
  value       = aws_lambda_function.charlie_api.arn
}

output "lambda_function_url" {
  description = "API Lambda function URL (legacy)"
  value       = try(aws_lambda_function_url.charlie_api_url.function_url, null)
}