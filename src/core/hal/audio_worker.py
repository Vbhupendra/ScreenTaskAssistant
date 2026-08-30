import threading
import time
from typing import Callable
from src.config import WAKE_WORD
from src.core.reasoning.intent_classifier import IntentClassifier, Intent

class AudioWorker(threading.Thread):
    def __init__(self, ear_provider, callback: Callable[[str, str], None]):
        super().__init__(daemon=True)
        self.ear = ear_provider
        self.callback = callback
        self.stop_event = threading.Event()
        self._is_listening = True
        self.intent_classifier = IntentClassifier()

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
                intent = self.intent_classifier.classify(text)
                
                # Robust Wake Word Detection (handles 'blackbox' and 'black box')
                trigger_variants = [WAKE_WORD.lower(), WAKE_WORD.lower().replace("box", " box")]
                has_wake_word = any(variant in text.lower() for variant in trigger_variants)
                
                # System triggers on any recognized intent, wake word, or cancel command
                is_triggered = (intent != Intent.UNKNOWN) or has_wake_word

                if is_triggered:
                    print(f">> AudioWorker: Triggered! Intent: {intent}")
                    self.callback(text, intent)
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
