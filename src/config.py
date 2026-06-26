import os
import json
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


# ---------------------------------------------------------------------------
# Configuration file path helpers
# ---------------------------------------------------------------------------
# NOTE: We use %APPDATA%\ScreenTaskAssistant instead of C:\ScreenTaskAssistant.
# Writing to the root of C:\ requires UAC elevation and will crash with a
# PermissionError on any standard Windows account. %APPDATA% is always
# writable by the current user with zero elevation — same zero-dependency,
# absolute-path approach, without the permissions problem.
# ---------------------------------------------------------------------------

def get_config_path() -> str:
    """Return the absolute path to config.json, creating the directory if needed."""
    # Resolve the writable absolute directory — no relative paths involved
    base_dir = os.getenv("APPDATA") or os.path.expanduser("~/AppData/Roaming")
    config_dir = os.path.join(base_dir, "ScreenTaskAssistant")

    # Force-create the full folder tree (safe no-op if already present)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)

    return os.path.join(config_dir, "config.json")


def load_user_api_key() -> str:
    """Load the Gemini API key, creating config.json first if it is missing."""
    config_file = get_config_path()

    # CRITICAL: Create the file FIRST before attempting to read it
    if not os.path.exists(config_file):
        with open(config_file, "w") as f:
            json.dump({"GEMINI_API_KEY": ""}, f, indent=4)
        return ""

    try:
        with open(config_file, "r") as f:
            data = json.load(f)
            return data.get("GEMINI_API_KEY", "")
    except Exception:
        return ""

