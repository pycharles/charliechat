output "lex_bot_id" {
  description = "Lex V2 Bot ID"
  value       = aws_lexv2models_bot.charlie.id
}

output "lex_bot_version" {
  description = "Lex V2 Bot Version"
  value       = aws_lexv2models_bot_version.v1.bot_version
}

output "lex_bot_locale_id" {
  description = "Lex V2 Bot Locale ID"
  value       = aws_lexv2models_bot_locale.en_us.locale_id
}

# Note: Bot alias not supported in current AWS provider version, used aws cli to get alias id for .env
