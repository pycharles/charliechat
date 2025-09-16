"""
AI Service for Charlie Chat

This service handles all AI-related functionality including
Bedrock integration, prompt building, and response generation.
"""

import boto3
import json
import os
from typing import Dict, Any, Optional, Tuple


class AIService:
    """Service for AI integration with AWS Bedrock"""
    
    def __init__(self):
        """Initialize the AI service with environment configuration"""
        # Environment-driven configuration
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        self.max_tokens = int(os.getenv("BEDROCK_MAX_TOKENS", "500"))  # Reduced default
        self.default_person = os.getenv("DEFAULT_PERSON", "Charles")
        self.debug_logging = os.getenv("DEBUG_LOGGING", "false").lower() == "true"
        
        # Knowledge Base configuration
        self.bedrock_kb_id = os.getenv("BEDROCK_KB_ID")
        
        # System prompt configuration
        system_prompt_override = os.getenv("SYSTEM_PROMPT_TEMPLATE")
        self.system_prompt_template = (
            system_prompt_override if system_prompt_override 
            else self._get_default_system_prompt()
        )
        
        # Initialize Bedrock clients
        self.bedrock_client = boto3.client("bedrock-runtime")
        self.bedrock_agent_client = boto3.client("bedrock-agent-runtime")

    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt template"""
        return """
You are Charlie Chat, representing {person}. You are a software engineer and technical leader with extensive experience in:

- AWS cloud architecture and services (Lambda, API Gateway, Route53, Bedrock, Lex)
- Python development and FastAPI
- Terraform for infrastructure as code
- Full-stack web development
- Technical leadership and team management

Answer questions about {person}'s specific experience, skills, and background. Use a professional but chill surfer tone.
Be concise and helpful. Use short paragraphs. Avoid repetitive introductions.
If asked about general topics, relate them back to {person}'s experience when possible.

{context}

