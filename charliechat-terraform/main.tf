terraform {
  required_version = ">= 1.13.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.12.0"
    }
    dotenv = {
      source  = "jrhouston/dotenv"
      version = ">= 1.0.1"
    }
  }
}

# Load environment variables from .env file
data "dotenv" "env" {
  filename = "../.env"
}

provider "aws" {
  region = data.dotenv.env.env["AWS_REGION"]
}

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

resource "aws_lexv2models_intent" "fallback" {
  bot_id       = aws_lexv2models_bot.charlie.id
  bot_version  = "DRAFT"
  locale_id    = aws_lexv2models_bot_locale.en_us.locale_id
  name         = "AMAZON.FallbackIntent"

}

resource "aws_lexv2models_intent" "intro" {
  bot_id      = aws_lexv2models_bot.charlie.id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us.locale_id
  name        = "ChatIntent"


  fulfillment_code_hook {
    enabled = false
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
# The bot can be used directly with the version reference



