"""
Unit tests for PromptEngineering functionality.

This module tests the prompt engineering service's functionality including
KB context selection, summarization, and response length calculation.
"""

import pytest
from app.services.prompt_engineering import PromptEngineer


class TestPromptEngineer:
    """Test class for PromptEngineer functionality."""
    
    @pytest.fixture
    def prompt_engineer(self):
        """Create a PromptEngineer instance for testing."""
        return PromptEngineer()
    
    def test_get_kb_query_params_background_questions(self, prompt_engineer):
        """Test KB query parameters for background/experience questions."""
        params = prompt_engineer.get_kb_query_params("tell me about your background")
        assert params["numberOfResults"] == 3
        
        params = prompt_engineer.get_kb_query_params("what is your experience?")
        assert params["numberOfResults"] == 3
        
        params = prompt_engineer.get_kb_query_params("tell me about your career history")
        assert params["numberOfResults"] == 3
    
    def test_get_kb_query_params_skills_questions(self, prompt_engineer):
        """Test KB query parameters for skills/education questions."""
        params = prompt_engineer.get_kb_query_params("what are your skills?")
        assert params["numberOfResults"] == 2
        
        params = prompt_engineer.get_kb_query_params("tell me about your education")
        assert params["numberOfResults"] == 2
        
        params = prompt_engineer.get_kb_query_params("what certifications do you have?")
        assert params["numberOfResults"] == 2
    
    def test_get_kb_query_params_general_questions(self, prompt_engineer):
        """Test KB query parameters for general questions."""
        params = prompt_engineer.get_kb_query_params("hello")
        assert params["numberOfResults"] == 2
        
        params = prompt_engineer.get_kb_query_params("how are you?")
        assert params["numberOfResults"] == 2
        
        params = prompt_engineer.get_kb_query_params("what's the weather like?")
        assert params["numberOfResults"] == 2
    
    def test_select_kb_context(self, prompt_engineer):
        """Test KB context selection."""
        passages = [
            "Passage 1 about skills",
            "Passage 2 about experience",
            "Passage 3 about education"
        ]
        
        selected, query_results = prompt_engineer.select_kb_context("tell me about skills", passages)
        
        # Should return 2 passages for specific questions
        assert len(selected) == 2
        assert selected == passages[:2]
        assert query_results == 2
    
    def test_summarize_kb_context_disabled(self, prompt_engineer):
        """Test KB context summarization when disabled."""
        passages = [
            "Passage 1 about skills",
            "Passage 2 about experience"
        ]
        
        result = prompt_engineer.summarize_kb_context(passages)
        
        # Should return joined passages when summarization is disabled
        assert "Passage 1 about skills" in result
        assert "Passage 2 about experience" in result
        assert "\n\n" in result  # Should be joined with double newlines
    
    def test_summarize_kb_context_enabled(self, prompt_engineer):
        """Test KB context summarization when enabled."""
        # Enable summarization
        prompt_engineer.enable_kb_summarization = True
        
        passages = [
            "Passage 1 about skills",
            "Passage 2 about experience"
        ]
        
        result = prompt_engineer.summarize_kb_context(passages)
        
        # Should return summarized version with [Recent] prefix
        assert "[Recent]" in result
        assert "Passage 1 about skills" in result
        assert "Passage 2 about experience" in result
        assert "..." in result
    
    def test_calculate_response_length_short_questions(self, prompt_engineer):
        """Test response length calculation for short questions."""
        max_tokens = 1000
        
        # Greeting questions
        assert prompt_engineer.calculate_response_length("hi", max_tokens) == 100
        assert prompt_engineer.calculate_response_length("hello", max_tokens) == 100
        assert prompt_engineer.calculate_response_length("thanks", max_tokens) == 100
        assert prompt_engineer.calculate_response_length("yes", max_tokens) == 100
        assert prompt_engineer.calculate_response_length("no", max_tokens) == 100
    
    def test_calculate_response_length_education_questions(self, prompt_engineer):
        """Test response length calculation for education/skills questions."""
        max_tokens = 1000
        
        assert prompt_engineer.calculate_response_length("what is your education?", max_tokens) == 700
        assert prompt_engineer.calculate_response_length("tell me about your skills", max_tokens) == 700
        assert prompt_engineer.calculate_response_length("what certifications do you have?", max_tokens) == 700
        assert prompt_engineer.calculate_response_length("what projects have you done?", max_tokens) == 600
    
    def test_calculate_response_length_what_questions(self, prompt_engineer):
        """Test response length calculation for what/how/when/where/why questions."""
        max_tokens = 1000
        
        assert prompt_engineer.calculate_response_length("what is Python?", max_tokens) == 600
        assert prompt_engineer.calculate_response_length("how does it work?", max_tokens) == 600
        assert prompt_engineer.calculate_response_length("when did you start?", max_tokens) == 600
        assert prompt_engineer.calculate_response_length("where do you work?", max_tokens) == 600
        assert prompt_engineer.calculate_response_length("why did you choose this?", max_tokens) == 600
    
    def test_calculate_response_length_background_questions(self, prompt_engineer):
        """Test response length calculation for background/experience questions."""
        max_tokens = 1000
        
        assert prompt_engineer.calculate_response_length("tell me about your background", max_tokens) == 700
        assert prompt_engineer.calculate_response_length("what is your experience?", max_tokens) == 600
        assert prompt_engineer.calculate_response_length("tell me about your career", max_tokens) == 700
        assert prompt_engineer.calculate_response_length("tell me about yourself", max_tokens) == 700
    
    def test_calculate_response_length_general_questions(self, prompt_engineer):
        """Test response length calculation for general questions."""
        max_tokens = 1000
        
        assert prompt_engineer.calculate_response_length("random question", max_tokens) == 500
        assert prompt_engineer.calculate_response_length("tell me something", max_tokens) == 500
    
    def test_calculate_response_length_respects_max_tokens(self, prompt_engineer):
        """Test that response length calculation respects the max_tokens cap."""
        max_tokens = 200  # Low cap
        
        # Even background questions should be capped
        result = prompt_engineer.calculate_response_length("tell me about your background", max_tokens)
        assert result == 200
        
        # Short questions should still be short
        result = prompt_engineer.calculate_response_length("hi", max_tokens)
        assert result == 100
    
    def test_initialization(self, prompt_engineer):
        """Test PromptEngineer initialization."""
        # Should have enable_kb_summarization attribute
        assert hasattr(prompt_engineer, 'enable_kb_summarization')
        assert isinstance(prompt_engineer.enable_kb_summarization, bool)
