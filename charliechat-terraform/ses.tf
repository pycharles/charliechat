# Amazon SES Configuration for Feedback Feature
# This file configures SES for sending feedback emails

# Output the sender email for reference (manually verified)
output "feedback_sender_email" {
  description = "Verified sender email address for feedback"
  value       = "noreply@charlesob.com"
}
