output "route53_zone_id" {
  description = "Route53 hosted zone ID for charlesob.com"
  value       = aws_route53_zone.charlesob.zone_id
}

output "route53_name_servers" {
  description = "Route53 name servers for domain registrar delegation"
  value       = aws_route53_zone.charlesob.name_servers
}
