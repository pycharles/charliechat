# charliechat
CharlieChatBot is a custom chatbot that can answer questions about my professional background, be interviewed, or act as a personal AI. It runs on FastAPI and is deployed using Terraform.

## Charlie Chatbot (AWS Lex + FastAPI)

This repo provisions an AWS Lex V2 bot (Terraform) and exposes a minimal FastAPI service that proxies chat messages to Lex.

### Prerequisites
- Terraform >= 1.6
- Python 3.10+
- AWS credentials with permissions to create Lex V2 resources

### Deploy Lex with Terraform
```bash
# Copy and fill in your .env file first
cp .env-template .env
# Edit .env with your actual AWS credentials

cd charliechat-terraform
terraform init
terraform apply -auto-approve
```

After apply, capture outputs:
```bash
terraform output -raw lex_bot_id
terraform output -raw lex_bot_alias_id
terraform output -raw lex_bot_locale_id
```

### Run the FastAPI service
```bash
cd ../charliechat-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# The .env file should already be created in the root directory
# If not, copy it: cp ../.env-template .env

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Test the chat endpoint
```bash
curl -s -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"local-test","text":"Hello!"}' | jq
```

### Notes
- The Terraform bot includes a basic `ChatIntent` and fallback intent with a greeting.
- Customize intents, slots, and responses in `charliechat-terraform/main.tf` to reflect your experience and Q&A.
- For production, scope down IAM policies instead of using `AmazonLexFullAccess`.
