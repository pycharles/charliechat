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

# Custom policy for Lex access
resource "aws_iam_role_policy" "lambda_lex_access" {
  name = "charlie-lambda-lex-access"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lex:RecognizeText",
          "lex:RecognizeUtterance",
          "lex:StartConversation"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "charlie_api" {
  filename         = "../charliechat-api/lambda-deployment.zip"
  function_name    = "charlie-chat-api"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_handler.handler"
  runtime         = "python3.11"
  timeout         = 30
  source_code_hash = filebase64sha256("../charliechat-api/lambda-deployment.zip")

  environment {
    variables = {
      # Lex Bot Configuration
      LEX_BOT_ID        = data.dotenv.env.env["LEX_BOT_ID"]
      LEX_BOT_ALIAS_ID  = data.dotenv.env.env["LEX_BOT_ALIAS_ID"]
      LEX_BOT_LOCALE_ID = data.dotenv.env.env["LEX_BOT_LOCALE_ID"]
      
      # Bedrock AI Configuration
      # BEDROCK_MODEL_ID: Switch Claude model (haiku/sonnet/opus)
      # BEDROCK_MAX_TOKENS: Control response length (100-4000)
      # SYSTEM_PROMPT_TEMPLATE: Custom personality/tone override
      # DEFAULT_PERSON: Default person name when Lex slot is missing
      # DEBUG_LOGGING: Enable debug logging for development
      BEDROCK_MODEL_ID     = data.dotenv.env.env["BEDROCK_MODEL_ID"]
      BEDROCK_MAX_TOKENS   = data.dotenv.env.env["BEDROCK_MAX_TOKENS"]
      SYSTEM_PROMPT_TEMPLATE = data.dotenv.env.env["SYSTEM_PROMPT_TEMPLATE"]
      DEFAULT_PERSON       = data.dotenv.env.env["DEFAULT_PERSON"]
      DEBUG_LOGGING        = data.dotenv.env.env["DEBUG_LOGGING"]
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.lambda_lex_access,
  ]
}

# Temporary Lambda function URL (alternative to API Gateway for testing)
# TODO: Remove this once API Gateway is working
resource "aws_lambda_function_url" "charlie_api_url" {
  function_name      = aws_lambda_function.charlie_api.function_name
  authorization_type = "NONE"
}
