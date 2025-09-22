# Feedback Lambda Function
# This Lambda processes feedback form submissions and sends emails via SES

# IAM Role for Feedback Lambda
resource "aws_iam_role" "feedback_lambda_role" {
  name = "charlie-feedback-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "feedback_lambda_basic_execution" {
  role       = aws_iam_role.feedback_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom IAM policy for SES permissions
resource "aws_iam_policy" "feedback_ses_policy" {
  name        = "charlie-feedback-ses-policy"
  description = "Policy for feedback Lambda to send emails via SES"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach SES policy to feedback Lambda role
resource "aws_iam_role_policy_attachment" "feedback_ses_policy" {
  role       = aws_iam_role.feedback_lambda_role.name
  policy_arn = aws_iam_policy.feedback_ses_policy.arn
}

# Create deployment package for feedback Lambda
data "archive_file" "feedback_lambda_zip" {
  type        = "zip"
  source_file = "../charliechat-api/lambda_feedback.py"
  output_path = "../charliechat-api/feedback-lambda-deployment.zip"
}

# Feedback Lambda function
resource "aws_lambda_function" "feedback_lambda" {
  filename         = data.archive_file.feedback_lambda_zip.output_path
  function_name    = "charlie-feedback-lambda"
  role            = aws_iam_role.feedback_lambda_role.arn
  handler         = "newrelic_lambda_wrapper.handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 128
  source_code_hash = filebase64sha256("../charliechat-api/feedback-lambda-deployment.zip")

  # New Relic Lambda Layer (required for monitoring)
  layers = [
    "arn:aws:lambda:${data.dotenv.env.env["AWS_REGION"]}:${data.dotenv.env.env["AWS_ACCOUNT"]}:layer:NewRelicPython311:56"
  ]

  environment {
    variables = {
      FEEDBACK_SENDER_EMAIL    = data.dotenv.env.env["FEEDBACK_SENDER_EMAIL"]
      FEEDBACK_RECIPIENT_EMAIL = data.dotenv.env.env["FEEDBACK_RECIPIENT_EMAIL"]

      # New Relic Configuration (Layer-based monitoring)
      NEW_RELIC_ACCOUNT_ID                    = data.dotenv.env.env["NEW_RELIC_ACCOUNT_ID"]
      NEW_RELIC_LAMBDA_EXTENSION_ENABLED      = data.dotenv.env.env["NEW_RELIC_LAMBDA_EXTENSION_ENABLED"]
      NEW_RELIC_LAMBDA_HANDLER                = "lambda_feedback.lambda_handler"  # Original handler for layer wrapper
      NEW_RELIC_EXTENSION_SEND_EXTENSION_LOGS = data.dotenv.env.env["NEW_RELIC_EXTENSION_SEND_EXTENSION_LOGS"]
      NEW_RELIC_EXTENSION_SEND_FUNCTION_LOGS  = data.dotenv.env.env["NEW_RELIC_EXTENSION_SEND_FUNCTION_LOGS"]
      NEW_RELIC_LICENSE_KEY                   = data.dotenv.env.env["NEW_RELIC_LICENSE_KEY"]
      NEW_RELIC_DATA_COLLECTION_TIMEOUT       = data.dotenv.env.env["NEW_RELIC_DATA_COLLECTION_TIMEOUT"]
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.feedback_lambda_basic_execution,
    aws_iam_role_policy_attachment.feedback_ses_policy,
  ]
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "feedback_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.feedback_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.charlie_api.execution_arn}/*/*"
}
