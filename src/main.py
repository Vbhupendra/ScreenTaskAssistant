import os
import sys

# Add the project root to sys.path so compiled binaries recognize the 'src'
# package layout regardless of the working directory at launch time.
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Also insert the src/ directory itself so bare module names resolve inside
# PyInstaller's extracted temp tree (belt-and-suspenders for packed .exe).
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import time
import threading
from typing import Optional

from src.config import (
    VOSK_MODEL_PATH, 
    DEFAULT_VISION_SOURCE, 
    VISION_DEVICE_INDEX, 
    GOOGLE_API_KEY, 
    WAKE_WORD,
    APP_NAME,
    MODEL_NAME
)
from src.core.hal.audio import AudioProvider
from src.core.hal.vision import get_vision_provider
from src.core.reasoning.vlm import ReasoningEngine
from src.core.actions.voice_output import VoiceOutput
from src.core.hal.tray import TrayManager
from src.core.hal.overlay import OverlayWindow

from src.core.hal.audio_worker import AudioWorker

class BlackBoxAgent:
    def __init__(self):
        self.running = True
        self.context_frame = None  # Pre-initialize to prevent AttributeError before first wake-word
        
        # 1. Initialize Non-blocking Components
        print(f">> Initializing {APP_NAME}...")
        self.speaker = VoiceOutput()
        self.overlay = OverlayWindow()
        self.vision = get_vision_provider(DEFAULT_VISION_SOURCE, VISION_DEVICE_INDEX)
        
        # Resolve API key storage lifecycle
        from src.core.config_manager import load_api_key, save_api_key
        
        key = load_api_key()
        if not key and GOOGLE_API_KEY:
            print(">> API Key found in env/.env. Syncing to config.json...")
            save_api_key(GOOGLE_API_KEY)
            key = GOOGLE_API_KEY
            
        if key:
            self._init_brain_and_audio(key)
        else:
            self.brain = None
            self.ear = None
            self.audio_worker = None
            
        # Initialize Tray with callbacks
        self.tray = TrayManager(
            on_exit_callback=self.stop,
            on_restart_callback=self.restart
        )

    def _init_brain_and_audio(self, key):
        """Initializes components requiring a valid API key."""
        print(">> Initializing AI and Audio engines...")
        self.brain = ReasoningEngine(api_key=key)
        self.ear = AudioProvider(model_path=VOSK_MODEL_PATH)
        self.audio_worker = AudioWorker(
            ear_provider=self.ear, 
            callback=self._on_wake_word
        )

    def start(self):
        # Start system tray in background thread
        self.tray.run()
        
        from src.core.config_manager import load_api_key, save_api_key
        key = load_api_key()
        
        if key:
            self.ear.start_listening()
            self.audio_worker.start()
            self.speaker.speak(f"{APP_NAME} Pro is active.")
            self.tray.notify(APP_NAME, "Assistant is online and listening.")
        else:
            print(">> Intercepting startup: No API key found. Requesting key via overlay UI...")
            
            def _on_key_saved(entered_key):
                if save_api_key(entered_key):
                    self._init_brain_and_audio(entered_key)
                    self.ear.start_listening()
                    self.audio_worker.start()
                    self.speaker.speak(f"{APP_NAME} Pro is active.")
                    self.tray.notify(APP_NAME, "Assistant is online and listening.")
                    return True
                return False
                
            self.overlay.show_key_input(_on_key_saved)
            
        # Start Tkinter event loop (Blocks main thread)
        self.overlay.run()

    def stop(self):
        print(f">> Stopping {APP_NAME}...")
        self.running = False
        if hasattr(self, 'audio_worker') and self.audio_worker:
            self.audio_worker.stop()
        if hasattr(self, 'ear') and self.ear:
            self.ear.stop()
        self.vision.cleanup()
        self.speaker.stop()
        print(">> Shutdown Complete.")
        
        # Stop Tkinter event loop to allow main thread to exit cleanly
        if hasattr(self, 'overlay') and self.overlay.root:
            try:
                self.overlay.root.quit()
            except Exception:
                pass
                
        # Only exit if not restarting
        if not getattr(self, '_restarting', False):
            sys.exit(0)

    def restart(self):
        print(f">> Restarting {APP_NAME}...")
        self._restarting = True
        self.stop()
        
        # Re-initialize and start
        # In a real scenario, we might want to use os.execv to truly restart the process
        # but for this architecture, we'll try a clean re-init
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def _on_wake_word(self, raw_text: str):
        """Callback triggered by AudioWorker when 'BlackBox' is heard."""
        # 1. Immediate Visual Feedback (Red status on Tray and Overlay)
        self.tray.update_state('listening')
        self.overlay.clear()
        self.overlay.show()
        self.overlay.update_status('listening')
        self.overlay.append("🎙️ **Listening for command...**\n")
        
        # 2. Context Injection: Snap the screen IMMEDIATELY
        # This captures what the user is looking at BEFORE they finish the sentence
        print(">> Context Trigger: Snapping screen...")
        self.context_frame = self.vision.capture(force=True)
        
        # 3. Process the full command
        self._process_command(raw_text)

    def _process_command(self, raw_text: str):
        """Handle the vision + reasoning pipeline."""
        try:
            # Clean up command (remove common wake-word variants)
            clean_command = raw_text.lower().replace("black box", "").replace("blackbox", "").strip()
            if not clean_command:
                print(">> Waiting for follow-up command...")
                wait_time = 3.0
                start_time = time.time()
                
                while time.time() - start_time < wait_time:
                    text = self.ear.get_command()
                    if text:
                        clean_command = text.strip()
                        break
                    time.sleep(0.05)
                
                if not clean_command:
                    clean_command = "Analyze current screen."
            
            # Autocorrect common STT mistakes for core commands
            clean_command = self._normalize_command(clean_command)
            
            print(f">> Triggered! Command: {clean_command}")
            
            # Show the command being processed and change status to THINKING
            self.overlay.clear()
            self.overlay.append(f"🔍 **Command:** {clean_command}\n\n")
            self.overlay.append("⚡ **Thinking...**\n")
            
            # Pause listening to avoid feedback or duplicate triggers
            self.audio_worker.pause_listening()
            
            # Update Tray & Overlay: Thinking (Blue Pulse)
            self.tray.update_state('thinking')
            self.overlay.update_status('thinking')
            
            # Use pre-captured context frame or capture a fresh one if needed
            urgent = self._is_urgent(clean_command)
            frame = self.context_frame if (self.context_frame and not urgent) else self.vision.capture(force=urgent)
            
            if not frame:
                print(">> Warning: No image frame captured. Proceeding with text-only.")
            
            # 4. Stream Reasoning + Output
            print(f">> Thinking ({MODEL_NAME})...")
            stream = self.brain.analyze_stream(image_bytes=frame, prompt=clean_command)
            
            # Prepare overlay before streaming: clear the "Thinking..." text and keep Query
            self.overlay.clear()
            self.overlay.append(f"🔍 **Command:** {clean_command}\n")
            self.overlay.append("─" * 40 + "\n\n")
            
            # Switch to speaking state
            self.tray.update_state('speaking')
            self.overlay.update_status('speaking')
            self.speaker.speak_stream(stream, overlay=self.overlay)
            
            # 5. Wait for speaker to finish before resetting
            while self.speaker.is_speaking():
                time.sleep(0.5)
            
            # 6. Reset
            time.sleep(0.5) # Final grace period
            self.context_frame = None # Clear context
            self.tray.update_state('idle')
            self.overlay.update_status('idle')
            self.audio_worker.resume_listening()
            
        except Exception as e:
            print(f"Error processing command: {e}")
            try:
                # Provide friendly audio feedback for errors
                self.speaker.speak("I encountered a system error. Please check the logs.")
            except:
                pass
            
            self.context_frame = None
            self.tray.update_state('idle')
            self.audio_worker.resume_listening()

    def _normalize_command(self, text: str) -> str:
        """Autocorrects commonly misheard phrases to match our core commands."""
        # Clean and lower the text
        normalized = text.lower()
        
        # Target 1: "what is on my screen"
        # STT might hear: "what is on my scream", "what is on my stream", "what's on my screen"
        if "what is on my" in normalized or "what's on my" in normalized:
            return "what is on my screen"
            
        # Target 2: "look at this code and explain it"
        # STT might hear: "look at this cold and explain it", "look at his code"
        if ("look at" in normalized or "look this" in normalized) and ("code" in normalized or "cold" in normalized or "explain" in normalized):
            return "look at this code and explain it"
            
        # Target 3: "read the first paragraph"
        # STT might hear: "read the fast paragraph", "read first photograph"
        if "read" in normalized and ("first" in normalized or "fast" in normalized or "paragraph" in normalized or "photograph" in normalized):
            return "read the first paragraph"
            
        return text

    def _is_urgent(self, text: str) -> bool:
        """Determines if the command requires a fresh/forced capture."""
        keywords = ["look", "read", "error", "see", "describe", "what is", "analyze", "help"]
        return any(keyword in text.lower() for keyword in keywords)

if __name__ == "__main__":
    agent = BlackBoxAgent()
    agent.start()
