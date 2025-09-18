# Charlie Chat Infrastructure

Terraform configurations for deploying the Charlie Chat application infrastructure on AWS.

> **Note**: This is the infrastructure component of Charlie Chat. For the complete project overview, see the [root README](../README.md).

## Overview

The infrastructure provisions:
- **Lambda Functions**: API and Lex fulfillment functions
- **API Gateway**: HTTP API for web interface and API endpoints
- **Route53**: DNS management and custom domain setup
- **IAM Roles**: Permissions for Lambda functions and external services
- **Lex V2 Bot**: Natural language understanding (configured separately)

## Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform >= 1.6 installed
- Domain name registered (for custom domain setup)
- SSL certificate in AWS Certificate Manager

## Quick Start

1. **Configure environment**
   ```bash
   cp ../.env-template ../.env
   # Edit .env with your AWS credentials and configuration
   ```

2. **Initialize and deploy**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

3. **Create Lex bot alias** (Terraform doesn't support this)
   ```bash
   aws lexv2-models create-bot-alias \
     --bot-id $(terraform output -raw lex_bot_id) \
     --bot-version 1 \
     --bot-alias-name live \
     --description "Live alias for Charlie bot"
   ```

## Configuration

### Environment Variables
The Terraform configuration reads from a `.env` file in the parent directory. See the [root .env-template](../.env-template) for all available options.

Required variables for infrastructure deployment:
- `LEX_BOT_ID` - Your Lex V2 bot ID
- `LEX_BOT_ALIAS_ID` - Your Lex bot alias ID
- `LEX_BOT_LOCALE_ID` - Bot locale (e.g., "en_US")
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_REGION` - AWS region (e.g., "us-east-1")

### Custom Domain Setup
To use a custom domain:
1. Update `route53.tf` with your domain name
2. Ensure your domain is registered in Route53
3. Update the ACM certificate ARN in `apigateway.tf`

## Infrastructure Components

### Lambda Functions
- **`charlie-chat-api`**: FastAPI web application with Mangum
- **`charlie-chat-lex-fulfillment`**: Direct Lex V2 fulfillment handler

### API Gateway
- HTTP API with custom domain support
- CORS configuration for web interface
- Lambda integration for both functions

### Route53
- DNS management for custom domains
- A records for root and www subdomains
- Automatic redirect from www to root domain

### IAM Roles
- **Lambda Execution Role**: Basic Lambda execution permissions
- **Lex Access Role**: Permissions for Lex V2 integration
- **Bedrock Access Role**: Permissions for AI service integration

## File Structure

```
├── main.tf                 # Provider configuration and data sources
├── variables.tf            # Input variables
├── lex.tf                  # Lex V2 bot configuration
├── lambda.tf               # Lambda functions and IAM roles
├── apigateway.tf           # API Gateway and custom domains
├── route53.tf              # DNS configuration
├── lex-outputs.tf          # Lex-related outputs
├── lambda-outputs.tf       # Lambda-related outputs
└── apigateway-outputs.tf   # API Gateway outputs
```

## Deployment

### Initial Deployment
```bash
terraform init
terraform plan
terraform apply
```

### Updates
After making changes to the Lambda code:
```bash
# Deploy updated Lambda functions
cd ../charliechat-api
./deploy_lambda.sh

# Update Terraform if needed
cd ../charliechat-terraform
terraform plan
terraform apply
```

## Outputs

After deployment, Terraform provides:
- API Gateway URL
- Custom domain URL
- Lambda function names and ARNs
- Route53 zone information

## Troubleshooting

### Common Issues
1. **Permission Denied**: Ensure AWS credentials have sufficient permissions
2. **Domain Not Found**: Verify domain is registered in Route53
3. **Certificate Issues**: Check ACM certificate ARN and region
4. **Lambda Timeout**: Increase timeout in `lambda.tf` if needed

### Debugging
```bash
# Check Terraform state
terraform show

# View logs
terraform console

# Destroy and recreate
terraform destroy
terraform apply
```

## Security Notes

- IAM roles follow the principle of least privilege
- Lambda functions have minimal required permissions
- API Gateway includes CORS configuration
- Environment variables are managed securely

## Cost Considerations

- Lambda functions are pay-per-request
- API Gateway charges per request
- Route53 has minimal monthly costs
- Lex V2 charges per text processed
- Bedrock charges per token generated

For detailed cost information, see AWS pricing documentation.
