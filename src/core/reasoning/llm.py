# =============================================================================
# llm.py  —  ARCHIVED / DEAD STUB  (Do NOT use in production)
# =============================================================================
#
# This file is an early-architecture placeholder from before the Gemini VLM
# integration was built. It contains MOCK responses only and is NOT connected
# to any real AI model.
#
# The LIVE reasoning engine used by the application is:
#   src/core/reasoning/vlm.py  →  ReasoningEngine (Gemini-powered, multimodal)
#
# This file is kept only for historical reference. No code in the active
# application imports from here. If you accidentally import this file, you will
# get silent mock responses instead of real AI — which would be very confusing.
#
# =============================================================================

import os


class _MockReasoningEngine:
    """
    INACTIVE MOCK ENGINE — For historical/reference purposes only.
    Use src.core.reasoning.vlm.ReasoningEngine for all real inference.
    """
    def __init__(self):
        self.history = []

    def think(self, context: dict) -> str:
        """
        Mock reasoning — returns hardcoded responses.
        NOT connected to any AI model.
        """
        user_text = context.get('text', '').lower()
        if "screen" in user_text or "look" in user_text:
            return "[MOCK] Analyzing your screen..."
        elif "hello" in user_text or "hi" in user_text:
            return "[MOCK] Hello! This is a mock response."
        return f"[MOCK] Heard: {user_text}"

    def _mock_response(self, text: str) -> str:
        return self.think({'text': text})


# NOTE: No global instance or module-level think() function is exported.
# The old code had `engine = ReasoningEngine()` and `def think(context):`
# at module level, which was dangerous because any accidental import would
# activate mock mode. That pattern has been removed intentionally.
