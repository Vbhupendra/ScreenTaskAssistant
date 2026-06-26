import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# ---------------------------------------------------------------------------
# Application Constants
# ---------------------------------------------------------------------------
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
MODEL_NAME = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# NOTE: All config file I/O (read/write API key, get config path) is handled
# exclusively by:  src/core/config_manager.py
#
# Do NOT add get_config_path() or load_user_api_key() here — those were
# duplicates of config_manager.py functions and have been removed to keep
# a single canonical source of truth.
# ---------------------------------------------------------------------------
