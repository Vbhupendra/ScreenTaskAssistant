import threading
import time
from typing import Callable
from src.config import WAKE_WORD

class AudioWorker(threading.Thread):
    def __init__(self, ear_provider, callback: Callable[[str], None]):
        super().__init__(daemon=True)
        self.ear = ear_provider
        self.callback = callback
        self.stop_event = threading.Event()
        self._is_listening = True

    def stop(self):
        self.stop_event.set()
        self._is_listening = False

    def run(self):
        print(f">> AudioWorker: Monitoring for '{WAKE_WORD}'...")
        while not self.stop_event.is_set():
            if not self._is_listening:
                time.sleep(0.5)
                continue
                
            text = self.ear.get_command()
            if text:
                text_lower = text.lower()
                
                # Robust Wake Word Detection (handles 'blackbox' and 'black box')
                trigger_variants = [WAKE_WORD.lower(), WAKE_WORD.lower().replace("box", " box")]
                is_triggered = any(variant in text_lower for variant in trigger_variants)
                
                # Direct commands that bypass the wake word requirement
                # This ensures the system still responds even if the wake word is missed or misheard
                direct_commands = [
                    "what is on my", "what's on my",
                    "look at this", "look this",
                    "read the first", "read first", "read the fast"
                ]
                if not is_triggered:
                    is_triggered = any(cmd in text_lower for cmd in direct_commands)

                if is_triggered:
                    print(f">> AudioWorker: Wake Word or Direct Command Recognized!")
                    self.callback(text)
                else:
                    # Optional: log other heard text for debugging
                    print(f"Heard (ignored): '{text}'")
            
            time.sleep(0.05) # Slightly faster polling for Pro version

    def pause_listening(self):
        self._is_listening = False

    def resume_listening(self):
        # Clear any backlog of audio accumulated while paused (like its own voice)
        if hasattr(self.ear, 'clear_queue'):
            self.ear.clear_queue()
        self._is_listening = True
