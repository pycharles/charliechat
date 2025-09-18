"""
Pytest configuration and shared fixtures for Charlie Chat API tests.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch
from app.config import Settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Create test settings with environment variables for testing."""
    # Set test environment variables
    test_env = {
        "BEDROCK_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
        "BEDROCK_MAX_TOKENS": "1000",
        "BEDROCK_KB_ID": "test-kb-id",
        "DEFAULT_PERSON": "Charlie",
        "DEBUG_LOGGING_DEV": "false",
        "DEBUG_LOGGING_PROD": "false"
    }
    
    with patch.dict(os.environ, test_env):
        yield Settings()


@pytest.fixture
def mock_bedrock_client():
    """Create a mock Bedrock client for testing."""
    mock_client = Mock()
    mock_client.invoke_model.return_value = {
        "body": Mock(read=Mock(return_value=b'{"content":[{"text":"Test response"}],"usage":{"input_tokens":100,"output_tokens":50}}'))
    }
    return mock_client


@pytest.fixture
def mock_bedrock_agent_client():
    """Create a mock Bedrock Agent client for testing."""
    mock_client = Mock()
    mock_client.retrieve.return_value = {
        "retrievalResults": [
            {
                "content": {
                    "text": "Test knowledge base content 1"
                }
            },
            {
                "content": {
                    "text": "Test knowledge base content 2"
                }
            }
        ]
    }
    return mock_client


@pytest.fixture
def sample_session_state():
    """Create a sample session state for testing."""
    return {
        "conversation_history": [
            {
                "question": "tell me about skills",
                "answer": "Charlie has extensive experience in software engineering, cloud architecture, and DevOps."
            },
            {
                "question": "what were we just talking about?",
                "answer": "We were discussing Charlie's technical skills and experience."
            }
        ],
        "current_voice_style": "normal",
        "last_question": "what were we just talking about?",
        "last_answer": "We were discussing Charlie's technical skills and experience."
    }


@pytest.fixture
def sample_conversation_history():
    """Create sample conversation history for testing."""
    return [
        {
            "question": "tell me about skills",
            "answer": "Charlie has extensive experience in software engineering, cloud architecture, and DevOps."
        },
        {
            "question": "what were we just talking about?",
            "answer": "We were discussing Charlie's technical skills and experience."
        }
    ]
