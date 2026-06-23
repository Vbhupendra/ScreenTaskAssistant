import sys
import os
import time

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.actions.voice_output import VoiceOutput
from src.core.hal.vision import get_vision_provider
# We skip Audio immediately if model not present to avoid crash, but try to import
from src.core.hal.audio import AudioProvider

def test_tts():
    print("Testing TTS...")
    try:
        speaker = VoiceOutput()
        speaker.speak("Verification test: Audio system check.")
        time.sleep(2)
        speaker.stop()
        print("PASS: TTS")
    except Exception as e:
        print(f"FAIL: TTS - {e}")

def test_vision():
    print("Testing Vision (Software)...")
    try:
        vision = get_vision_provider('DISPLAY')
        
        # 1. Normal Capture
        frame1 = vision.capture()
        if frame1:
            print(f"PASS: Normal Capture {len(frame1)} bytes.")
        else:
            print("WARN: Normal Capture None (Static?).")

        # 2. Forced Capture (Should ALWAYS work)
        frame2 = vision.capture(force=True)
        if frame2:
            print(f"PASS: Forced Capture {len(frame2)} bytes.")
        else:
            print("FAIL: Forced Capture returned None!")

        vision.cleanup()
    except Exception as e:
        print(f"FAIL: Vision - {e}")

def verify_setup():
    print("=== Black Box Verification ===")
    
    # 1. Test Dependencies
    try:
        import mss
        import numpy
        import cv2
        import vosk
        import pyaudio
        print("PASS: Import Dependencies")
    except ImportError as e:
        print(f"FAIL: Missing Dependency - {e}")
    
    # 2. Test TTS
    test_tts()
    
    # 3. Test Vision
    test_vision()
    
    # 4. Check Vosk Model
    from src.config import VOSK_MODEL_PATH
    if os.path.exists(VOSK_MODEL_PATH) and os.path.isdir(VOSK_MODEL_PATH):
        print(f"PASS: Vosk Model found at {VOSK_MODEL_PATH}.")
    else:
        print(f"FAIL: Vosk Model NOT found at {VOSK_MODEL_PATH}. Check src/config.py")

    print("=== Verification Complete ===")

if __name__ == "__main__":
    verify_setup()
