# CloudFront Distribution Outputs

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for charlesob.com"
  value       = aws_cloudfront_distribution.charlesob.id
}

output "cloudfront_distribution_domain_name" {
  description = "CloudFront distribution domain name for charlesob.com"
  value       = aws_cloudfront_distribution.charlesob.domain_name
}

output "cloudfront_www_distribution_id" {
  description = "CloudFront distribution ID for www.charlesob.com"
  value       = aws_cloudfront_distribution.charlesob_www.id
}

output "cloudfront_www_distribution_domain_name" {
  description = "CloudFront distribution domain name for www.charlesob.com"
  value       = aws_cloudfront_distribution.charlesob_www.domain_name
}

output "domain_access_info" {
  description = "Domain access information with HTTP to HTTPS redirect"
  value = {
    primary_domain = "https://charlesob.com"
    www_domain     = "https://www.charlesob.com"
    http_behavior  = "Automatically redirects HTTP to HTTPS"
    note          = "Both HTTP and HTTPS traffic are now supported with automatic HTTPS redirect"
  }
}
