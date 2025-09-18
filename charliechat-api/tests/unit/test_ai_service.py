"""
Unit tests for AIService functionality.

This module tests the AI service's core functionality including
prompt building, Bedrock integration, and knowledge base retrieval.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.ai_service import AIService
from app.config import Settings


class TestAIService:
    """Test class for AIService functionality."""
    
    @pytest.fixture
    def ai_service(self, test_settings, mock_bedrock_client, mock_bedrock_agent_client):
        """Create an AIService instance for testing."""
        with patch('boto3.client') as mock_boto3_client:
            # Configure boto3.client to return our mocks
            mock_boto3_client.side_effect = lambda service_name: {
                'bedrock-runtime': mock_bedrock_client,
                'bedrock-agent-runtime': mock_bedrock_agent_client
            }[service_name]
            
            service = AIService()
            # Override the clients with our mocks
            service.bedrock_client = mock_bedrock_client
            service.bedrock_agent_client = mock_bedrock_agent_client
            return service
    
    def test_initialization(self, ai_service, test_settings):
        """Test that AIService initializes correctly."""
        # AIService now uses environment variables, so we need to check defaults
        assert ai_service.model_id is not None
        assert ai_service.max_tokens is not None
        assert ai_service.default_person is not None
        # Check that clients are properly initialized
        assert ai_service.bedrock_client is not None
        assert ai_service.bedrock_agent_client is not None
    
    def test_build_prompt_without_session_context(self, ai_service):
        """Test prompt building without conversation history."""
        prompt = ai_service.build_prompt(
            person="Charlie",
            question="tell me about skills",
            session_attributes=None,
            voice_style="normal"
        )
        
        assert "Charlie" in prompt
        assert "tell me about skills" in prompt
        assert "CONVERSATION CONTEXT" not in prompt
    
    def test_build_prompt_with_session_context(self, ai_service, sample_session_state):
        """Test prompt building with conversation history."""
        prompt = ai_service.build_prompt(
            person="Charlie",
            question="what were we just talking about?",
            session_attributes=sample_session_state,
            voice_style="normal"
        )
        
        assert "Charlie" in prompt
        assert "what were we just talking about?" in prompt
        assert "CONVERSATION CONTEXT" in prompt
        assert "tell me about skills" in prompt  # From conversation history
    
    def test_build_prompt_with_kb_context(self, ai_service):
        """Test prompt building with pre-selected KB context."""
        kb_context = "Charlie has skills in Python, AWS, and DevOps."
        
        prompt = ai_service.build_prompt(
            person="Charlie",
            question="tell me about skills",
            session_attributes=None,
            voice_style="normal",
            kb_context=kb_context
        )
        
        assert "Charlie" in prompt
        assert "tell me about skills" in prompt
        assert kb_context in prompt
    
    def test_retrieve_kb_context(self, ai_service, mock_bedrock_agent_client):
        """Test knowledge base context retrieval."""
        with patch.object(ai_service, 'bedrock_agent_client', mock_bedrock_agent_client):
            context = ai_service._retrieve_kb_context("tell me about skills", number_of_results=2)
        
        assert context is not None
        assert "Test knowledge base content" in context
        mock_bedrock_agent_client.retrieve.assert_called_once()
    
    def test_retrieve_kb_context_no_results(self, ai_service, mock_bedrock_agent_client):
        """Test knowledge base context retrieval when no results are found."""
        # Mock empty response
        mock_bedrock_agent_client.retrieve.return_value = {"retrievalResults": []}
        
        with patch.object(ai_service, 'bedrock_agent_client', mock_bedrock_agent_client):
            context = ai_service._retrieve_kb_context("random question", number_of_results=2)
        
        assert context == "No additional KB context available."
    
    def test_calculate_response_length(self, ai_service):
        """Test response length calculation based on question type."""
        # Short response for simple questions
        assert ai_service._calculate_response_length("hi") == 150
        assert ai_service._calculate_response_length("thanks") == 150
        
        # Medium response for specific questions
        assert ai_service._calculate_response_length("what is Python?") == 300
        assert ai_service._calculate_response_length("how does it work?") == 300
        
        # Longer response for complex questions
        assert ai_service._calculate_response_length("explain your experience") == 500
        assert ai_service._calculate_response_length("tell me about your background") == 500
        
        # Default length
        assert ai_service._calculate_response_length("random question") == ai_service.max_tokens
    
    def test_trim_answer(self, ai_service):
        """Test answer trimming functionality."""
        long_answer = "This is a very long answer. " * 100  # Very long answer
        trimmed = ai_service._trim_answer(long_answer, max_length=100)
        
        assert len(trimmed) < len(long_answer)
        # The trimming logic may trim at a sentence boundary or add "..."
        assert trimmed.endswith("...") or trimmed.endswith(".")
    
    def test_voice_style_instructions(self, ai_service):
        """Test voice style instruction generation."""
        normal_instructions = ai_service._get_voice_style_instructions("normal")
        assert normal_instructions == ""  # Normal style returns empty string
        
        surfer_instructions = ai_service._get_voice_style_instructions("surfer")
        assert "surfer" in surfer_instructions.lower()
        assert "dude" in surfer_instructions.lower()
        
        pirate_instructions = ai_service._get_voice_style_instructions("pirate")
        assert "pirate" in pirate_instructions.lower()
        assert "arr" in pirate_instructions.lower()
        
        ninja_instructions = ai_service._get_voice_style_instructions("ninja")
        assert "ninja" in ninja_instructions.lower()
        assert "stealth" in ninja_instructions.lower()
        
        # Test unknown style
        unknown_instructions = ai_service._get_voice_style_instructions("unknown")
        assert unknown_instructions == ""
    
    def test_query_bedrock_success(self, ai_service, mock_bedrock_client):
        """Test successful Bedrock query."""
        mock_response = {
            "body": Mock(read=Mock(return_value=b'{"content":[{"text":"Test response"}],"usage":{"input_tokens":100,"output_tokens":50}}'))
        }
        mock_bedrock_client.invoke_model.return_value = mock_response

        with patch.object(ai_service, 'bedrock_client', mock_bedrock_client):
            response, session_attributes = ai_service.query_bedrock(
                person="Charlie",
                question="test question",
                session_attributes=None,
                voice_style="normal",
                request_id="test-001"
            )
        
        assert response == "Test response"
        assert "conversation_history" in session_attributes
        assert len(session_attributes["conversation_history"]) == 1
        assert session_attributes["conversation_history"][0]["question"] == "test question"
    
    def test_query_bedrock_with_existing_session(self, ai_service, mock_bedrock_client, sample_session_state):
        """Test Bedrock query with existing session state."""
        mock_response = {
            "body": Mock(read=Mock(return_value=b'{"content":[{"text":"Test response"}],"usage":{"input_tokens":100,"output_tokens":50}}'))
        }
        mock_bedrock_client.invoke_model.return_value = mock_response

        with patch.object(ai_service, 'bedrock_client', mock_bedrock_client):
            response, session_attributes = ai_service.query_bedrock(
                person="Charlie",
                question="new question",
                session_attributes=sample_session_state,
                voice_style="normal",
                request_id="test-002"
            )
        
        assert response == "Test response"
        assert "conversation_history" in session_attributes
        # Should have 3 exchanges now (2 existing + 1 new)
        assert len(session_attributes["conversation_history"]) == 3
        assert session_attributes["conversation_history"][-1]["question"] == "new question"
    
    def test_query_bedrock_error_handling(self, ai_service, mock_bedrock_client):
        """Test Bedrock query error handling."""
        # Mock an error
        mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock error")

        with patch.object(ai_service, 'bedrock_client', mock_bedrock_client):
            response, session_attributes = ai_service.query_bedrock(
                person="Charlie",
                question="test question",
                session_attributes=None,
                voice_style="normal",
                request_id="test-003"
            )
        
        assert "trouble processing" in response.lower()
        assert "conversation_history" not in session_attributes
