import os
import re
import threading
import subprocess
import time

class VoiceOutput:
    """
    Lightweight, reliable TTS engine for BlackBox Pro.

    Architecture:
    - On Windows: spawns a PowerShell subprocess per speech job.
      This completely sidesteps all COM / SAPI5 background-thread limitations
      that silently break pyttsx3 in daemon threads.
    - On other platforms: falls back to pyttsx3.
    - A single daemon worker thread drains the job queue.
      When idle it blocks on queue.get() — zero busy-wait, zero system load.
    - Interruption (stop_speaking) kills the running process immediately;
      no blocking runAndWait() to wait for.
    """

    def __init__(self):
        import queue as _queue
        self.q = _queue.Queue()
        self.running = True
        self._speaking = False
        self._current_proc = None          # current PowerShell process (or None)
        self._lock = threading.Lock()      # protects _current_proc
        self.worker_thread = threading.Thread(
            target=self._process_queue, daemon=True, name="TTS-Worker"
        )
        self.worker_thread.start()

    # ── Internal worker ──────────────────────────────────────────────────────

    def _process_queue(self):
        """Single daemon thread: pulls utterances from the queue and speaks them."""
        import queue as _queue
        if os.name == 'nt':
            self._speak_fn = self._speak_windows
        else:
            self._speak_fn = self._speak_pyttsx3

        while self.running:
            try:
                text = self.q.get(block=True, timeout=0.5)
            except _queue.Empty:
                continue
            except Exception:
                continue

            if text is None:           # shutdown sentinel
                break
            if text == "STOP":         # flush sentinel — already stopped above
                continue

            self._speaking = True
            try:
                self._speak_fn(text)
            except Exception as e:
                print(f"TTS Error: {e}")
            finally:
                self._speaking = False

    def _speak_windows(self, text: str):
        """
        Speak on Windows using PowerShell's built-in SpeechSynthesizer.
        Uses Rate 0 (default speed) for maximum clarity.
        Automatically selects the highest-quality installed voice available.
        """
        # Sanitize text: remove characters that break PowerShell string embedding
        safe_text = (
            text
            .replace("'", " ")
            .replace('"', " ")
            .replace('`', " ")
            .replace('\n', ' ')
            .replace('\r', '')
            .strip()
        )
        if not safe_text:
            return

        # Use Rate 0 (default) for clearest output.
        # Try to use the best available voice (David or Zira on Windows 10/11).
        ps_cmd = (
            "Add-Type -AssemblyName System.Speech; "
            "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$synth.Rate = 0; "
            # Prefer high-quality voices: Microsoft David Desktop > Zira Desktop > any installed
            "$voices = $synth.GetInstalledVoices() | Where-Object { $_.Enabled }; "
            "$preferred = $voices | Where-Object { $_.VoiceInfo.Name -like '*David*' -or $_.VoiceInfo.Name -like '*Zira*' }; "
            "if ($preferred) { $synth.SelectVoice($preferred[0].VoiceInfo.Name) }; "
            f"$synth.Speak('{safe_text}')"
        )
        try:
            proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            with self._lock:
                self._current_proc = proc
            proc.wait()
        except Exception as e:
            print(f"TTS Windows Error: {e}")
        finally:
            with self._lock:
                self._current_proc = None

    def _speak_pyttsx3(self, text: str):
        """Fallback for non-Windows platforms."""
        try:
            import pyttsx3
            if not hasattr(self, '_engine') or self._engine is None:
                self._engine = pyttsx3.init()
                self._engine.setProperty('rate', 185)
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as e:
            print(f"pyttsx3 Error: {e}")

    # ── Public API ───────────────────────────────────────────────────────────

    def speak(self, text: str):
        """Queue a text block for speech. Returns immediately."""
        if not text or not text.strip():
            return
        self.q.put(text)

    def stop_speaking(self):
        """
        Immediately interrupt current speech and discard all queued utterances.
        Kills the running PowerShell process if one is active.
        """
        import queue as _queue

        # 1. Kill any running speech process right now
        with self._lock:
            proc = self._current_proc
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

        # 2. Drain the queue (no task_done needed — we don't call Queue.join())
        while True:
            try:
                self.q.get_nowait()
            except _queue.Empty:
                break

        self._speaking = False

    def stream_to_overlay(self, generator, overlay=None):
        """
        Consume a streaming AI response and display it in the overlay panel.
        DOES NOT speak automatically — the user must click 'Read Summary' to hear it.
        This keeps TTS strictly opt-in and prevents unexpected auto-speech.
        """
        print("Assistant: ", end="", flush=True)
        if overlay:
            overlay.show()

        for chunk in generator:
            if not self.running:
                break
            print(chunk, end="", flush=True)
            if overlay:
                overlay.append(chunk)

        print()  # Newline after stream ends

    def speak_stream(self, generator, overlay=None):
        """
        Consume a streaming text generator chunk-by-chunk.
        Splits on sentence boundaries and queues each sentence for speech.
        Simultaneously writes chunks to the overlay panel.
        NOTE: Prefer stream_to_overlay() for display-only use to avoid auto-speech.
        """
        buffer = ""
        print("Assistant: ", end="", flush=True)
        if overlay:
            overlay.show()

        # Split on sentence-ending punctuation (. ? ! or newline) followed by whitespace
        sentence_end_pattern = re.compile(r'(?<=[.?!\n])\s+')

        for chunk in generator:
            if not self.running:
                break
            print(chunk, end="", flush=True)
            if overlay:
                overlay.append(chunk)
            buffer += chunk

            parts = sentence_end_pattern.split(buffer)
            if len(parts) > 1:
                for sentence in parts[:-1]:
                    clean = sentence.strip()
                    if clean:
                        self.speak(clean)
                buffer = parts[-1]

        # Flush any trailing partial sentence
        if buffer.strip():
            self.speak(buffer.strip())
        print()

    def stop(self):
        """Shut down the worker thread cleanly."""
        self.running = False
        self.stop_speaking()
        self.q.put(None)   # wake the blocked queue.get() so the thread can exit
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2)

    def is_speaking(self):
        """True while speech is actively playing or text is queued."""
        return self._speaking or not self.q.empty()

