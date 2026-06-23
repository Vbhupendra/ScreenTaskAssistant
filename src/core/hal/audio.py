import queue
import threading
from typing import Optional
import speech_recognition as sr

class AudioProvider:
    """Handles audio input and STT using Google Web Speech API for maximum accuracy."""
    
    def __init__(self, model_path=None, device_index: Optional[int] = None):
        # model_path is kept for backwards compatibility with main.py but ignored
        self.device_index = device_index
        self.recognizer = sr.Recognizer()
        
        # Optimize for faster background listening
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.6  # Shorter pause to end phrase
        
        self.mic = sr.Microphone(device_index=self.device_index)
        self.q = queue.Queue()
        self.running = False
        self.stop_listening_func = None

    def start_listening(self):
        """Starts background listening thread."""
        if self.running: return
        
        print(">> Audio Provider: Calibrating for ambient noise... Please wait.")
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
            
        print(">> Audio Provider: Listening (Online High-Accuracy Mode)...")
        self.running = True
        
        # listen_in_background spawns a daemon thread and manages audio capture automatically
        self.stop_listening_func = self.recognizer.listen_in_background(
            self.mic, self._audio_callback, phrase_time_limit=15
        )

    def _audio_callback(self, recognizer, audio):
        """Called automatically on a background thread when a phrase is spoken."""
        if not self.running:
            return
            
        try:
            # Using Google's highly accurate Web Speech API
            text = recognizer.recognize_google(audio)
            if text:
                print(f"  [STT Heard]: '{text}'") # Debug print to show exactly what it heard
                self.q.put(text)
        except sr.UnknownValueError:
            # Speech was unintelligible
            pass
        except sr.RequestError as e:
            print(f"STT Network Error: {e}")

    def get_command(self, timeout: float = 0.05) -> Optional[str]:
        """Polls the queue for recognized text."""
        if not self.running:
            return None
            
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None

    def clear_queue(self):
        """Empties the text queue to discard old phrases."""
        with self.q.mutex:
            self.q.queue.clear()

    def stop(self):
        self.running = False
        if self.stop_listening_func:
            self.stop_listening_func(wait_for_stop=False)
