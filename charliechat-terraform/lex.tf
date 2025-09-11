# Lex V2 Bot Resources
resource "aws_iam_role" "lex_bot_role" {
  name               = "charlie-lex-bot-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = { Service = "lexv2.amazonaws.com" }
        Action   = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lex_bot_full_access" {
  role       = aws_iam_role.lex_bot_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonLexFullAccess"
}

resource "aws_iam_role_policy_attachment" "lex_bot_bedrock_full_access" {
  role       = aws_iam_role.lex_bot_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

resource "aws_lexv2models_bot" "charlie" {
  name                         = var.bot_name
  description                  = "Charlie virtual resume bot"
  role_arn                     = aws_iam_role.lex_bot_role.arn
  idle_session_ttl_in_seconds  = 300
  
  data_privacy {
    child_directed = false
  }
}

resource "aws_lexv2models_bot_locale" "en_us" {
  bot_id                = aws_lexv2models_bot.charlie.id
  bot_version           = "DRAFT"
  locale_id             = "en_US"
  n_lu_intent_confidence_threshold = 0.40

  voice_settings {
    voice_id = "Joanna"
  }
}

resource "aws_lexv2models_bot_version" "v1" {
  bot_id = aws_lexv2models_bot.charlie.id
  locale_specification = {
    (aws_lexv2models_bot_locale.en_us.locale_id) = {
      source_bot_version = "DRAFT"
    }
  }
}

# Note: aws_lexv2models_bot_alias is not yet supported in the AWS provider
# Note: removing intents since terraform support is limited
