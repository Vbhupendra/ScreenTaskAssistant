import sys
import os
import time
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.reasoning.vlm import ReasoningEngine

def test_cooldown_mechanism():
    print("=== Testing Fast Fallback & Cooldown Mechanism ===")
    
    # 1. Initialize ReasoningEngine with a dummy key
    # We patch config_manager's load_api_key to return dummy key
    with patch('src.core.config_manager.load_api_key', return_value="DUMMY_KEY"), \
         patch('google.genai.Client') as mock_client_class:
         
        # Mock client behavior
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        engine = ReasoningEngine()
        
        # We will mock client.models.generate_content
        # Let's count how many times it gets called for each model
        call_counts = {}
        
        def mock_generate_content(model, contents, config):
            call_counts[model] = call_counts.get(model, 0) + 1
            if model == "gemini-3.5-flash":
                # Raise transient error (e.g. 503 unavailable)
                raise Exception("503 Service Unavailable")
            elif model == "gemini-2.5-flash":
                mock_response = MagicMock()
                mock_response.text = "Success from gemini-2.5-flash"
                return mock_response
            else:
                raise Exception("Unexpected model called")
                
        mock_client.models.generate_content.side_effect = mock_generate_content
        
        # First request: should try gemini-3.5-flash, fail, then fallback to gemini-2.5-flash
        t0 = time.time()
        res1 = engine.analyze(image_bytes=None, prompt="Test prompt")
        t1 = time.time()
        print(f"First request result: {res1} (Time taken: {t1-t0:.4f}s)")
        print(f"Call counts after first request: {call_counts}")
        
        assert res1 == "Success from gemini-2.5-flash", "Expected fallback success"
        assert call_counts.get("gemini-3.5-flash") == 1, "Expected gemini-3.5-flash to be called"
        assert call_counts.get("gemini-2.5-flash") == 1, "Expected fallback gemini-2.5-flash to be called"
        
        # Verify that gemini-3.5-flash was put on cooldown
        assert "gemini-3.5-flash" in engine._failed_models_cooldown, "gemini-3.5-flash should be on cooldown"
        print("PASS: First request successfully fell back and blacklisted gemini-3.5-flash")
        
        # Second request: should skip gemini-3.5-flash and call gemini-2.5-flash directly!
        call_counts.clear()
        t0 = time.time()
        res2 = engine.analyze(image_bytes=None, prompt="Second prompt")
        t1 = time.time()
        print(f"Second request result: {res2} (Time taken: {t1-t0:.4f}s)")
        print(f"Call counts after second request: {call_counts}")
        
        assert res2 == "Success from gemini-2.5-flash", "Expected fallback success"
        assert "gemini-3.5-flash" not in call_counts, "gemini-3.5-flash should have been skipped!"
        assert call_counts.get("gemini-2.5-flash") == 1, "Expected gemini-2.5-flash to be called directly"
        print("PASS: Second request skipped gemini-3.5-flash due to cooldown")
        
    print("=== All Fallback/Cooldown Tests Passed ===")

if __name__ == "__main__":
    test_cooldown_mechanism()
