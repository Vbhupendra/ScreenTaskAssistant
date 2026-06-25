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
    Guarantees the config directory and config.json both exist before any
    caller tries to read from them. Follows the strict 4-step sequence:

      Step 1 — Resolve config_dir from APPDATA (Windows) or ~/.config (other).
      Step 2 — os.makedirs to build the full folder tree.
      Step 3 — If config.json is absent, write a blank default immediately.
      Step 4 — Return the guaranteed-valid path to the caller.

    Raises RuntimeError if the file still cannot be created (e.g. permissions),
    so the caller is never handed a path that doesn't exist on disk.
    """
    # Step 1: Resolve the directory path
    config_dir = get_config_dir()
    config_file_path = os.path.join(config_dir, "config.json")

    # Step 2: Build the full folder structure — safe no-op if already present
    os.makedirs(config_dir, exist_ok=True)

    # Step 3: Create config.json with a blank default if it does not yet exist
    if not os.path.exists(config_file_path):
        try:
            with open(config_file_path, "w") as f:
                json.dump({"GEMINI_API_KEY": ""}, f, indent=4)
            print(f">> Config: Created fresh config file at {config_file_path}")
        except Exception as e:
            raise RuntimeError(
                f"Config: Could not create {config_file_path} — {e}"
            ) from e

    # Step 4: File is guaranteed to exist — return the path
    return config_file_path

def load_api_key() -> str:
    """
    Loads the API key from the local OS-compliant config file.

    Calls _ensure_config_file() first, which runs the full 4-step init
    sequence (resolve → makedirs → create-if-missing → return path).
    Only after that sequence completes successfully does this function
    open and read the JSON, so a FileNotFoundError on fresh installs is
    impossible.
    """
    # _ensure_config_file() guarantees the file exists before we read it
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
