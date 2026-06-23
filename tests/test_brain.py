import sys
import os
from google import genai

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.reasoning.vlm import ReasoningEngine
from src.config import GOOGLE_API_KEY
from src.core.config_manager import load_api_key

def test_brain():
    print("=== Testing Gemini Brain Connection ===")
    
    key = GOOGLE_API_KEY
    if not key:
        key = load_api_key()
        
    if not key:
        print("FAIL: No API Key found in .env or local config.json")
        return

    client = genai.Client(api_key=key)
    
    print("Listing Available Models:")
    found_flash = False
    for m in client.models.list():
        if 'generateContent' in m.supported_actions:
            print(f" - {m.name}")
            if "flash" in m.name:
                found_flash = True
    
    print(f"\nFlash capability found: {found_flash}")

    try:
        # Try initializing with what we have
        brain = ReasoningEngine(api_key=key)
        print("Model initialized.")
        
        print("Sending test prompt...")
        response = brain.analyze(image_bytes=None, prompt="Ping. One word response.")
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"FAIL: Brain Connection Error - {e}")
        
    print("=== Test Complete ===")

if __name__ == "__main__":
    test_brain()
