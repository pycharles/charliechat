# Charlie Chat Architecture

## Overview

This document describes the technical architecture of Charlie Chat, a layered application that combines AWS Lex V2 for natural language understanding with Bedrock AI for intelligent responses.

> **Note**: This is the technical architecture documentation for the Charlie Chat API. For the complete project overview, see the [root README](../README.md).

## Architecture Pattern

The application follows a **layered architecture pattern** with clear separation of concerns:

```
┌─────────────────┐
│   Web Layer     │ ← FastAPI routes, templates, static files
├─────────────────┤
│  Services Layer │ ← Business logic, AI integration, Lex handling
├─────────────────┤
│  Models Layer   │ ← Data validation and serialization
├─────────────────┤
│  Config Layer   │ ← Environment and application configuration
└─────────────────┘
```

## Layer Responsibilities

### Web Layer (`app/web/`)
- **Purpose**: Handles HTTP requests, responses, and presentation
- **Components**:
  - `routes.py` - FastAPI route definitions
  - `templates/` - HTML templates for web interface
  - `static/` - CSS, JavaScript, and static assets
- **Responsibilities**:
  - Request/response handling
  - Input validation
  - Content negotiation (HTML vs JSON)
  - Static file serving

### Services Layer (`app/services/`)
- **Purpose**: Contains business logic and external service integration
- **Components**:
  - `chat_service.py` - Orchestrates chat flow and session management
  - `lex_service.py` - Lex V2 integration and slot extraction
  - `ai_service.py` - Bedrock AI integration, Knowledge Base retrieval, and prompt building
- **Responsibilities**:
  - Business logic implementation
  - External API integration (Lex V2, Bedrock AI, Knowledge Base)
  - Session state management
  - Error handling and fallbacks
  - Knowledge Base context retrieval and integration

### Models Layer (`app/models/`)
- **Purpose**: Defines data structures and validation rules
- **Components**:
  - `chat.py` - Chat request/response models
  - `lex.py` - Lex V2 event and response models
- **Responsibilities**:
  - Data validation
  - Type safety
  - API contract definition
  - Serialization/deserialization

### Config Layer (`app/config.py`)
- **Purpose**: Centralizes configuration management
- **Responsibilities**:
  - Environment variable loading
  - Configuration validation
  - Default value management
  - Settings access

## Data Flow

### Chat Request Flow
```
User Input → Web Layer → Chat Service → Lex Service → AI Service → Response
     ↓              ↓           ↓            ↓           ↓
  HTML/JSON    Validation   Orchestration  Slot Extract  Bedrock AI
                                                          ↓
                                                   Knowledge Base
                                                      Context
```

### Session Management
```
Session State → Lex Service → Session Attributes → AI Context → Updated State
```

## Design Principles

### 1. Separation of Concerns
- Each layer has a single, well-defined responsibility
- Dependencies flow downward only
- No circular dependencies between layers

### 2. Dependency Injection
- Services are injected rather than instantiated
- Easy to mock for testing
- Flexible configuration

### 3. Error Handling
- Each layer handles its own errors appropriately
- Graceful degradation when possible
- Clear error messages for debugging

### 4. Configuration Management
- All configuration externalized to environment variables
- Sensible defaults for development
- Validation at startup

### 5. Testability
- Each layer can be tested independently
- Clear interfaces between layers
- Mockable dependencies

## Benefits

- **Maintainability**: Clear boundaries make code easier to understand and modify
- **Testability**: Each layer can be tested independently with appropriate mocks
- **Scalability**: Services can be extracted to separate microservices if needed
- **Flexibility**: Easy to swap implementations or add new features
- **Readability**: Code structure is self-documenting and intuitive

## Lambda Architecture

The application uses a single Lambda function for deployment:

### API Lambda (`lambda_api/`)
- **Purpose**: Web interface, API endpoints, and Lex integration
- **Handler**: `lambda_api.py` (Mangum wrapper)
- **Dependencies**: Full FastAPI stack + Lex + AI services
- **Use Cases**: Web UI, HTMX requests, JSON API, Lex integration
- **Deployment**: Simple single-function deployment

This simplified architecture reduces complexity while maintaining all functionality through the layered design pattern.