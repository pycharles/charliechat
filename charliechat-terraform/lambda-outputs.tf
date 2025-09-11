output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.charlie_api.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.charlie_api.arn
}

output "lambda_function_url" {
  description = "Lambda function URL (direct access)"
  value       = try(aws_lambda_function_url.charlie_api_url[0].function_url, null)
}
