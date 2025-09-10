output "lex_bot_id" {
  description = "Lex V2 Bot ID"
  value       = aws_lexv2models_bot.charlie.id
}

# output "lex_bot_alias_id" {
#   description = "Lex V2 Bot Alias ID"
#   value       = aws_lexv2models_bot_alias.live.bot_alias_id
# }
# Note: Bot alias output commented out as aws_lexv2models_bot_alias is not supported

output "lex_bot_locale_id" {
  description = "Lex V2 Bot Locale ID"
  value       = aws_lexv2models_bot_locale.en_us.locale_id
}



