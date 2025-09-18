# IAM Policy for Charlie Chat User to manage SES
# This policy allows the charliechat-user to manage SES email identities

# IAM policy for SES management
resource "aws_iam_policy" "charliechat_user_ses_policy" {
  name        = "charliechat-user-ses-policy"
  description = "Policy for charliechat-user to manage SES email identities"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:VerifyEmailIdentity",
          "ses:DeleteIdentity",
          "ses:GetIdentityVerificationAttributes",
          "ses:ListIdentities",
          "ses:GetSendQuota",
          "ses:GetSendRate"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach the SES policy to the charliechat-user
resource "aws_iam_user_policy_attachment" "charliechat_user_ses_policy" {
  user       = "charliechat-user"
  policy_arn = aws_iam_policy.charliechat_user_ses_policy.arn
}
