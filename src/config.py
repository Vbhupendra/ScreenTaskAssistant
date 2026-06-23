import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# System Configuration
APP_NAME = "BlackBox Pro"
VERSION = "1.0.0 (Pro Background Assistant)"

# Audio Configuration
WAKE_WORD = "blackbox"
VOSK_MODEL_PATH = "model/vosk-model-small-en-us-0.15"

# Vision Configuration
DEFAULT_VISION_SOURCE = "DISPLAY"
VISION_DEVICE_INDEX = 0

# Brain Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = "gemini-3.5-flash"

