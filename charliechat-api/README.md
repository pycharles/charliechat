# Charlie Chat API

FastAPI application that provides the core chat functionality, combining AWS Lex V2 for natural language understanding with Bedrock AI for intelligent responses.

> **Note**: This is the API component of Charlie Chat. For the complete project overview, see the [root README](../README.md).

## Quick Start

### Prerequisites
- Python 3.11+
- AWS CLI configured
- Infrastructure deployed (see [Infrastructure Setup](../charliechat-terraform/README.md))

### Setup

1. **Navigate to API directory**
   ```bash
   cd charliechat-api
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp ../.env-template .env
   # Edit .env with your AWS credentials and configuration
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Configuration

The application uses environment variables for configuration. See the [root .env-template](../.env-template) for all available options.

### Required Variables
- `LEX_BOT_ID` - Your Lex V2 bot ID
- `LEX_BOT_ALIAS_ID` - Your Lex bot alias ID  
- `LEX_BOT_LOCALE_ID` - Bot locale (e.g., "en_US")
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_REGION` - AWS region (e.g., "us-east-1")

### Optional Variables
- `BEDROCK_MODEL_ID` - Claude model (default: "anthropic.claude-3-haiku-20240307-v1:0")
- `BEDROCK_MAX_TOKENS` - Response length (default: "500")
- `BEDROCK_KB_ID` - Knowledge Base ID for enhanced context
- `SYSTEM_PROMPT_TEMPLATE` - Custom AI personality
- `DEFAULT_PERSON` - Default person name (default: "Charles")
- `DEBUG_LOGGING` - Enable debug logs (default: "false")

## Infrastructure

The application requires AWS infrastructure to be deployed. See the [Infrastructure documentation](../charliechat-terraform/README.md) for detailed setup instructions.

### Lambda Deployment
```bash
# Deploy the Lambda function
./deploy_lambda.sh
```

## API Endpoints

### Chat Endpoint
```bash
POST /chat
Content-Type: application/json

{
  "session_id": "test-session",
  "text": "Tell me about your experience",
  "session_state": null
}
```

### Feedback Endpoint
```bash
POST /feedback
Content-Type: application/json

{
  "session_id": "test-session",
  "text": "Great responses!",
  "sentiment": "positive"
}
```

### Web Interface
- `GET /` - Main chat interface
- `GET /blog` - Dev journal with Markdown articles
- `GET /static/*` - Static assets (CSS, JS, images)

## Development

### Project Structure
```
app/
├── web/                    # Web interface (routes, templates, static)
│   ├── routes.py          # FastAPI route definitions
│   ├── templates/         # HTML templates
│   └── static/           # CSS, JavaScript, images
├── services/              # Business logic
│   ├── chat_service.py   # Chat orchestration
│   ├── lex_service.py    # Lex V2 integration
│   └── ai_service.py     # Bedrock AI integration
├── models/                # Data models
│   ├── chat.py           # Chat request/response models
│   └── lex.py            # Lex V2 event models
├── config.py             # Configuration management
└── main.py               # Application entry point
```

### Key Features
- **Layered Architecture**: Clean separation of concerns
- **Session Memory**: Maintains conversation context across turns
- **Knowledge Base Integration**: Enhanced responses with KB context
- **Voice Styles**: Multiple personality options (Normal, Surfer, Pirate, Ninja)
- **Error Handling**: Robust error handling with user-friendly messages
- **Environment-Driven**: Highly configurable via environment variables

### Adding Blog Articles
The dev journal supports Markdown articles. Add new articles by:
1. Creating a new `.md` file in the `journal-md/` directory
2. Use the format `YYYY-MM-DD-title.md` for automatic date parsing
3. The article will appear on the `/blog` page automatically

## Architecture

For detailed architectural information, see [ARCHITECTURE.md](ARCHITECTURE.md).