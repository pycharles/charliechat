"""
Prompt Engineering Module

Handles custom prompt logic including:
- KB context selection based on question type
- Response length calculation
- KB context summarization
- Dynamic KB query parameters
"""

import os
import re
import random
from typing import List, Dict, Any, Tuple, Optional


class PromptEngineer:
    """Handles prompt engineering logic for Charlie Chat"""
    
    def __init__(self):
        self.debug_logging = os.getenv("DEBUG_LOGGING_DEV", "false").lower() == "true" or os.getenv("DEBUG_LOGGING_PROD", "false").lower() == "true"
        self.enable_kb_summarization = os.getenv("ENABLE_KB_SUMMARIZATION", "false").lower() == "true"
    
    def get_conciseness_style(self) -> str:
        """
        Generate a random conciseness style for the prompt
        
        Returns:
            String describing the conciseness style to use
        """
        conciseness_styles = [
            "very concise (around 300-500 characters)",   # for quick facts like education
            "concise (around 500-700 characters)",        # default short answer
            "medium (around 700-900 characters)"          # slightly more detailed, still brief
        ]
        selected_style = random.choice(conciseness_styles)
        
        if self.debug_logging:
            print(f"[DEBUG] Selected conciseness style: {selected_style}")
        
        return selected_style
    
    def select_kb_context(self, question: str, kb_passages: List[str]) -> Tuple[List[str], int]:
        """
        Select which KB passages to include based on question type
        
        Args:
            question: User's question
            kb_passages: List of KB passages retrieved
            
        Returns:
            Tuple of (selected_passages, number_of_results_for_query)
        """
        if not kb_passages:
            return [], 3  # Default to 3 if no passages
        
        question_lower = question.lower()
        
        # Determine question type
        is_background_question = any(word in question_lower for word in [
            "background", "experience", "career", "tell me about yourself", 
            "overview", "history", "story"
        ])
        
        is_specific_question = any(word in question_lower for word in [
            "education", "skills", "certifications", "degree", "school",
            "what is", "what are", "list", "show me"
        ])
        
        # Select passages based on question type
        if is_background_question:
            # For background questions, use up to 3 passages, prioritize recent experience
            selected = kb_passages[:3]
            query_results = 3
            if self.debug_logging:
                print(f"[DEBUG] Background question detected - using {len(selected)} passages")
        elif is_specific_question:
            # For specific questions, use only 1-2 most relevant passages
            selected = kb_passages[:2]
            query_results = 2
            if self.debug_logging:
                print(f"[DEBUG] Specific question detected - using {len(selected)} passages")
        else:
            # Default: use 2 passages
            selected = kb_passages[:2]
            query_results = 2
            if self.debug_logging:
                print(f"[DEBUG] General question - using {len(selected)} passages")
        
        if self.debug_logging:
            print(f"[DEBUG] Selected KB passages: {len(selected)} out of {len(kb_passages)} available")
            for i, passage in enumerate(selected):
                print(f"[DEBUG] Passage {i+1}: {passage[:100]}...")
        
        return selected, query_results
    
    def calculate_response_length(self, question: str, max_tokens: int = 1000) -> int:
        """
        Calculate appropriate response length based on question type
        
        Args:
            question: User's question
            max_tokens: Maximum tokens allowed
            
        Returns:
            Target token count for response
        """
        question_lower = question.lower().strip()
        
        # Greeting/acknowledgment patterns
        if re.match(r'^(hi|hello|hey|thanks?|thank you|yes|no|ok|okay|sure|yep|nope)$', question_lower):
            return min(100, max_tokens)
        
        # Simple attribute questions
        if any(word in question_lower for word in [
            "education", "degree", "school", "university", "college",
            "skills", "certifications", "cert", "certificate"
        ]):
            return min(700, max_tokens)  # Increased from 300 to 700 for more complete answers
        
        # Specific "what/how/when/where/why" questions
        if any(word in question_lower for word in [
            "what", "how", "when", "where", "why", "which", "who"
        ]):
            return min(600, max_tokens)  # Increased from 500 to 600 for more detailed answers
        
        # Full background or comprehensive questions
        if any(phrase in question_lower for phrase in [
            "tell me about yourself", "background", "experience", "career",
            "overview", "story", "history", "everything"
        ]):
            return min(700, max_tokens)
        
        # Default for other questions
        return min(500, max_tokens)  # Increased from 400 to 500 for better default responses
    
    def summarize_kb_context(self, passages: List[str]) -> str:
        """
        Summarize KB passages to reduce token usage
        
        Args:
            passages: List of KB passages
            
        Returns:
            Summarized context string
        """
        if not self.enable_kb_summarization or not passages:
            return "\n\n".join(passages)
        
        # Simple summarization: extract key points and dates
        summarized_parts = []
        
        for passage in passages:
            # Extract dates (YYYY format)
            dates = re.findall(r'\b(19|20)\d{2}\b', passage)
            if dates:
                date_range = f"{min(dates)}-{max(dates)}" if len(dates) > 1 else dates[0]
            else:
                date_range = "Recent"
            
            # Extract key points (lines starting with - or •)
            key_points = re.findall(r'[-•]\s*([^\n]+)', passage)
            if key_points:
                key_summary = "; ".join(key_points[:3])  # First 3 key points
                summarized_parts.append(f"[{date_range}] {key_summary}")
            else:
                # Fallback: first 200 characters
                summarized_parts.append(f"[{date_range}] {passage[:200]}...")
        
        if self.debug_logging:
            print(f"[DEBUG] KB summarization enabled - reduced {len(passages)} passages")
        
        return "\n\n".join(summarized_parts)
    
    def get_kb_query_params(self, question: str) -> Dict[str, Any]:
        """
        Get dynamic KB query parameters based on question type
        
        Args:
            question: User's question
            
        Returns:
            Dictionary of query parameters for Bedrock KB
        """
        question_lower = question.lower()
        
        # Determine question type and set numberOfResults accordingly
        is_background_question = any(word in question_lower for word in [
            "background", "experience", "career", "tell me about yourself", 
            "overview", "history", "story"
        ])
        
        is_specific_question = any(word in question_lower for word in [
            "education", "skills", "certifications", "degree", "school",
            "what is", "what are", "list", "show me"
        ])
        
        if is_background_question:
            number_of_results = 3
        elif is_specific_question:
            number_of_results = 2
        else:
            number_of_results = 2
        
        return {
            'numberOfResults': number_of_results
        }


# Create global instance
prompt_engineer = PromptEngineer()
