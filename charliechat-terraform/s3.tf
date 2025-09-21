# S3 Bucket Versioning Configuration
# This manages versioning for existing S3 buckets

# Import existing bedrock knowledge base bucket
resource "aws_s3_bucket" "bedrock_knowledge_base" {
  bucket = "bedrock-knowledge-base-charliechat"

  tags = {
    Name        = "Bedrock Knowledge Base Data Source"
    Environment = "production"
    Project     = "charlie-chat"
  }
}

# Enable versioning on the bedrock knowledge base bucket
resource "aws_s3_bucket_versioning" "bedrock_knowledge_base" {
  bucket = aws_s3_bucket.bedrock_knowledge_base.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "bedrock_knowledge_base" {
  bucket = aws_s3_bucket.bedrock_knowledge_base.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "bedrock_knowledge_base" {
  bucket = aws_s3_bucket.bedrock_knowledge_base.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
