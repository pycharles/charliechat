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
      LEX_BOT_ID        = data.dotenv.env.env["LEX_BOT_ID"]
      LEX_BOT_ALIAS_ID  = data.dotenv.env.env["LEX_BOT_ALIAS_ID"]
      LEX_BOT_LOCALE_ID = data.dotenv.env.env["LEX_BOT_LOCALE_ID"]
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
