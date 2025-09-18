output "api_gateway_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
  description = "Base URL for the Charlie Chat API"
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.charlie_api.id
}

output "custom_domain_url" {
  value = "https://charlesob.com"
  description = "Primary custom domain URL for the Charlie Chat API (charlesob.com)"
}

output "api_gateway_target" {
  value = aws_apigatewayv2_domain_name.charlesob.domain_name_configuration[0].target_domain_name
  description = "API Gateway target domain for Route53 A record"
}

output "dns_instructions" {
  value = <<-EOT
    DNS Configuration:
    
    Primary domain: charlesob.com (points to API Gateway)
    Redirect domain: www.charlesob.com (redirects to charlesob.com)
    
    Route53 will handle both domains automatically:
    - charlesob.com -> API Gateway (A record alias)
    - www.charlesob.com -> charlesob.com (CNAME record)
    
    The application will redirect www.charlesob.com requests to charlesob.com
  EOT
  description = "DNS configuration summary"
}
