from google import genai
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
key = os.getenv('GOOGLE_API_KEY')
if not key:
    from src.core.config_manager import load_api_key
    key = load_api_key()

if not key:
    print("ERROR: No Google API Key found in .env or local config.json")
    sys.exit(1)

client = genai.Client(api_key=key)

# Exact strings from model_list_utf8.txt
test_models = [
    'gemini-3.5-flash',
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite'
]

print(f"Testing Gemini Connectivity with key: {key[:10]}...")

for m_name in test_models:
    print(f"\n--- Trying model: {m_name} ---")
    try:
        response = client.models.generate_content(
            model=m_name,
            contents="Hello. Reply with 'Success'."
        )
        print(f"RESULT: {response.text.strip()}")
        print(f"SUCCESS: {m_name} is working.")
        break
    except Exception as e:
        print(f"ERROR for {m_name}: {e}")

print("\nConnectivity scan complete.")
