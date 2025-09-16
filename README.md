# Charlie Chat

An AI-powered chatbot that combines AWS Lex V2 for natural language understanding with Bedrock AI for intelligent responses. Built with FastAPI and deployed using Terraform, it can answer questions about professional background, conduct interviews, or act as a personal AI assistant.

## 🚀 Quick Start

1. **Clone and setup environment**
   ```bash
   git clone <repository-url>
   cd charliechat
   cp .env-template .env
   # Edit .env with your AWS credentials
   ```

2. **Deploy infrastructure**
   ```bash
   cd charliechat-terraform
   terraform init && terraform apply
   ```

3. **Run the application**
   ```bash
   cd ../charliechat-api
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. **Access the web interface**
   - Open `http://localhost:8000` in your browser
   - Start chatting with the AI assistant

## 📁 Project Structure

```
charliechat/
├── charliechat-api/          # FastAPI application
│   ├── README.md            # API documentation and setup
│   ├── ARCHITECTURE.md      # Technical architecture details
│   └── app/                 # Application code
├── charliechat-terraform/   # Infrastructure as code
│   └── README.md           # Infrastructure setup and deployment
├── training-data/           # Knowledge Base training data
│   └── README.md           # Training data documentation
├── .env-template           # Environment configuration template
└── README.md              # This file - project overview
```

## 📚 Documentation

- **[API Documentation](charliechat-api/README.md)** - Application setup, configuration, and usage
- **[Architecture Details](charliechat-api/ARCHITECTURE.md)** - Technical architecture and design patterns
- **[Infrastructure Setup](charliechat-terraform/README.md)** - AWS infrastructure deployment and management
- **[Training Data](training-data/README.md)** - Knowledge Base training data and setup

## 🛠 Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **AI**: AWS Bedrock (Claude 3)
- **NLP**: AWS Lex V2
- **Infrastructure**: Terraform
- **Deployment**: AWS Lambda + API Gateway
- **Frontend**: HTMX + SCSS

## ✨ Features

- **Natural Language Understanding** via AWS Lex V2
- **Intelligent Responses** powered by AWS Bedrock AI
- **Web Interface** with modern, responsive design
- **Session Management** for conversational context
- **Voice Style Options** (Normal, Surfer, Pirate, Ninja)
- **Knowledge Base Integration** for enhanced responses
- **Dev Journal** with Markdown support
- **Feedback System** for continuous improvement

## 🔧 Configuration

The application is highly configurable through environment variables. See the [API documentation](charliechat-api/README.md#configuration) for detailed configuration options.

## 🚀 Deployment

For production deployment, see the [Infrastructure documentation](charliechat-terraform/README.md) for detailed AWS setup instructions.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
