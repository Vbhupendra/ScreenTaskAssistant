import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config_manager import get_config_path, load_api_key, save_api_key, _ensure_config_file

config_path = get_config_path()
backup = config_path + ".bak"

# Backup existing config
if os.path.exists(backup):
    os.remove(backup)
if os.path.exists(config_path):
    os.rename(config_path, backup)

print("--- Test 1: _ensure_config_file() creates file with GEMINI_API_KEY template ---")
# Call _ensure_config_file directly to confirm it creates the default template
created_path = _ensure_config_file()
print(f"  File created at: {created_path}")
print(f"  File exists: {os.path.exists(created_path)}")
with open(created_path) as f:
    data = json.load(f)
print(f"  Raw contents: {data}")
assert "GEMINI_API_KEY" in data, "FAIL: default template key GEMINI_API_KEY missing"
assert data["GEMINI_API_KEY"] == "", "FAIL: default value should be empty string"
print("  PASS: _ensure_config_file creates {\"GEMINI_API_KEY\": \"\"} template")

print()
print("--- Test 2: save_api_key() writes both api_key and GEMINI_API_KEY ---")
result = save_api_key("MY_TEST_KEY_12345")
print(f"  Save returned: {result}")
with open(config_path) as f:
    data = json.load(f)
print(f"  api_key: {data.get('api_key')}")
print(f"  GEMINI_API_KEY: {data.get('GEMINI_API_KEY')}")
assert data.get("api_key") == "MY_TEST_KEY_12345", "FAIL: api_key mismatch"
assert data.get("GEMINI_API_KEY") == "MY_TEST_KEY_12345", "FAIL: GEMINI_API_KEY mismatch"
print("  PASS")

print()
print("--- Test 3: load_api_key() reads back saved key ---")
loaded = load_api_key()
print(f"  Loaded key: {loaded}")
assert loaded == "MY_TEST_KEY_12345", f"FAIL: expected MY_TEST_KEY_12345, got {loaded}"
print("  PASS")

print()
print("--- Test 4: load_api_key() on blank template returns empty string ---")
# Write a blank template and verify load returns ""
with open(config_path, "w") as f:
    json.dump({"GEMINI_API_KEY": ""}, f, indent=4)
loaded_blank = load_api_key()
print(f"  Loaded from blank template: \"{loaded_blank}\"")
assert loaded_blank == "", f"FAIL: expected empty string, got \"{loaded_blank}\""
print("  PASS")

# Restore original backup
os.remove(config_path)
if os.path.exists(backup):
    os.rename(backup, config_path)
    print("\nOriginal config restored.")

print("\n=== All config_manager tests PASSED ===")
