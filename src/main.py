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
from src.core.reasoning.intent_classifier import IntentClassifier, Intent

# ---------------------------------------------------------------------------
# Module-level constants – built once, reused on every command
# ---------------------------------------------------------------------------
_INTENT_PROMPTS = {
    Intent.UNDERSTAND: "Analyze and describe what is currently visible on my screen.",
    Intent.DIAGNOSE:   "Check the screen for any errors, bugs, or anomalies, and diagnose the issue.",
    Intent.SOLVE:      "Provide a complete, step-by-step solution or code fix to resolve the problem visible on the screen.",
    Intent.EXPLAIN:    "Explain the code, interface, or layout shown on my screen.",
    Intent.SUMMARIZE:  "Provide a concise summary of the content and structure on my screen."
}

# Short generic triggers whose full text should be REPLACED by the intent prompt
_GENERIC_TRIGGERS = {
    Intent.UNDERSTAND: {"what's this", "what is this", "what's on my screen", "what is on my screen",
                        "what do you see", "describe this", "describe the screen",
                        "look at this", "check this", "check that", "what am i looking at"},
    Intent.DIAGNOSE:   {"what's wrong", "what is wrong", "find the error", "find error",
                        "find the bug", "find the problem", "diagnose", "analyze the error",
                        "what's the bug", "what is the bug", "look for error",
                        "any error", "check for error", "check the error", "debug this"},
    Intent.SOLVE:      {"fix this", "solve this", "solve that", "fix the bug", "correct this",
                        "resolve this", "fix it", "solve it", "make it work"},
    Intent.EXPLAIN:    {"explain this", "explain that", "explain how", "explain why",
                        "what does this mean", "how does this work", "explain the code"},
    Intent.SUMMARIZE:  {"summarize this", "give me a summary", "what is the summary",
                        "summarize the screen", "summarize the text"}
}

