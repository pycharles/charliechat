# CloudFront Distribution for HTTP to HTTPS Redirect
# This handles both HTTP and HTTPS traffic, automatically redirecting HTTP to HTTPS

# CloudFront distribution for root domain
resource "aws_cloudfront_distribution" "charlesob" {
  origin {
    domain_name = aws_apigatewayv2_domain_name.charlesob.domain_name_configuration[0].target_domain_name
    origin_id   = "APIGateway-charlesob.com"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  enabled = true

  aliases = ["charlesob.com"]

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "APIGateway-charlesob.com"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true
      headers      = ["*"]

      cookies {
        forward = "all"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = data.aws_acm_certificate.charlesob.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Name        = "charlesob.com-cloudfront"
    Environment = "production"
    Project     = "charlie-chat"
  }
}

# CloudFront distribution for www subdomain
resource "aws_cloudfront_distribution" "charlesob_www" {
  origin {
    domain_name = aws_apigatewayv2_domain_name.charlesob_www.domain_name_configuration[0].target_domain_name
    origin_id   = "APIGateway-www.charlesob.com"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  enabled = true

  aliases = ["www.charlesob.com"]

  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "APIGateway-www.charlesob.com"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true
      headers      = ["*"]

      cookies {
        forward = "all"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = data.aws_acm_certificate.charlesob.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Name        = "www.charlesob.com-cloudfront"
    Environment = "production"
    Project     = "charlie-chat"
  }
}
