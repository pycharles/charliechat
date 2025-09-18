"""
Unit tests for ChatService session state preservation functionality.

This module tests the conversation context preservation across multiple chat requests,
ensuring that session state is properly maintained and conversation history is preserved.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from app.services.chat_service import ChatService
from app.config import Settings


class TestChatServiceSessionState:
    """Test class for ChatService session state functionality."""
    
    @pytest.fixture
    def settings(self):
        """Create a test settings instance."""
        return Settings()
    
    @pytest.fixture
    def chat_service(self, settings):
        """Create a ChatService instance for testing."""
        return ChatService(settings)
    
    @pytest.fixture
    def mock_ai_service(self):
        """Create a mock AI service for testing."""
        mock_ai = Mock()
        # Mock the KB context retrieval to return a list of passages
        mock_ai._retrieve_kb_context.return_value = "Passage 1 about skills\n\nPassage 2 about experience"
        return mock_ai
    
    @pytest.mark.asyncio
    async def test_first_request_creates_conversation_history(self, chat_service, mock_ai_service):
        """Test that the first request creates conversation history in session state."""
        # Mock the AI service response
        mock_response = "As an experienced software engineer, Charlie has skills in Python, AWS, and DevOps."
        mock_session_state = {
            "conversation_history": [
                {
                    "question": "tell me about skills",
                    "answer": mock_response
                }
            ],
            "current_voice_style": "normal",
            "last_question": "tell me about skills",
            "last_answer": mock_response
        }
        mock_ai_service.query_bedrock.return_value = (mock_response, mock_session_state)
        
        # Mock the prompt engineer methods
        with patch('app.services.chat_service.prompt_engineer') as mock_prompt_engineer:
            mock_prompt_engineer.get_kb_query_params.return_value = {"numberOfResults": 2}
            mock_prompt_engineer.select_kb_context.return_value = (["Passage 1", "Passage 2"], 2)
            mock_prompt_engineer.summarize_kb_context.return_value = "Summarized context"
            mock_prompt_engineer.calculate_response_length.return_value = 300
            
            # Patch the AI service in chat service
            with patch.object(chat_service, 'ai_service', mock_ai_service):
                response, session_state = await chat_service.process_chat(
                    request_id="test-001",
                    session_id="test-session-123",
                    text="tell me about skills",
                    session_state=None,
                    voice_style="normal"
                )
        
        # Assertions
        assert response == mock_response
        assert "conversation_history" in session_state
        assert len(session_state["conversation_history"]) == 1
        assert session_state["conversation_history"][0]["question"] == "tell me about skills"
        assert session_state["conversation_history"][0]["answer"] == mock_response
    
    @pytest.mark.asyncio
    async def test_education_follow_up_conversation(self, chat_service, mock_ai_service):
        """Test the specific education follow-up scenario: education -> what were we talking about."""
        # Mock the AI service response for follow-up question
        mock_response = "We were just discussing Charlie's education background, including his degree in Nuclear Engineering Technology from Thomas A. Edison University and various certifications."
        mock_session_state = {
            "conversation_history": [
                {
                    "question": "tell me about education",
                    "answer": "Charlie has a degree in Nuclear Engineering Technology from Thomas A. Edison University and holds certifications including CISSP and MCSE."
                },
                {
                    "question": "what were we just talking about?",
                    "answer": mock_response
                }
            ],
            "current_voice_style": "normal",
            "last_question": "what were we just talking about?",
            "last_answer": mock_response
        }
        mock_ai_service.query_bedrock.return_value = (mock_response, mock_session_state)
        
        # Initial session state from first request about education
        initial_session_state = {
            "conversation_history": [
                {
                    "question": "tell me about education",
                    "answer": "Charlie has a degree in Nuclear Engineering Technology from Thomas A. Edison University and holds certifications including CISSP and MCSE."
                }
            ],
            "current_voice_style": "normal",
            "last_question": "tell me about education",
            "last_answer": "Charlie has a degree in Nuclear Engineering Technology from Thomas A. Edison University and holds certifications including CISSP and MCSE."
        }
        
        # Mock the prompt engineer methods
        with patch('app.services.chat_service.prompt_engineer') as mock_prompt_engineer:
            mock_prompt_engineer.get_kb_query_params.return_value = {"numberOfResults": 2}
            mock_prompt_engineer.select_kb_context.return_value = (["Education passage 1", "Education passage 2"], 2)
            mock_prompt_engineer.summarize_kb_context.return_value = "Education context"
            mock_prompt_engineer.calculate_response_length.return_value = 500
            
            # Patch the AI service in chat service
            with patch.object(chat_service, 'ai_service', mock_ai_service):
                response, session_state = await chat_service.process_chat(
                    request_id="test-education-followup",
                    session_id="test-session-123",
                    text="what were we just talking about?",
                    session_state=initial_session_state,
                    voice_style="normal"
                )
        
        # Assertions - verify the response references the previous education discussion
        assert response == mock_response
        assert "education" in response.lower()  # Should reference education
        assert "conversation_history" in session_state
        assert len(session_state["conversation_history"]) == 2
        assert session_state["conversation_history"][0]["question"] == "tell me about education"
        assert session_state["conversation_history"][1]["question"] == "what were we just talking about?"
    
    @pytest.mark.asyncio
    async def test_second_request_preserves_conversation_history(self, chat_service, mock_ai_service):
        """Test that a second request preserves and extends conversation history."""
        # Mock the AI service response for second request
        mock_response = "In our previous conversation, we were discussing Charlie's skills in software engineering."
        mock_session_state = {
            "conversation_history": [
                {
                    "question": "tell me about skills",
                    "answer": "Previous response about skills"
                },
                {
                    "question": "what were we just talking about?",
                    "answer": mock_response
                }
            ],
            "current_voice_style": "normal",
            "last_question": "what were we just talking about?",
            "last_answer": mock_response
        }
        mock_ai_service.query_bedrock.return_value = (mock_response, mock_session_state)
        
        # Initial session state from first request
        initial_session_state = {
            "conversation_history": [
                {
                    "question": "tell me about skills",
                    "answer": "Previous response about skills"
                }
            ],
            "current_voice_style": "normal",
            "last_question": "tell me about skills",
            "last_answer": "Previous response about skills"
        }
        
        # Mock the prompt engineer methods
        with patch('app.services.chat_service.prompt_engineer') as mock_prompt_engineer:
            mock_prompt_engineer.get_kb_query_params.return_value = {"numberOfResults": 2}
            mock_prompt_engineer.select_kb_context.return_value = (["Passage 1", "Passage 2"], 2)
            mock_prompt_engineer.summarize_kb_context.return_value = "Summarized context"
            mock_prompt_engineer.calculate_response_length.return_value = 500
            
            # Patch the AI service in chat service
            with patch.object(chat_service, 'ai_service', mock_ai_service):
                response, session_state = await chat_service.process_chat(
                    request_id="test-002",
                    session_id="test-session-123",
                    text="what were we just talking about?",
                    session_state=initial_session_state,
                    voice_style="normal"
                )
        
        # Assertions
        assert response == mock_response
        assert "conversation_history" in session_state
        assert len(session_state["conversation_history"]) == 2
        assert session_state["conversation_history"][0]["question"] == "tell me about skills"
        assert session_state["conversation_history"][1]["question"] == "what were we just talking about?"
    
    @pytest.mark.asyncio
    async def test_conversation_history_limit(self, chat_service, mock_ai_service):
        """Test that conversation history is limited to prevent token overflow."""
        # Create a session state with 3 exchanges (the limit)
        initial_session_state = {
            "conversation_history": [
                {"question": "Q1", "answer": "A1"},
                {"question": "Q2", "answer": "A2"},
                {"question": "Q3", "answer": "A3"}
            ],
            "current_voice_style": "normal"
        }
        
        mock_response = "This is the 4th response."
        mock_session_state = {
            "conversation_history": [
                {"question": "Q2", "answer": "A2"},
                {"question": "Q3", "answer": "A3"},
                {"question": "Q4", "answer": mock_response}
            ],
            "current_voice_style": "normal"
        }
        mock_ai_service.query_bedrock.return_value = (mock_response, mock_session_state)
        
        # Mock the prompt engineer methods
        with patch('app.services.chat_service.prompt_engineer') as mock_prompt_engineer:
            mock_prompt_engineer.get_kb_query_params.return_value = {"numberOfResults": 2}
            mock_prompt_engineer.select_kb_context.return_value = (["Passage 1", "Passage 2"], 2)
            mock_prompt_engineer.summarize_kb_context.return_value = "Summarized context"
            mock_prompt_engineer.calculate_response_length.return_value = 400
            
            # Patch the AI service in chat service
            with patch.object(chat_service, 'ai_service', mock_ai_service):
                response, session_state = await chat_service.process_chat(
                    request_id="test-003",
                    session_id="test-session-123",
                    text="Q4",
                    session_state=initial_session_state,
                    voice_style="normal"
                )
        
        # Assertions
        assert response == mock_response
        assert len(session_state["conversation_history"]) == 3  # Should be limited to 3
        assert session_state["conversation_history"][0]["question"] == "Q2"  # Oldest removed
        assert session_state["conversation_history"][2]["question"] == "Q4"  # Newest added
    
    def test_json_serialization_roundtrip(self):
        """Test that session state can be serialized and deserialized correctly."""
        # Create a complex session state
        original_session_state = {
            "conversation_history": [
                {
                    "question": "tell me about skills",
                    "answer": "Charlie has skills in Python, AWS, and DevOps."
                },
                {
                    "question": "what were we just talking about?",
                    "answer": "We were discussing Charlie's technical skills."
                }
            ],
            "current_voice_style": "normal",
            "last_question": "what were we just talking about?",
            "last_answer": "We were discussing Charlie's technical skills."
        }
        
        # Serialize to JSON
        session_state_json = json.dumps(original_session_state)
        
        # Deserialize from JSON
        parsed_session_state = json.loads(session_state_json)
        
        # Assertions
        assert parsed_session_state == original_session_state
        assert len(parsed_session_state["conversation_history"]) == 2
        assert parsed_session_state["conversation_history"][0]["question"] == "tell me about skills"
    
    @pytest.mark.asyncio
    async def test_empty_session_state_handling(self, chat_service, mock_ai_service):
        """Test that empty or None session state is handled gracefully."""
        mock_response = "This is a new conversation."
        mock_session_state = {
            "conversation_history": [
                {
                    "question": "hello",
                    "answer": mock_response
                }
            ],
            "current_voice_style": "normal"
        }
        mock_ai_service.query_bedrock.return_value = (mock_response, mock_session_state)
        
        # Mock the prompt engineer methods
        with patch('app.services.chat_service.prompt_engineer') as mock_prompt_engineer:
            mock_prompt_engineer.get_kb_query_params.return_value = {"numberOfResults": 2}
            mock_prompt_engineer.select_kb_context.return_value = (["Passage 1", "Passage 2"], 2)
            mock_prompt_engineer.summarize_kb_context.return_value = "Summarized context"
            mock_prompt_engineer.calculate_response_length.return_value = 100
            
            # Patch the AI service in chat service
            with patch.object(chat_service, 'ai_service', mock_ai_service):
                response, session_state = await chat_service.process_chat(
                    request_id="test-004",
                    session_id="test-session-123",
                    text="hello",
                    session_state=None,  # No initial session state
                    voice_style="normal"
                )
        
        # Assertions
        assert response == mock_response
        assert "conversation_history" in session_state
        assert len(session_state["conversation_history"]) == 1
    
    @pytest.mark.asyncio
    async def test_malformed_session_state_handling(self, chat_service, mock_ai_service):
        """Test that malformed session state is handled gracefully."""
        mock_response = "This is a new conversation despite malformed input."
        mock_session_state = {
            "conversation_history": [
                {
                    "question": "hello",
                    "answer": mock_response
                }
            ],
            "current_voice_style": "normal"
        }
        mock_ai_service.query_bedrock.return_value = (mock_response, mock_session_state)
        
        # Mock the prompt engineer methods
        with patch('app.services.chat_service.prompt_engineer') as mock_prompt_engineer:
            mock_prompt_engineer.get_kb_query_params.return_value = {"numberOfResults": 2}
            mock_prompt_engineer.select_kb_context.return_value = (["Passage 1", "Passage 2"], 2)
            mock_prompt_engineer.summarize_kb_context.return_value = "Summarized context"
            mock_prompt_engineer.calculate_response_length.return_value = 100
            
            # Patch the AI service in chat service
            with patch.object(chat_service, 'ai_service', mock_ai_service):
                response, session_state = await chat_service.process_chat(
                    request_id="test-005",
                    session_id="test-session-123",
                    text="hello",
                    session_state={"invalid": "json"},  # Malformed session state
                    voice_style="normal"
                )
        
        # Assertions - should still work despite malformed input
        assert response == mock_response
        assert "conversation_history" in session_state
    
    @pytest.mark.asyncio
    async def test_conversation_context_passed_to_ai_service(self, chat_service, mock_ai_service):
        """Test that conversation context is properly passed to the AI service."""
        # Mock the AI service to capture the call parameters
        mock_ai_service.query_bedrock = Mock(return_value=("Test response", {"conversation_history": []}))
        
        # Initial session state with conversation history
        initial_session_state = {
            "conversation_history": [
                {
                    "question": "tell me about education",
                    "answer": "Charlie has a degree in Nuclear Engineering Technology."
                }
            ],
            "current_voice_style": "normal"
        }
        
        # Mock the prompt engineer methods
        with patch('app.services.chat_service.prompt_engineer') as mock_prompt_engineer:
            mock_prompt_engineer.get_kb_query_params.return_value = {"numberOfResults": 2}
            mock_prompt_engineer.select_kb_context.return_value = (["Passage 1", "Passage 2"], 2)
            mock_prompt_engineer.summarize_kb_context.return_value = "Summarized context"
            mock_prompt_engineer.calculate_response_length.return_value = 500
            
            # Patch the AI service in chat service
            with patch.object(chat_service, 'ai_service', mock_ai_service):
                response, session_state = await chat_service.process_chat(
                    request_id="test-context-passing",
                    session_id="test-session-123",
                    text="what were we just talking about?",
                    session_state=initial_session_state,
                    voice_style="normal"
                )
        
        # Verify that query_bedrock was called with the session attributes containing conversation history
        mock_ai_service.query_bedrock.assert_called_once()
        call_args = mock_ai_service.query_bedrock.call_args
        
        # Check that session_attributes contains the conversation history
        session_attributes = call_args.kwargs['session_attributes']
        assert 'conversation_history' in session_attributes
        assert len(session_attributes['conversation_history']) == 1
        assert session_attributes['conversation_history'][0]['question'] == "tell me about education"
        assert session_attributes['conversation_history'][0]['answer'] == "Charlie has a degree in Nuclear Engineering Technology."
    
    @pytest.mark.asyncio
    async def test_aws_follow_up_conversation(self, chat_service, mock_ai_service):
        """Test the AWS follow-up scenario from the user's example."""
        # First request: ask about education
        education_response = "Charles has a B.S. in Nuclear Engineering Technology and a Master's degree in IT with a specialization in Information Assurance and Security."
        education_session_state = {
            "conversation_history": [
                {
                    "question": "tell me about education",
                    "answer": education_response
                }
            ],
            "current_voice_style": "normal",
            "last_question": "tell me about education",
            "last_answer": education_response
        }
        mock_ai_service.query_bedrock.return_value = (education_response, education_session_state)
        
        # Mock the prompt engineer methods
        with patch('app.services.chat_service.prompt_engineer') as mock_prompt_engineer:
            mock_prompt_engineer.get_kb_query_params.return_value = {"numberOfResults": 2}
            mock_prompt_engineer.select_kb_context.return_value = (["Passage 1", "Passage 2"], 2)
            mock_prompt_engineer.summarize_kb_context.return_value = "Summarized context"
            mock_prompt_engineer.calculate_response_length.return_value = 400
            
            # Patch the AI service in chat service
            with patch.object(chat_service, 'ai_service', mock_ai_service):
                response1, session_state1 = await chat_service.process_chat(
                    request_id="test-aws-001",
                    session_id="test-aws-session",
                    text="tell me about education",
                    session_state=None,
                    voice_style="normal"
                )
        
        # Second request: follow-up about what we were talking about
        follow_up_response = "We were discussing Charles's education background, specifically his nuclear engineering and IT degrees."
        follow_up_session_state = {
            "conversation_history": [
                {
                    "question": "tell me about education",
                    "answer": education_response
                },
                {
                    "question": "what were we just talking about",
                    "answer": follow_up_response
                }
            ],
            "current_voice_style": "normal",
            "last_question": "what were we just talking about",
            "last_answer": follow_up_response
        }
        mock_ai_service.query_bedrock.return_value = (follow_up_response, follow_up_session_state)
        
        with patch('app.services.chat_service.prompt_engineer') as mock_prompt_engineer:
            mock_prompt_engineer.get_kb_query_params.return_value = {"numberOfResults": 2}
            mock_prompt_engineer.select_kb_context.return_value = (["Passage 1", "Passage 2"], 2)
            mock_prompt_engineer.summarize_kb_context.return_value = "Summarized context"
            mock_prompt_engineer.calculate_response_length.return_value = 400
            
            with patch.object(chat_service, 'ai_service', mock_ai_service):
                response2, session_state2 = await chat_service.process_chat(
                    request_id="test-aws-002",
                    session_id="test-aws-session",
                    text="what were we just talking about",
                    session_state=session_state1,
                    voice_style="normal"
                )
        
        # Third request: ask about AWS (should reference previous education context)
        aws_response = "Based on the previous discussion about Charles's education, he has experience with AWS cloud infrastructure and migrations."
        aws_session_state = {
            "conversation_history": [
                {
                    "question": "tell me about education",
                    "answer": education_response
                },
                {
                    "question": "what were we just talking about",
                    "answer": follow_up_response
                },
                {
                    "question": "tell me about aws",
                    "answer": aws_response
                }
            ],
            "current_voice_style": "normal",
            "last_question": "tell me about aws",
            "last_answer": aws_response
        }
        mock_ai_service.query_bedrock.return_value = (aws_response, aws_session_state)
        
        with patch('app.services.chat_service.prompt_engineer') as mock_prompt_engineer:
            mock_prompt_engineer.get_kb_query_params.return_value = {"numberOfResults": 2}
            mock_prompt_engineer.select_kb_context.return_value = (["Passage 1", "Passage 2"], 2)
            mock_prompt_engineer.summarize_kb_context.return_value = "Summarized context"
            mock_prompt_engineer.calculate_response_length.return_value = 400
            
            with patch.object(chat_service, 'ai_service', mock_ai_service):
                response3, session_state3 = await chat_service.process_chat(
                    request_id="test-aws-003",
                    session_id="test-aws-session",
                    text="tell me about aws",
                    session_state=session_state2,
                    voice_style="normal"
                )
        
        # Assertions
        assert response1 == education_response
        assert response2 == follow_up_response
        assert response3 == aws_response
        assert len(session_state3["conversation_history"]) == 3
        
        # Verify conversation history is maintained correctly
        assert session_state3["conversation_history"][0]["question"] == "tell me about education"
        assert session_state3["conversation_history"][1]["question"] == "what were we just talking about"
        assert session_state3["conversation_history"][2]["question"] == "tell me about aws"
        
        # Verify that the AI service was called with conversation context
        call_args = mock_ai_service.query_bedrock.call_args_list[2]  # Third call
        passed_session_attributes = call_args[1]['session_attributes']
        assert "conversation_history" in passed_session_attributes
        assert len(passed_session_attributes["conversation_history"]) == 2  # Previous 2 exchanges


class TestSessionStateIntegration:
    """Integration tests for session state across the full request flow."""
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test a complete conversation flow with multiple turns."""
        # This would be an integration test that tests the full stack
        # For now, we'll mark it as a placeholder
        pytest.skip("Integration test - requires full app setup")
    
    @pytest.mark.asyncio
    async def test_htmx_session_state_roundtrip(self):
        """Test that session state works correctly with HTMX frontend."""
        # This would test the actual HTMX interaction
        pytest.skip("Integration test - requires frontend testing")
