import os
import json

def get_config_dir() -> str:
    """Returns the platform-specific directory for configuration data.

    Uses APPDATA on Windows (os.name == 'nt') and ~/.config on Mac/Linux,
    with a safe fallback if the environment variable is not set.
    """
    if os.name == 'nt':
        base_dir = os.getenv('APPDATA') or os.path.expanduser('~/AppData/Roaming')
    else:
        base_dir = os.path.expanduser('~/.config')
    return os.path.join(base_dir, 'ScreenTaskAssistant')

def get_config_path() -> str:
    """Returns the full path to config.json in the OS-compliant local directory.

    Also guarantees the parent directory exists on every call, so fresh
    installations (or any code path that bypasses _ensure_config_file) can
    never crash with a FileNotFoundError.
    """
    config_dir = get_config_dir()
    os.makedirs(config_dir, exist_ok=True)  # safe no-op if already present
    return os.path.join(config_dir, "config.json")

def _ensure_config_file() -> str:
    """
    Ensures the config directory and config.json exist.
    If config.json is missing, creates it with a blank default template.
    Returns the full path to config.json.
    """
    config_dir = get_config_dir()
    config_path = get_config_path()

    # Create the directory tree if it doesn't already exist
    os.makedirs(config_dir, exist_ok=True)

    # Bootstrap a fresh config file if one is not yet present
    if not os.path.exists(config_path):
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"GEMINI_API_KEY": ""}, f, indent=4)
            print(f">> Config: Created fresh config file at {config_path}")
        except Exception as e:
            print(f"Error creating default config file: {e}")

    return config_path

def load_api_key() -> str:
    """
    Loads the API key from the local OS-compliant config file.
    Auto-creates the file with a blank template if it doesn't exist.
    """
    config_path = _ensure_config_file()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Support both key names for forwards/backwards compatibility
            key = data.get("api_key") or data.get("GEMINI_API_KEY") or ""
            return key.strip()
    except Exception as e:
        print(f"Error reading local config file: {e}")
    return ""

def save_api_key(api_key: str) -> bool:
    """
    Saves the API key to the local OS-compliant config file.
    Auto-creates the file and directory structure if they don't exist.
    """
    try:
        config_path = _ensure_config_file()

        # Load any existing data to preserve other keys
        data = {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

        data["api_key"] = api_key.strip()
        # Keep GEMINI_API_KEY in sync for any external tooling that reads it
        data["GEMINI_API_KEY"] = api_key.strip()

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving API key to local config: {e}")
        return False
