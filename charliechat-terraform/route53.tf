# Route53 Hosted Zone for charlesob.com
resource "aws_route53_zone" "charlesob" {
  name = "charlesob.com"
  
  tags = {
    Name = "charlie-chat-domain"
    Environment = "production"
  }
}

# A record with fqdn alias for root domain pointing to API Gateway
resource "aws_route53_record" "charlesob_root" {
  zone_id = aws_route53_zone.charlesob.zone_id
  name    = "charlesob.com"
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.charlesob.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.charlesob.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}

# CNAME for www subdomain pointing to root domain
resource "aws_route53_record" "charlesob_www" {
  zone_id = aws_route53_zone.charlesob.zone_id
  name    = "www.charlesob.com"
  type    = "CNAME"
  ttl     = 300
  records = ["charlesob.com"]
}