# Single shared instance — avoids recreating on every voice command
_classifier = IntentClassifier()

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
            on_restart_callback=self.restart,
            on_show_callback=self.overlay.show,
            on_hide_callback=self.overlay.hide
        )

        # Register overlay action-button callbacks
        self.overlay.set_callbacks(
            on_read=self._handle_read_aloud,
            on_save_report=self._handle_save_report
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

    # ── Overlay Action Button Handlers ────────────────────────────────────────

    def _handle_read_aloud(self, text: str):
        """Called by overlay Read Summary button.
        Receives clean, code-stripped text and speaks it aloud.
        Runs on a daemon thread so Tkinter is never blocked.
        """
        if not text:
            return
        print(">> Read Summary requested. Speaking clean text...")
        self.speaker.stop_speaking()
        self.speaker.speak(text)

    def _handle_save_report(self, markdown_text: str):
        """Called by overlay Save Report button.
        Opens a native save-file dialog (on the Tkinter main thread via after())
        and writes the full markdown content to the chosen location.
        """
        import datetime
        from tkinter import filedialog, messagebox

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"BlackBox_Report_{timestamp}.md"

        def _do_save():
            path = filedialog.asksaveasfilename(
                title="Save Report",
                initialfile=default_name,
                defaultextension=".md",
                filetypes=[
                    ("Markdown files", "*.md"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )
            if not path:
                return  # User cancelled
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("# BlackBox Pro — Analysis Report\n")
                    f.write(f"*Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                    f.write("---\n\n")
                    f.write(markdown_text)
                print(f">> Report saved to: {path}")
                messagebox.showinfo("Report Saved", f"Report saved to:\n{path}")
            except Exception as e:
                print(f">> Error saving report: {e}")
                messagebox.showerror("Save Error", f"Could not save report:\n{e}")

        # Schedule on Tkinter's main thread — required for file dialogs
        if hasattr(self, 'overlay') and self.overlay.root:
            self.overlay.root.after(0, _do_save)

    # ──────────────────────────────────────────────────────────────────────────

    def restart(self):
        print(f">> Restarting {APP_NAME}...")
        self._restarting = True
        self.stop()
        
        # Re-initialize and start
        # In a real scenario, we might want to use os.execv to truly restart the process
        # but for this architecture, we'll try a clean re-init
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def _on_wake_word(self, raw_text: str, intent: str = Intent.UNKNOWN):
        """Callback triggered by AudioWorker when a trigger condition is met."""
        if intent == Intent.CANCEL:
            self._handle_cancel()
            return

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
        self._process_command(raw_text, intent)

    def _handle_cancel(self):
        """Cancels any ongoing speech and resets the application state."""
        print(">> Cancel command received. Stopping current actions...")
        self.speaker.stop_speaking()
        self.overlay.clear()
        self.overlay.update_status('cancelled')
        self.tray.update_state('idle')
        self.audio_worker.resume_listening()
        self.speaker.speak("Action cancelled.")

    def _process_command(self, raw_text: str, intent: str = Intent.UNKNOWN):
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
                        intent = _classifier.classify(clean_command)
                        break
                    time.sleep(0.05)
                
                if not clean_command:
                    clean_command = "Analyze current screen."
                    intent = Intent.UNDERSTAND
            
            if intent == Intent.UNKNOWN and clean_command:
                intent = _classifier.classify(clean_command)

            if intent == Intent.CANCEL:
                self._handle_cancel()
                return

            if intent == Intent.UNKNOWN:
                print(f">> Unknown intent for command: {clean_command}. Skipping task pipeline.")
                self.overlay.clear()
                self.overlay.append(f"🔍 **Command:** {clean_command}\n\n")
                self.overlay.append("❌ **Command not recognized.**\n")
                self.overlay.append("Please use a screen-related command (describe, diagnose, fix, explain, summarize).\n")
                self.overlay.update_status('idle')
                self.tray.update_state('idle')
                self.audio_worker.resume_listening()
                return

            # Normalize command based on detected intent
            clean_command = self._normalize_command_with_intent(clean_command, intent)
            
            print(f">> Triggered! Intent: {intent} | Command: {clean_command}")
            
            # Pause listening to avoid feedback or duplicate triggers
            self.audio_worker.pause_listening()
            
            # Step 1: ANALYZING SCREEN
            self.overlay.clear()
            self.overlay.append(f"🔍 **Command:** {clean_command}\n\n")
            self.overlay.append("📸 **Analyzing the screen...**\n")
            self.overlay.update_status('analyzing_screen')
            self.tray.update_state('thinking')
            
            # Use pre-captured context frame or capture a fresh one if needed
            urgent = self._is_urgent(clean_command)
            frame = self.context_frame if (self.context_frame and not urgent) else self.vision.capture(force=urgent)
            
            if not frame:
                print(">> Warning: No image frame captured. Proceeding with text-only.")
            
            # Step 2: UNDERSTANDING CONTEXT
            self.overlay.append("🧠 **Understanding the context...**\n")
            self.overlay.update_status('understanding_context')
            
            # Stream AI response to overlay only — NO auto-speech.
            # The user can click the 'Read Summary' button to hear the result.
            print(f">> Thinking ({MODEL_NAME})...")
            stream = self.brain.analyze_stream(image_bytes=frame, prompt=clean_command)
            
            # Prepare overlay before streaming: clear the progress messages and keep Query
            self.overlay.clear()
            self.overlay.append(f"🔍 **Command:** {clean_command}\n")
            self.overlay.append("─" * 40 + "\n\n")
            
            # Display only — no auto TTS. User controls speech via the 'Read Summary' button.
            # stream_to_overlay will handle updating to IDENTIFYING_PROBLEMS and GENERATING_SOLUTION
            self.speaker.stream_to_overlay(stream, overlay=self.overlay)
            
            # Step 5: COMPLETED state
            self.overlay.update_status('completed')
            self.tray.update_state('idle')
            
            # Reset state after streaming completes
            self.context_frame = None
            self.audio_worker.resume_listening()
            
        except Exception as e:
            print(f"Error processing command: {e}")
            self.overlay.update_status('error')
            try:
                self.speaker.speak("I encountered a system error. Please check the logs.")
            except Exception as tts_err:
                print(f">> TTS error during error handler: {tts_err}")
            
            self.context_frame = None
            self.tray.update_state('idle')
            self.audio_worker.resume_listening()

    def _normalize_command_with_intent(self, text: str, intent: str) -> str:
        """Standardizes user commands using the classified intent.
        
        Generic/short trigger phrases are replaced with a full optimized prompt.
        Longer, specific user sentences are kept verbatim with the intent appended.
        Uses module-level _INTENT_PROMPTS and _GENERIC_TRIGGERS constants.
        """
        if intent not in _INTENT_PROMPTS:
            return text
        
        cleaned_text = text.lower().strip()
        triggers = _GENERIC_TRIGGERS.get(intent, set())
        
        # Replace with the optimized prompt if the command is a known generic trigger
        # or is too short to carry useful context (<=3 words).
        is_generic = any(trigger in cleaned_text for trigger in triggers) or len(cleaned_text.split()) <= 3
        
        if is_generic:
            return _INTENT_PROMPTS[intent]
        else:
            return f"{text} (Instruction: {_INTENT_PROMPTS[intent]})"

    def _is_urgent(self, text: str) -> bool:
        """Determines if the command requires a fresh/forced capture."""
        keywords = ["look", "read", "error", "see", "describe", "what is", "analyze", "help"]
        return any(keyword in text.lower() for keyword in keywords)

if __name__ == "__main__":
    agent = BlackBoxAgent()
    agent.start()
