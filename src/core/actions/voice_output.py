import pyttsx3
import threading
import queue
import time

class VoiceOutput:
    """Non-blocking, streaming Text-to-Speech engine for BlackBox Pro."""
    def __init__(self):
        self.q = queue.Queue()
        self.running = True
        self._speaking = False
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        
    def _process_queue(self):
        """Worker loop to process speech commands."""
        # Initialize engine inside thread for Windows/COM compatibility
        engine = pyttsx3.init()
        engine.setProperty('rate', 185)  # Pro Speed: Crisp and fast
        
        while self.running:
            try:
                # Small timeout for responsiveness
                text = self.q.get(timeout=0.1)
                if text is None: break
                
                self._speaking = True
                engine.say(text)
                engine.runAndWait()
                self._speaking = False
                self.q.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"TTS Error: {e}")
                self._speaking = False

    def speak(self, text: str):
        """Add a text block to the speech queue."""
        if not text or not text.strip(): return
        self.q.put(text)

    def speak_stream(self, generator, overlay=None):
        """Consume a text generator and speak as chunks arrive."""
        buffer = ""
        print("Assistant: ", end="", flush=True)
        if overlay:
            overlay.clear()
            overlay.show()
        
        delimiters = [". ", "? ", "! ", "\n"]
        
        for chunk in generator:
            if not self.running: break
            
            # Print for immediate visual feedback
            print(chunk, end="", flush=True)
            if overlay:
                overlay.append(chunk)
            buffer += chunk
            
            # Check for legitimate sentence endings (punctuation + space)
            # This prevents splitting on abbreviations like "Mr." or "v1.5"
            for d in delimiters:
                if d in buffer:
                    parts = buffer.split(d)
                    # Speak all complete sentences
                    for part in parts[:-1]:
                        text = part.strip()
                        if text:
                            self.speak(text + d.strip()) # Add back punctuation for intonation
                    
                    # Keep the last part (incomplete sentence)
                    buffer = parts[-1]
                    break
        
        # Catch any final text
        if buffer.strip():
            self.speak(buffer.strip())
        print() # Newline after stream ends

    def stop(self):
        """Stop the speaker thread."""
        self.running = False
        self.q.put(None)
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1)

    def is_speaking(self):
        """Check if assistant is currently talking or has pending text."""
        return self._speaking or not self.q.empty()
