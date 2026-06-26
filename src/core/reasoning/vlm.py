import os
import time
from google import genai
from google.genai import types
from typing import Optional
from PIL import Image
import io

from src.config import MODEL_NAME

SYSTEM_INSTRUCTION = (
    "You are BlackBox Pro, an always-on AI reasoning and development assistant. "
    "You have real-time access to the user's screen context and audio commands.\n\n"
    "Your primary goal is to help the user solve tasks, write code, and troubleshoot system/application issues.\n"
    "Whenever the user asks a question or triggers an analysis:\n"
    "1. Thoroughly inspect the screenshot for any error messages, compiler bugs, crash dumps, exceptions, broken user interfaces, typos, or security concerns.\n"
    "2. If you notice ANY problem, clearly identify it, explain the root cause, and proactively generate a complete, step-by-step solution or code fix.\n"
    "3. Keep your answers direct, action-oriented, and complete. Ensure you provide the exact code changes, command line instructions, or step-by-step resolution needed to fix the issue."
)

# Ordered fallback chain: primary model first, then backups
# gemini-2.5-flash is proven fast (~1-2s). gemini-2.0-flash as tertiary backup.
MODEL_FALLBACK_CHAIN = [
    MODEL_NAME,           # Primary: gemini-2.5-flash (from config) — 1-2s latency
    "gemini-2.0-flash",   # Secondary fallback                       — 2-3s latency
    "gemini-2.0-flash-lite", # Tertiary fallback                    — stable light fallback
]

# Errors that should trigger a fallback to the next model
FALLBACK_TRIGGERS = ["503", "UNAVAILABLE", "overloaded", "ResourceExhausted", "429", "quota"]

class ReasoningEngine:
    """Gemini-powered Multimodal Reasoning Engine with automatic model fallback."""
    def __init__(self, api_key: str = None):
        self._initial_api_key = api_key
        self.client = None
        self._failed_models_cooldown = {} # model_name -> cooldown_expiration_timestamp
        try:
            self._get_client()
        except Exception as e:
            print(f"Warning during ReasoningEngine init: {e}")

    def _get_client(self):
        """Dynamically loads the API key from the config storage and ensures client is initialized."""
        from src.core.config_manager import load_api_key
        key = load_api_key()
        if not key:
            key = getattr(self, '_initial_api_key', None)
            
        if not key:
            raise ValueError("Google GenAI API key is missing. Please configure it via overlay.")
            
        if not hasattr(self, '_current_key') or self._current_key != key or not self.client:
            self._current_key = key
            print(">> Reasoning Engine: (Re)initializing client (fail-fast: 1 attempt, 10s hard timeout)...")
            self.client = genai.Client(
                api_key=key,
                http_options=types.HttpOptions(
                    timeout=10000,  # 10-second hard cap per model attempt (minimum allowed deadline is 10s)
                    retry_options=types.HttpRetryOptions(attempts=1)
                )
            )
            
        return self.client

    def _should_fallback(self, error_str: str) -> bool:
        """Returns True if this error warrants trying a fallback model."""
        return any(trigger in error_str for trigger in FALLBACK_TRIGGERS)

    def _get_active_models(self) -> list:
        """Finds active models that are not currently cooling down."""
        now = time.time()
        active = [m for m in MODEL_FALLBACK_CHAIN if now >= self._failed_models_cooldown.get(m, 0)]
        if not active:
            print(">> All fallback models are on cooldown! Resetting cooldowns.")
            self._failed_models_cooldown.clear()
            active = MODEL_FALLBACK_CHAIN
        return active

    def analyze(self, image_bytes: Optional[bytes], prompt: str) -> str:
        """Standard analysis, returns full text. Tries each model in fallback chain."""
        contents = self._prepare_inputs(image_bytes, prompt)
        client = self._get_client()
        config = types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)

        active_models = self._get_active_models()
        for model in active_models:
            try:
                print(f">> Using model: {model}")
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config
                )
                return response.text
            except Exception as e:
                error_str = str(e)
                if self._should_fallback(error_str):
                    print(f">> Model '{model}' unavailable (503/quota). Putting on cooldown and trying next fallback...")
                    self._failed_models_cooldown[model] = time.time() + 300
                    continue
                else:
                    print(f"Reasoning Error: {e}")
                    return "I encountered an error while thinking. Please try again."

        # All models exhausted
        print(">> All fallback models failed.")
        return "All AI models are temporarily unavailable. Please try again in a moment."

    def analyze_stream(self, image_bytes: Optional[bytes], prompt: str):
        """Streaming analysis, yields text chunks. Tries each model in fallback chain."""
        contents = self._prepare_inputs(image_bytes, prompt)
        client = self._get_client()
        config = types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)

        active_models = self._get_active_models()
        for model in active_models:
            try:
                print(f">> Using model: {model}")
                response = client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=config
                )
                # Consume the stream — this is where a 503 will actually be raised
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return  # Stream completed successfully — stop fallback chain

            except Exception as e:
                error_str = str(e)
                if self._should_fallback(error_str):
                    print(f">> Model '{model}' unavailable (503/quota). Putting on cooldown and trying next fallback...")
                    self._failed_models_cooldown[model] = time.time() + 300
                    continue
                else:
                    print(f"Streaming Reasoning Error: {e}")
                    yield "I encountered an error while thinking. Please try again."
                    return

        # All models exhausted
        print(">> All fallback models failed.")
        yield "All AI models are temporarily unavailable. Please try again in a moment."

    def _prepare_inputs(self, image_bytes: Optional[bytes], prompt: str) -> list:
        enhanced_prompt = (
            f"User Command/Question: {prompt}\n\n"
            "INSTRUCTION FOR YOU:\n"
            "Thoroughly analyze the screenshot. If there is ANY error, bug, exception, "
            "compiler issue, or problem visible, you MUST:\n"
            "1. Explicitly identify and describe the problem.\n"
            "2. Explain the root cause of the issue.\n"
            "3. Proactively generate a complete, direct solution or code fix to resolve it.\n"
            "Format your output in clean, structured Markdown using headers (##), bullet lists (-), bold text (**text**), and code blocks (```python ... ```) so that the formatting renders properly in the user's chat panel."
        )
        inputs = [enhanced_prompt]
        if image_bytes:
            image = Image.open(io.BytesIO(image_bytes))
            inputs.append(image)
        return inputs