Question: {question}
"""

    def normalize_person_name(self, person_value: Optional[str]) -> str:
        """
        Normalize person name to a consistent value
        
        Args:
            person_value: Raw person value from Lex slot
            
        Returns:
            Normalized person name
        """
        if not person_value or not person_value.strip():
            return self.default_person
        
        # Simple normalization - could be enhanced with more sophisticated logic
        person = person_value.strip().lower()
        
        # Map common variations to standard name
        name_mapping = {
            "charlie": "Charles",
            "chaz": "Charles", 
            "charles o'brien": "Charles",
            "charles obrien": "Charles",
            "charles o brien": "Charles"
        }
        
        return name_mapping.get(person, person_value.strip().title())

    def _trim_answer(self, answer: str, max_length: int = 1200) -> str:
        """
        Trim answer for storage in session attributes
        
        Args:
            answer: Full answer text
            max_length: Maximum length to keep
            
        Returns:
            Trimmed answer text
        """
        answer = answer.strip()
        if len(answer) <= max_length:
            return answer
        return answer[:max_length] + "..."

    def build_prompt(self, person: str, question: str, session_attributes: Optional[Dict[str, Any]] = None, voice_style: str = "normal") -> str:
        """
        Build a conversational prompt for Bedrock with KB context integration
        
        Args:
            person: Person name to represent
            question: User's question
            session_attributes: Optional session context for follow-ups
            voice_style: Voice style for response tone
            
        Returns:
            Formatted prompt string with KB context
        """
        # Retrieve KB context
        kb_context = self._retrieve_kb_context(question)
        
        # Check if this is a first-time interaction
        is_first_interaction = not session_attributes or not session_attributes.get("last_answer")
        
        # Build context from session attributes
        session_context = ""
        if session_attributes and not is_first_interaction:
            last_question = session_attributes.get("last_question", "").strip()
            last_answer = session_attributes.get("last_answer", "").strip()
            
            if last_question and last_answer:
                session_context = f"Previous question: {last_question}\nPrevious answer: {last_answer}\n"
        
        # Combine session context and KB context
        combined_context = ""
        if session_context:
            combined_context += session_context
        if kb_context and kb_context != "No additional KB context available.":
            combined_context += f"Additional context from knowledge base:\n{kb_context}\n"
        
        # Get voice style instructions
        voice_instructions = self._get_voice_style_instructions(voice_style)
        
        # Build final prompt using system template
        final_prompt = self.system_prompt_template.format(
            person=person,
            question=question,
            context=combined_context.strip()
        )
        
        # Insert voice instructions after the first line
        lines = final_prompt.split('\n')
        if len(lines) > 1 and voice_instructions:
            lines.insert(1, f"\n{voice_instructions}\n")
            final_prompt = '\n'.join(lines)
        elif voice_instructions:
            final_prompt = f"{final_prompt}\n\n{voice_instructions}"
        
        if self.debug_logging:
            print("=== KB Context ===")
            print(kb_context)
            print("=== Final Prompt ===")
            print(final_prompt)
        
        return final_prompt

    def _get_voice_style_instructions(self, voice_style: str) -> str:
        """Get voice style specific instructions"""
        voice_instructions = {
            "normal": "",  # No additional instructions
            "surfer": "Respond in a chill surfer tone. Use friendly casual words like 'dude', 'awesome', 'totally', 'stoked'.",
            "pirate": "Respond like a pirate, playful but clear, throw in an occasional 'Arr' and use pirate speak like 'matey', 'ye', 'aye'.",
            "ninja": "Respond with ninja wisdom and stealth. Use mysterious, wise language with occasional references to the way of the ninja."
        }
        return voice_instructions.get(voice_style, "")

    def _retrieve_kb_context(self, question: str) -> str:
        """
        Retrieve context from Bedrock Knowledge Base
        
        Args:
            question: User's question to search for
            
        Returns:
            Concatenated KB context or fallback message
        """
        if not self.bedrock_kb_id:
            if self.debug_logging:
                print("[DEBUG] No BEDROCK_KB_ID configured, skipping KB retrieval")
            return "No additional KB context available."
        
        try:
            if self.debug_logging:
                print(f"[DEBUG] Retrieving KB context for question: {question}")
            
            # Call Bedrock Knowledge Base retrieve and generate
            response = self.bedrock_agent_client.retrieve_and_generate(
                knowledgeBaseId=self.bedrock_kb_id,
                input={"text": question}
            )
            
            # Extract retrieval results
            retrieval_results = response.get("retrievalResults", [])
            
            if not retrieval_results:
                if self.debug_logging:
                    print("[DEBUG] No KB results found")
                return "No additional KB context available."
            
            # Collect top 3-5 results and strip to plain text
            kb_texts = []
            for doc in retrieval_results[:5]:  # Top 5 results
                content = doc.get("content", {})
                text = content.get("text", "").strip()
                if text:
                    kb_texts.append(text)
            
            if not kb_texts:
                if self.debug_logging:
                    print("[DEBUG] No valid KB content found")
                return "No additional KB context available."
            
            # Concatenate and truncate to ~1500 characters
            combined_text = "\n".join(kb_texts)
            if len(combined_text) > 1500:
                combined_text = combined_text[:1500] + "..."
            
            if self.debug_logging:
                print(f"[DEBUG] Retrieved KB context ({len(combined_text)} chars): {combined_text[:200]}...")
            
            return combined_text
            
        except Exception as e:
            if self.debug_logging:
                print(f"[DEBUG] KB retrieval failed: {e}")
            return "No additional KB context available."

    def _calculate_response_length(self, question: str) -> int:
        """Calculate appropriate response length based on question complexity"""
        question_lower = question.lower()
        
        # Short responses for simple questions
        if any(word in question_lower for word in ['hi', 'hello', 'hey', 'thanks', 'bye', 'ok', 'yes', 'no']):
            return 150
        
        # Medium responses for specific questions
        if any(word in question_lower for word in ['what', 'how', 'when', 'where', 'why']):
            return 300
        
        # Longer responses for complex questions
        if any(word in question_lower for word in ['explain', 'describe', 'tell me about', 'experience', 'background']):
            return 500
        
        # Default length
        return self.max_tokens

    def query_bedrock(self, person: str, question: str, session_attributes: Optional[Dict[str, Any]] = None, voice_style: str = "normal") -> Tuple[str, Dict[str, Any]]:
        """
        Query Bedrock AI for a response
        
        Args:
            person: Person name to represent
            question: User's question
            session_attributes: Optional session context
            
        Returns:
            Tuple of (ai_response, updated_session_attributes)
        """
        try:
            # Use stored voice_style from session if available, otherwise use provided voice_style
            stored_voice_style = session_attributes.get('current_voice_style', voice_style) if session_attributes else voice_style
            
            # Build the prompt
            prompt = self.build_prompt(person, question, session_attributes, stored_voice_style)
            
            if self.debug_logging:
                print(f"[DEBUG] Full prompt: {prompt}")
            
            # Calculate dynamic response length
            response_length = self._calculate_response_length(question)
            
            # Prepare the request
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": response_length,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Call Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response["body"].read())
            ai_response = response_body["content"][0]["text"]
            
            if self.debug_logging:
                truncated_response = ai_response[:300] + "..." if len(ai_response) > 300 else ai_response
                print(f"[DEBUG] AI response: {truncated_response}")
            
            # Prepare updated session attributes
            updated_attributes = session_attributes.copy() if session_attributes else {}
            updated_attributes["last_answer"] = self._trim_answer(ai_response)
            updated_attributes["last_question"] = question.strip().replace('\n', ' ').replace('\r', ' ')
            updated_attributes["current_voice_style"] = stored_voice_style
            
            return ai_response, updated_attributes
            
        except Exception as e:
            print(f"Bedrock error: {e}")
            fallback_message = "I'm having trouble processing your request right now. Please try again."
            
            # Clear session attributes on error
            updated_attributes = session_attributes.copy() if session_attributes else {}
            updated_attributes.pop("last_answer", None)
            updated_attributes.pop("last_question", None)
            
            return fallback_message, updated_attributes
