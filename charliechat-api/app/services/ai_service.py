"""
AI Service for Charlie Chat

This service handles all AI-related functionality including
Bedrock integration, prompt building, and response generation.
"""

import boto3
import json
import os
import re
from typing import Dict, Any, Optional, Tuple
from ..utils.debug_logger import debug_logger


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

CONVERSATION GUIDELINES:
- Act naturally in conversation - don't introduce yourself repeatedly
- Reference previous topics when relevant (e.g., "As I mentioned earlier...", "Building on what we discussed...")
- Use a professional but chill surfer tone
- Be concise and helpful with short paragraphs
- If asked about general topics, relate them back to {person}'s experience when possible
- Only introduce yourself on the very first interaction

IMPORTANT: Use the specific context provided below to answer questions about {person}'s experience, skills, and background. Do not give generic responses - always reference the specific details provided in the context.

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

    def _trim_answer(self, answer: str, max_length: Optional[int] = None) -> str:
        """
        Trim answer for storage in session attributes
        
        Args:
            answer: Full answer text
            max_length: Maximum length to keep. If None, returns full answer untrimmed.
            
        Returns:
            Trimmed answer text (or full answer if max_length is None)
        """
        answer = answer.strip()
        
        # If no max_length specified, return full answer
        if max_length is None:
            return answer
            
        if len(answer) <= max_length:
            return answer
        
        # Try to trim at a sentence boundary instead of arbitrary character limit
        trimmed = answer[:max_length]
        last_period = trimmed.rfind('.')
        last_newline = trimmed.rfind('\n')
        
        # Use the last sentence boundary if it's within reasonable range
        if last_period > max_length * 0.8:  # If period is in last 20% of text
            return answer[:last_period + 1]
        elif last_newline > max_length * 0.8:  # If newline is in last 20% of text
            return answer[:last_newline]
        else:
            return answer[:max_length] + "..."
    
    def _convert_to_first_person(self, text: str) -> str:
        """
        Convert third-person references to Charles to first-person.
        
        This method preprocesses knowledge base context to make it more natural
        when used in first-person responses.
        
        Args:
            text: The text to convert (typically KB context)
            
        Returns:
            Text with Charles references converted to first person
        """
        if not text or not isinstance(text, str):
            return text
        
        # Store original for debug logging
        original_text = text
        
        # Pattern 1: "Charles O'Brien" -> "I"
        text = re.sub(r'\bCharles\s+O\'?Brien\b', 'I', text, flags=re.IGNORECASE)
        
        # Pattern 2: "Charles Obrien" (without apostrophe) -> "I"
        text = re.sub(r'\bCharles\s+Obrien\b', 'I', text, flags=re.IGNORECASE)
        
        # Pattern 3: "Charles" (standalone, but be more careful about other names)
        # Only replace "Charles" if it's not followed by another capitalized word (like "Charles Dickens")
        # Use a more specific pattern to avoid false positives
        text = re.sub(r'\bCharles\b(?!\s+[A-Z][a-z])', 'I', text)
        
        # Pattern 4: "he" -> "I" (when referring to Charles)
        # Be more careful with "he" to avoid changing unrelated pronouns
        text = re.sub(r'\bhe\b', 'I', text, flags=re.IGNORECASE)
        
        # Pattern 5: "his" -> "my"
        text = re.sub(r'\bhis\b', 'my', text, flags=re.IGNORECASE)
        
        # Pattern 6: "him" -> "me"
        text = re.sub(r'\bhim\b', 'me', text, flags=re.IGNORECASE)
        
        # Pattern 7: "His" -> "My" (capitalized)
        text = re.sub(r'\bHis\b', 'My', text)
        
        # Pattern 8: "Him" -> "Me" (capitalized)
        text = re.sub(r'\bHim\b', 'Me', text)
        
        # Fix verb conjugations that might have been affected
        # "I has" -> "I have"
        text = re.sub(r'\bI\s+has\b', 'I have', text, flags=re.IGNORECASE)
        # "I is" -> "I am"
        text = re.sub(r'\bI\s+is\b', 'I am', text, flags=re.IGNORECASE)
        # "I was" -> "I was" (keep as is)
        # "I were" -> "I was" (fix subjunctive)
        text = re.sub(r'\bI\s+were\b', 'I was', text, flags=re.IGNORECASE)
        # "I delivers" -> "I deliver" (fix third person singular)
        text = re.sub(r'\bI\s+delivers\b', 'I deliver', text, flags=re.IGNORECASE)
        # "I consistently delivers" -> "I consistently deliver" (fix with adverb)
        text = re.sub(r'\bI\s+(\w+)\s+delivers\b', r'I \1 deliver', text, flags=re.IGNORECASE)
        # "I has" -> "I have" (with adverb)
        text = re.sub(r'\bI\s+(\w+)\s+has\b', r'I \1 have', text, flags=re.IGNORECASE)
        # "I, a technology leader, has" -> "I, a technology leader, have" (with comma)
        text = re.sub(r'\bI,\s+(\w+\s+\w+),\s+has\b', r'I, \1, have', text, flags=re.IGNORECASE)
        
        # Fix capitalization issues
        # "my" -> "My" when it starts a sentence
        text = re.sub(r'(^|\.\s+)my\b', r'\1My', text)
        # "me" -> "Me" when it starts a sentence
        text = re.sub(r'(^|\.\s+)me\b', r'\1Me', text)
        
        # Debug logging if text was changed
        if self.debug_logging and text != original_text:
            debug_logger.log_ai(
                "KB_FIRST_PERSON",
                f"Converted KB context to first person: {original_text[:100]}... -> {text[:100]}...",
                None
            )
        
        return text

    def build_prompt(self, person: str, question: str, session_attributes: Optional[Dict[str, Any]] = None, voice_style: str = "normal", kb_context: Optional[str] = None) -> str:
        """
        Build a conversational prompt for Bedrock with KB context integration
        
        Args:
            person: Person name to represent
            question: User's question
            session_attributes: Optional session context for follow-ups
            voice_style: Voice style for response tone
            kb_context: Pre-selected KB context (optional)
            
        Returns:
            Formatted prompt string with KB context
        """
        # Use provided KB context or retrieve it
        if kb_context is None:
            kb_context = self._retrieve_kb_context(question)
        
        # Check if this is a first-time interaction
        is_first_interaction = not session_attributes or not session_attributes.get("conversation_history")
        
        # Debug logging for session attributes
        if self.debug_logging:
            debug_logger.log_ai(
                "SESSION_DEBUG",
                f"Session attributes: {session_attributes}, First interaction: {is_first_interaction}",
                None
            )
        
        # Build context from session attributes
        session_context = ""
        if session_attributes and not is_first_interaction:
            conversation_history = session_attributes.get("conversation_history", [])
            if conversation_history:
                session_context = "CONVERSATION CONTEXT:\n"
                for i, exchange in enumerate(conversation_history[-2:], 1):  # Last 2 exchanges
                    session_context += f"Q{i}: {exchange['question']}\n"
                    session_context += f"A{i}: {exchange['answer']}\n\n"
                if self.debug_logging:
                    debug_logger.log_ai("SESSION_CONTEXT", f"Built session context: {session_context[:200]}...", None)
        
        # Combine session context and KB context
        combined_context = ""
        if session_context:
            combined_context += session_context
        if kb_context and kb_context != "No additional KB context available.":
            # Convert KB context to first person before adding to prompt
            # COMMENTED OUT: Testing if model responds in first person without this conversion
            # first_person_kb_context = self._convert_to_first_person(kb_context)
            # combined_context += f"Additional context from knowledge base:\n{first_person_kb_context}\n"
            
            # Use original KB context without first-person conversion
            combined_context += f"Additional context from knowledge base:\n{kb_context}\n"
        
        # Get voice style instructions
        voice_instructions = self._get_voice_style_instructions(voice_style)
        
        # Get conciseness style from prompt engineering
        from .prompt_engineering import prompt_engineer
        conciseness_style = prompt_engineer.get_conciseness_style()
        
        # Debug log the conciseness style being used
        if self.debug_logging:
            debug_logger.log_ai("CONCISENESS", f"Selected conciseness style: {conciseness_style}", None)
        
        # Build final prompt using system template
        final_prompt = self.system_prompt_template.format(
            person=person,
            question=question,
            context=combined_context.strip(),
            conciseness_style=conciseness_style
        )
        
        # Debug log the full prompt to verify conciseness style is included
        if self.debug_logging:
            debug_logger.log_ai("PROMPT", f"Prompt length: {len(final_prompt)} characters", None)
            debug_logger.log_ai("PROMPT", f"Full prompt: {final_prompt}", None)
        
        # Insert voice instructions after the first line
        lines = final_prompt.split('\n')
        if len(lines) > 1 and voice_instructions:
            lines.insert(1, f"\n{voice_instructions}\n")
            final_prompt = '\n'.join(lines)
        elif voice_instructions:
            final_prompt = f"{final_prompt}\n\n{voice_instructions}"
        
        if self.debug_logging:
            debug_logger.log_ai("KB_CONTEXT", f"KB Context: {kb_context}", None)
            debug_logger.log_ai("FINAL_PROMPT", f"Final prompt: {final_prompt}", None)
        
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

    def _retrieve_kb_context(self, question: str, number_of_results: int = 3) -> str:
        """
        Retrieve context from Bedrock Knowledge Base
        
        Args:
            question: User's question to search for
            number_of_results: Number of results to retrieve (1-3)
            
        Returns:
            Concatenated KB context or fallback message
        """
        if not self.bedrock_kb_id:
            if self.debug_logging:
                debug_logger.log_ai("KB_RETRIEVAL", "No BEDROCK_KB_ID configured, skipping KB retrieval", None)
            return "No additional KB context available."
        
        try:
            if self.debug_logging:
                debug_logger.log_ai("KB_RETRIEVAL", f"Retrieving KB context for question: {question}", None)
            
            # Call Bedrock Knowledge Base retrieve (not generate)
            response = self.bedrock_agent_client.retrieve(
                knowledgeBaseId=self.bedrock_kb_id,
                retrievalQuery={'text': question},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': number_of_results
                    }
                }
            )
            
            # Extract and combine retrieved passages
            if 'retrievalResults' in response:
                passages = []
                for result in response['retrievalResults']:
                    if 'content' in result and 'text' in result['content']:
                        passages.append(result['content']['text'].strip())
                
                if passages:
                    kb_text = "\n\n".join(passages)
                    if self.debug_logging:
                        debug_logger.log_ai("KB_RETRIEVAL", f"KB retrieved {len(passages)} passages: {kb_text[:200]}...", None)
                    return kb_text
                else:
                    if self.debug_logging:
                        debug_logger.log_ai("KB_RETRIEVAL", "No passages found in KB response", None)
                    return "No additional KB context available."
            else:
                if self.debug_logging:
                    debug_logger.log_ai("KB_RETRIEVAL", "No retrieval results found in response", None)
                return "No additional KB context available."
            
        except Exception as e:
            if self.debug_logging:
                debug_logger.log_ai("KB_RETRIEVAL", f"KB retrieval failed: {e}", None)
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

    def query_bedrock(self, person: str, question: str, session_attributes: Optional[Dict[str, Any]] = None, voice_style: str = "normal", request_id: Optional[str] = None, request: Optional[Any] = None, kb_context: Optional[str] = None, response_length: Optional[int] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Query Bedrock AI for a response
        
        Args:
            person: Person name to represent
            question: User's question
            session_attributes: Optional session context
            voice_style: Voice style for response tone
            request_id: Optional request ID for logging consistency
            request: Optional FastAPI request object for timing
            kb_context: Pre-selected KB context (optional)
            response_length: Pre-calculated response length (optional)
            
        Returns:
            Tuple of (ai_response, updated_session_attributes)
        """
        # Use provided request ID or generate one
        if not request_id:
            import uuid
            request_id = str(uuid.uuid4())[:8]
        
        try:
            debug_logger.log_ai(
                request_id,
                f"Starting Bedrock query for person: {person}, question: '{question[:50]}{'...' if len(question) > 50 else ''}'",
                request
            )
            
            # Use provided voice_style parameter (from current request) instead of stored session value
            # This ensures the current user selection takes precedence over stored session state
            current_voice_style = voice_style
            
            # Build the prompt
            debug_logger.log_ai(request_id, "Building prompt with context", request)
            prompt = self.build_prompt(person, question, session_attributes, current_voice_style, kb_context)
            
            
            # Use provided response length or calculate default
            if response_length is None:
                response_length = self._calculate_response_length(question)
            debug_logger.log_ai(request_id, f"Using response length: {response_length} tokens", request)
            
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
            debug_logger.log_ai(request_id, f"Calling Bedrock with model: {self.model_id}", request)
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            debug_logger.log_ai(request_id, "Bedrock API call completed", request)
            
            # Parse response
            response_body = json.loads(response["body"].read())
            ai_response = response_body["content"][0]["text"]
            
            # Log token usage
            if "usage" in response_body:
                usage = response_body["usage"]
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                total_tokens = input_tokens + output_tokens
                debug_logger.log_ai(request_id, f"Token usage - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}", request)
            else:
                debug_logger.log_ai(request_id, "Token usage not available in response", request)
            
            if self.debug_logging:
                debug_logger.log_ai(request_id, f"Raw response length: {len(ai_response)} characters", request)
                debug_logger.log_ai(request_id, f"Token limit used: {response_length} tokens", request)
            
            # Prepare updated session attributes
            updated_attributes = session_attributes.copy() if session_attributes else {}
            
            # Store FULL answer for user (no truncation)
            updated_attributes["last_answer"] = ai_response
            updated_attributes["last_question"] = question.strip().replace('\n', ' ').replace('\r', ' ')
            updated_attributes["current_voice_style"] = current_voice_style
            
            # Debug log to confirm full answer is stored
            if self.debug_logging:
                debug_logger.log_ai(request_id, f"Storing full answer ({len(ai_response)} chars) in last_answer", request)
            
            # Build conversation history with trimmed answer to keep token usage low
            conversation_history = updated_attributes.get("conversation_history", [])
            trimmed_for_history = self._trim_answer(ai_response, max_length=1200)
            
            # Debug log when answer is trimmed for history
            if self.debug_logging and len(ai_response) > 1200:
                debug_logger.log_ai(
                    request_id,
                    f"Trimmed for history: {len(ai_response)} -> {len(trimmed_for_history)} chars",
                    request
                )
            
            conversation_history.append({
                "question": question.strip().replace('\n', ' ').replace('\r', ' '),
                "answer": trimmed_for_history
            })
            # Keep only last 3 exchanges to avoid token limits
            if len(conversation_history) > 3:
                conversation_history = conversation_history[-3:]
            updated_attributes["conversation_history"] = conversation_history
            
            debug_logger.log_ai(request_id, "Bedrock query completed successfully", request)
            return ai_response, updated_attributes
            
        except Exception as e:
            debug_logger.log_ai(request_id, f"Bedrock error: {e}", request)
            fallback_message = "I'm having trouble processing your request right now. Please try again."
            
            # Clear session attributes on error
            updated_attributes = session_attributes.copy() if session_attributes else {}
            updated_attributes.pop("last_answer", None)
            updated_attributes.pop("last_question", None)
            
            return fallback_message, updated_attributes
