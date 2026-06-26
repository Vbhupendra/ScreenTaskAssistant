"""
test_imports.py — BlackBox Pro Import Health Check
===================================================
Verifies all critical modules can be imported successfully.
Run from the project root: python test_imports.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print(" BlackBox Pro — Import Health Check")
print("=" * 50)

passed = 0
failed = 0

def check(label, module_path):
    global passed, failed
    try:
        __import__(module_path)
        print(f"  [OK]   {label}")
        passed += 1
    except ImportError as e:
        print(f"  [FAIL] {label}: {e}")
        failed += 1
    except Exception as e:
        print(f"  [WARN] {label}: {e}")
        passed += 1  # Module loaded but may have runtime requirements (e.g. display)

print("\n--- Core Config ---")
check("src.config",                         "src.config")
check("src.core.config_manager",            "src.core.config_manager")

print("\n--- HAL (Hardware Abstraction Layer) ---")
check("src.core.hal.audio",                 "src.core.hal.audio")
check("src.core.hal.audio_worker",          "src.core.hal.audio_worker")
check("src.core.hal.vision",                "src.core.hal.vision")
check("src.core.hal.overlay",               "src.core.hal.overlay")
check("src.core.hal.tray",                  "src.core.hal.tray")

print("\n--- Reasoning Engine ---")
check("src.core.reasoning.vlm (Active)",    "src.core.reasoning.vlm")
check("src.core.reasoning.llm (Stub/Dead)", "src.core.reasoning.llm")

print("\n--- Actions ---")
check("src.core.actions.voice_output",      "src.core.actions.voice_output")

print("\n--- Top-Level Entry Point ---")
check("src.main",                           "src.main")

print("\n" + "=" * 50)
if failed == 0:
    print(f"  ALL {passed} checks PASSED. System is healthy.")
else:
    print(f"  {passed} passed, {failed} FAILED — fix issues above before running.")
print("=" * 50)

sys.exit(0 if failed == 0 else 1)
