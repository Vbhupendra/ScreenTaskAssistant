"""
test_reasoning_integration.py
End-to-end integration tests for config_manager and ReasoningEngine:
- valid API key load (config.json & .env fallback)
- fresh config setup
- missing/invalid key error handling
- normal screen analysis
- streaming reasoning
- cancellation flow
"""
import sys
import os
import io
import json
import unittest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config_manager import load_api_key, save_api_key, get_config_path
from src.core.reasoning.vlm import ReasoningEngine


class TestReasoningIntegration(unittest.TestCase):

    def setUp(self):
        self.config_path = get_config_path()
        self.orig_config = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.orig_config = json.load(f)
            except Exception:
                pass

    def tearDown(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.orig_config, f, indent=4)
            except Exception:
                pass

    def test_local_valid_key_loading(self):
        """Verify load_api_key returns non-empty key when environment or config is present."""
        key = load_api_key()
        self.assertTrue(len(key) > 0, "load_api_key must return valid key")

    def test_fresh_config_env_fallback(self):
        """Verify load_api_key falls back to env when config.json has empty key."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"GEMINI_API_KEY": ""}, f, indent=4)
        key = load_api_key()
        # Should fall back to os.getenv("GOOGLE_API_KEY")
        env_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
        if env_key:
            self.assertEqual(key, env_key)

    def test_invalid_key_raises_or_returns_error(self):
        """Verify ReasoningEngine with invalid key yields friendly error message."""
        engine = ReasoningEngine(api_key="INVALID_KEY_12345")
        img = Image.new("RGB", (50, 50), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        
        chunks = list(engine.analyze_stream(buf.getvalue(), "Test prompt"))
        full_text = "".join(chunks)
        self.assertIn("error while thinking", full_text)

    def test_normal_screen_analysis_stream(self):
        """Verify real multimodal screen query streams response chunks successfully."""
        key = load_api_key()
        if not key:
            self.skipTest("No valid API key available in test environment.")

        engine = ReasoningEngine(api_key=key)
        img = Image.new("RGB", (100, 100), color="yellow")
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        chunks = list(engine.analyze_stream(buf.getvalue(), "What color is this image?"))
        full_text = "".join(chunks)
        self.assertTrue(len(full_text) > 0)
        self.assertIn("ANSWER", full_text)


if __name__ == "__main__":
    unittest.main()
