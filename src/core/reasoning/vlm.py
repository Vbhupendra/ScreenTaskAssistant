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
    "Your primary goal is to help the user solve tasks, write code, and troubleshoot system/application issues.\n\n"
    "Format final responses using the conceptual structure below. Keep responses short, direct, voice-friendly, and free of introductory filler (e.g. do not say 'I have analyzed your screen...').\n\n"
    "Format layout:\n"
    "ANSWER: <The direct answer or problem identification. First answer the user's actual request.>\n"
    "REASON: <Brief, single-sentence explanation of the root cause (include only when necessary to understand a problem/diagnosis).>\n"
    "ACTION: <Concrete, explicit code snippet, command, or step to resolve it (include only when a fix/solution is requested or needed).>\n\n"
    "Rules for sections:\n"
    "- Simple question: Provide only the ANSWER section.\n"
    "- Explanation (e.g. explain this code): Provide ANSWER and optional REASON. Omit the ACTION section.\n"
    "- Diagnosis (e.g. what's wrong): State the problem in ANSWER, why it happened in REASON, and how to fix it in ACTION.\n"
    "- Solution (e.g. fix this): Provide the recommended fix in ANSWER and the exact code/command block in ACTION.\n\n"
    "Ensure technical information is accurate and structured in clean Markdown. Never invent information that cannot be established from the screen context. If context is insufficient, explicitly state what is missing."
)

# Ordered fallback chain: primary model first, then active backups
MODEL_FALLBACK_CHAIN = [
    MODEL_NAME,              # Primary: gemini-3.6-flash (from config) — fast (~1-2s)
    "gemini-3.5-flash",       # Secondary fallback — robust backup
    "gemini-3.1-flash-lite",  # Tertiary fallback — light/fast backup
]

# Errors that should trigger a fallback to the next model
FALLBACK_TRIGGERS = ["503", "UNAVAILABLE", "overloaded", "ResourceExhausted", "429", "quota", "404", "NOT_FOUND", "NotFound"]

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
        """Dynamically loads the API key from constructor parameter or config storage / env."""
        key = getattr(self, '_initial_api_key', None)
        if not key:
            from src.core.config_manager import load_api_key
            key = load_api_key()
            
        if not key:
            raise ValueError("Google GenAI API key is missing. Please configure it via overlay.")
            
        if not hasattr(self, '_current_key') or self._current_key != key or not self.client:
            self._current_key = key
            print(">> Reasoning Engine: (Re)initializing client (fail-fast: 1 attempt)...")
            self.client = genai.Client(
                api_key=key,
                http_options=types.HttpOptions(
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
                exc_type = type(e).__name__
                if self._should_fallback(error_str):
                    print(f">> Reasoning Engine: Model '{model}' unavailable/deprecated ({exc_type}: {error_str[:120]}). Trying next fallback...")
                    self._failed_models_cooldown[model] = time.time() + 300
                    continue
                else:
                    print(f">> Reasoning Engine: Non-fallback error on model '{model}' ({exc_type}: {error_str[:120]}).")
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
                # Consume the stream — this is where a 503/404 will actually be raised
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return  # Stream completed successfully — stop fallback chain

            except Exception as e:
                error_str = str(e)
                exc_type = type(e).__name__
                if self._should_fallback(error_str):
                    print(f">> Reasoning Engine: Model '{model}' unavailable/deprecated ({exc_type}: {error_str[:120]}). Trying next fallback...")
                    self._failed_models_cooldown[model] = time.time() + 300
                    continue
                else:
                    print(f">> Reasoning Engine: Non-fallback error on model '{model}' ({exc_type}: {error_str[:120]}).")
                    yield "I encountered an error while thinking. Please try again."
                    return

        # All models exhausted
        print(">> All fallback models failed.")
        yield "All AI models are temporarily unavailable. Please try again in a moment."

    def _prepare_inputs(self, image_bytes: Optional[bytes], prompt: str) -> list:
        enhanced_prompt = (
            f"User Command/Question: {prompt}\n\n"
            "PRONOUN RESOLUTION INSTRUCTION:\n"
            "Any context-dependent references (such as 'this', 'that', 'here', 'it', 'my screen') "
            "made by the user refer explicitly to the provided screen screenshot/active UI context.\n\n"
            "RESPONSE RULES:\n"
            "1. Answer the user's request first. Use concrete, technical details. Do not repeat the user's question.\n"
            "2. Avoid generic/filler phrases such as 'I have analyzed your screen', 'Based on my analysis', 'It appears that', or 'I would like to inform you'.\n"
            "3. Format your response using these headers when relevant (omit unnecessary sections):\n"
            "ANSWER: [Short, direct answer, or problem identification]\n"
            "REASON: [Brief, single-sentence explanation of the root cause, only if needed]\n"
            "ACTION: [The exact command, code block, or step to resolve it, only if a solution is needed]\n\n"
            "Format Guide:\n"
            "- Simple Question: Return only 'ANSWER: [response]'.\n"
            "- Code Explanation: Return 'ANSWER: [explanation]' (optionally include REASON; omit ACTION).\n"
            "- Diagnosis: Return 'ANSWER: [problem description]', 'REASON: [root cause]', and 'ACTION: [remediation command/code]'.\n"
            "- Solution: Return 'ANSWER: [recommended fix description]' and 'ACTION: [exact command/code block to run]'.\n\n"
            "If the screen context is insufficient to answer, explicitly state what is missing instead of guessing."
        )
        inputs = [enhanced_prompt]
        if image_bytes:
            image = Image.open(io.BytesIO(image_bytes))
            inputs.append(image)
        return inputs
