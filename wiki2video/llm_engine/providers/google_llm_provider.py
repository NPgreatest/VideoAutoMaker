# llm_engine/providers/google_llm_provider.py
from __future__ import annotations

import backoff
import requests
from google import genai
from google.genai.types import GenerationConfig

from .base_provider import BaseLLMProvider
from ...config.config_vars import BACKOFF_MAX_TRIES, BACKOFF_MAX_TIME
from ...config.config_manager import config


class GoogleLLMProvider(BaseLLMProvider):
    DEFAULT_API_URL = ""  # Google Gen AI SDK doesn't use api_url

    def __init__(self, api_url=None, **kwargs):
        super().__init__(
            api_url=api_url or self.DEFAULT_API_URL,
            **kwargs,
        )
        # Initialize Google Gen AI client with Vertex AI
        project_id = config.get("google", "project_id")
        if not project_id:
            raise ValueError("Missing google.project_id in config.json")
        
        # Use Vertex AI mode similar to google_image_provider.py
        self.client = genai.Client(
            vertexai=True,
            project=project_id,
        )

    def _convert_messages_to_google_format(self, messages):
        """
        Convert ChatMessage format to Google Gen AI format.
        Google Gen AI accepts a list of dicts with 'role' and 'parts' (content).
        
        Note: System messages are typically handled differently in Google Gen AI.
        For now, we'll convert system messages to user messages.
        """
        google_messages = []
        system_instruction = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Handle system messages - collect them for potential system instruction
            if role == "system":
                if system_instruction:
                    system_instruction += "\n" + content
                else:
                    system_instruction = content
                continue
            
            # Map role names: Google uses 'user', 'model' (instead of 'assistant')
            if role == "assistant":
                google_role = "model"
            else:
                google_role = "user"
            
            google_messages.append({
                "role": google_role,
                "parts": [{"text": content}]
            })
        
        # If we have system instruction, prepend it to the first user message
        if system_instruction and google_messages:
            first_msg = google_messages[0]
            if first_msg["role"] == "user":
                first_msg["parts"][0]["text"] = system_instruction + "\n\n" + first_msg["parts"][0]["text"]
        
        return google_messages

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, requests.exceptions.HTTPError),
        max_tries=BACKOFF_MAX_TRIES,
        max_time=BACKOFF_MAX_TIME,
        jitter=backoff.random_jitter
    )
    def chat(
        self,
        messages,
        model,
        temperature=0.2,
        max_tokens=1200,
        stream=False,
        extra=None,
    ):
        """
        Send chat request to Google Gemini model via Vertex AI.
        
        Args:
            messages: List of ChatMessage dicts with 'role' and 'content'
            model: Model name (e.g., "gemini-2.5-flash")
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response (not implemented yet)
            extra: Additional parameters
        
        Returns:
            ChatResult dict with 'content' and 'raw' keys
        """
        # Convert messages to Google format
        google_messages = self._convert_messages_to_google_format(messages)
        
        # Ensure we have at least one message
        if not google_messages:
            raise ValueError("No valid messages provided (only system messages are not sufficient)")
        
        # Build generation config
        generation_config_kwargs = {}
        if temperature is not None:
            generation_config_kwargs["temperature"] = temperature
        if max_tokens is not None:
            generation_config_kwargs["max_output_tokens"] = max_tokens
        
        # Merge extra config if provided
        if extra:
            generation_config_kwargs.update(extra)
        
        # Create GenerationConfig object if we have any config parameters
        generation_config = None
        if generation_config_kwargs:
            try:
                generation_config = GenerationConfig(**generation_config_kwargs)
            except (TypeError, AttributeError):
                # Fallback: if GenerationConfig doesn't exist or doesn't accept these params,
                # pass as dict (some SDK versions might accept dict)
                generation_config = generation_config_kwargs
        
        try:
            # Call Google Gen AI API
            # Note: config parameter is optional
            if generation_config:
                response = self.client.models.generate_content(
                    model=model,
                    contents=google_messages,
                    config=generation_config,
                )
            else:
                response = self.client.models.generate_content(
                    model=model,
                    contents=google_messages,
                )
            
            # Extract text content
            content = response.text if hasattr(response, "text") and response.text else ""
            
            # Return in ChatResult format
            return {
                "content": content,
                "raw": response,
            }
            
        except Exception as e:
            raise RuntimeError(f"Google Gemini generation failed: {e}") from e

