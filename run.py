import os
import sys

# 1. Dependency checks for running from source (GitHub Desktop, VS Code, etc.)
MISSING_DEPS = []
try:
    import pyaudio
except ImportError:
    MISSING_DEPS.append("pyaudio")
try:
    import mss
except ImportError:
    MISSING_DEPS.append("mss")
try:
    import cv2
except ImportError:
    MISSING_DEPS.append("opencv-python")
try:
    import google.genai
except ImportError:
    MISSING_DEPS.append("google-genai")
try:
    import speech_recognition
except ImportError:
    MISSING_DEPS.append("SpeechRecognition")
try:
    import PIL
except ImportError:
    MISSING_DEPS.append("pillow")
try:
    import pystray
except ImportError:
    MISSING_DEPS.append("pystray")
try:
    import plyer
except ImportError:
    MISSING_DEPS.append("plyer")
try:
    import dotenv
except ImportError:
    MISSING_DEPS.append("python-dotenv")

if MISSING_DEPS:
    print("=" * 60)
    print("⚠️  MISSING DEPENDENCIES DETECTED")
    print("=" * 60)
    print("The system is missing the following required packages:")
    for dep in MISSING_DEPS:
        print(f"  - {dep}")
    print("\nPlease install them by running this command in your terminal:")
    print("  pip install -r requirements.txt")
    print("=" * 60)
    sys.exit(1)

# Ensure the package environment is aligned for both source run and compiled EXE
if hasattr(sys, '_MEIPASS'):
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)
else:
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

from src.main import BlackBoxAgent

if __name__ == "__main__":
    agent = BlackBoxAgent()
    agent.start()

