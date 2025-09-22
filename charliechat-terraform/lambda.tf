# Data sources for current region and account
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# Lambda IAM Role
resource "aws_iam_role" "lambda_execution_role" {
  name = "charlie-lambda-execution-role"

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
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach Bedrock full access policy for Knowledge Base integration
resource "aws_iam_role_policy_attachment" "lambda_bedrock_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

# Note: Lex access policy removed - no longer using Lex

# API Lambda function (FastAPI + Mangum)
resource "aws_lambda_function" "charlie_api" {
  filename         = "../charliechat-api/lambda-deployment.zip"
  function_name    = "charlie-chat-api"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "newrelic_lambda_wrapper.handler"
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256
  source_code_hash = filebase64sha256("../charliechat-api/lambda-deployment.zip")
  
  # New Relic Lambda Layer (required for monitoring)
  layers = [
    "arn:aws:lambda:${data.dotenv.env.env["AWS_REGION"]}:${data.dotenv.env.env["AWS_ACCOUNT"]}:layer:NewRelicPython311:56"
  ]

  environment {
    variables = {
      # Bedrock AI Configuration
      # BEDROCK_MODEL_ID: Switch Claude model (haiku/sonnet/opus)
      # BEDROCK_MAX_TOKENS: Control response length (100-4000)
      # BEDROCK_KB_ID: Knowledge Base ID for enhanced context
      # SYSTEM_PROMPT_TEMPLATE: Custom personality/tone override
      # DEFAULT_PERSON: Default person name when not specified
      # DEBUG_LOGGING_PROD: Enable debug logging in production Lambda
      BEDROCK_MODEL_ID     = data.dotenv.env.env["BEDROCK_MODEL_ID"]
      BEDROCK_MAX_TOKENS   = data.dotenv.env.env["BEDROCK_MAX_TOKENS"]
      BEDROCK_KB_ID        = data.dotenv.env.env["BEDROCK_KB_ID"]
      SYSTEM_PROMPT_TEMPLATE = data.dotenv.env.env["SYSTEM_PROMPT_TEMPLATE"]
      DEFAULT_PERSON       = data.dotenv.env.env["DEFAULT_PERSON"]
      DEBUG_LOGGING        = data.dotenv.env.env["DEBUG_LOGGING_PROD"]
      
      # PostHog Analytics Configuration
      # POSTHOG_API_KEY: PostHog project API key (required for analytics)
      # POSTHOG_HOST: PostHog host URL (optional, defaults to app.posthog.com)
      POSTHOG_API_KEY      = data.dotenv.env.env["POSTHOG_API_KEY"]
      POSTHOG_HOST         = data.dotenv.env.env["POSTHOG_HOST"]

      # New Relic Configuration (Layer-based monitoring)
      NEW_RELIC_ACCOUNT_ID                    = data.dotenv.env.env["NEW_RELIC_ACCOUNT_ID"]
      NEW_RELIC_LAMBDA_EXTENSION_ENABLED      = data.dotenv.env.env["NEW_RELIC_LAMBDA_EXTENSION_ENABLED"]
      NEW_RELIC_LAMBDA_HANDLER                = "lambda_api.lambda_api.handler"  # Original handler for layer wrapper
      NEW_RELIC_EXTENSION_SEND_EXTENSION_LOGS = data.dotenv.env.env["NEW_RELIC_EXTENSION_SEND_EXTENSION_LOGS"]
      NEW_RELIC_EXTENSION_SEND_FUNCTION_LOGS  = data.dotenv.env.env["NEW_RELIC_EXTENSION_SEND_FUNCTION_LOGS"]
      NEW_RELIC_LICENSE_KEY                   = data.dotenv.env.env["NEW_RELIC_LICENSE_KEY"]
      NEW_RELIC_DATA_COLLECTION_TIMEOUT       = data.dotenv.env.env["NEW_RELIC_DATA_COLLECTION_TIMEOUT"]
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy_attachment.lambda_bedrock_access,
  ]
}


# Lambda function URL (commented out - using API Gateway instead)
# resource "aws_lambda_function_url" "charlie_api_url" {
#   function_name      = aws_lambda_function.charlie_api.function_name
#   authorization_type = "NONE"
# }
