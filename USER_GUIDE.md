# Black Box AI - User Guide

## Running the System (Background Mode)

The Black Box AI Assistant runs as a **System Tray Application**. This allows it to stay active in the background without needing an open terminal.

### Option A: Running from Precompiled Executable (Recommended)
1. Download the ZIP file containing `ScreenTaskAssistant.exe` from the latest GitHub build artifact.
2. Extract the ZIP and double-click `ScreenTaskAssistant.exe` to launch it.
3. Look for the **Green Icon** in your system tray (Windows Taskbar).
4. The system will notify you that it is online.

### Option B: Running from Source
1. Ensure all dependencies are installed: `pip install -r requirements.txt`.
2. Run the command from the root directory: `python run.py`
3. Look for the **Green Icon** in your system tray.

### Tray Icon Status Indicators
*   🟢 **Green**: Idle & Listening for the wake word.
*   🔵 **Blue**: Thinking (Reasoning with Gemini).
*   🟡 **Yellow**: Speaking (TTS Output).

### Stopping the System
Right-click the tray icon and select **Exit**.

---
For Terminal - python src/main.py

## Interaction & Triggering

The system implements a **Strict Wake-Word Trigger**. It will only process your commands if you say the word:

> "**BlackBox**"

### Examples:
*   "**BlackBox**, what is on my screen"
*   "**BlackBox**, look at this code and explain it"
*   "**BlackBox**, read the first paragraph"

---

## Intelligent Routing & Intents

The system uses a lightweight, local regex-based classification engine to instantly categorize your commands without calling an external LLM. Commands are routed into 5 core intents, optimizing how the system acts on your query:

| Intent | Purpose / Action | Example Phrases |
| :--- | :--- | :--- |
| **UNDERSTAND** | Describe screen layout, widgets, and UI elements. | `"what's this"`, `"describe the screen"`, `"look at this"` |
| **DIAGNOSE** | Scan for errors, crashes, stack traces, and bugs. | `"what's wrong"`, `"find the error"`, `"debug this exception"` |
| **SOLVE** | Request a step-by-step code fix or solution. | `"fix this"`, `"solve the git merge conflict"`, `"how do I fix this"` |
| **EXPLAIN** | Explain a file, code snippet, layout, or concepts. | `"explain the Dockerfile"`, `"what does this mean"` |
| **SUMMARIZE** | Provide a high-level summary of text/content. | `"summarize this"`, `"give me a brief summary"` |

---

## Context-Dependent Pronouns (Screen Awareness)

When you use pronouns referring to context, the AI automatically evaluates the current screen/active window:
*   **"this" / "that" / "here" / "it"** (e.g., *"What is wrong here?"*, *"Explain that"*, *"Fix it"*)
*   The system immediately captures a screenshot at the moment you speak the trigger word and resolves the pronouns against the screen's visual layout.

---

## Robust Speech-to-Text Normalization

Speech-to-text (STT) recognition is prone to transcription errors. The system automatically normalizes common mistakes before routing intents:
*   **Phonetics**: `"dis"` $\rightarrow$ `"this"`, `"dat"` $\rightarrow$ `"that"`, `"whats"` $\rightarrow$ `"what's"`
*   **Acoustic Errors**: `"scream"` $\rightarrow$ `"screen"`, `"cold"` $\rightarrow$ `"code"`, `"on my stream"` $\rightarrow$ `"on my screen"`, `"photograph"` $\rightarrow$ `"paragraph"`
*   *This ensures command detection is smooth even in noisy environments.*

---

## Instant Cancellation

If the assistant is speaking or processing, you can immediately halt all actions and reset the tray application back to idle listening by saying:
*   **"Stop"**
*   **"Cancel"**
*   **"Nevermind"**
*   **"Abort"**
*   **"Quit"**

---

## Voice & Display Response Format

To ensure answers are clear, technical, and fast, voice responses and overlay texts follow a strict structure:
1. **ANSWER**: The direct solution or description first.
2. **REASON**: The brief reason explaining why the issue occurs.
3. **ACTION**: The exact step or command to run to resolve it.

*Example:*
> "I found the problem. Your Python environment is missing the `requests` package. Run: `pip install requests`"

---

## Troubleshooting

*   **Icon not appearing**: Ensure `Pillow` and `pystray` are installed (run `pip install -r requirements.txt`).
*   **Not responding**: Ensure "BlackBox" is pronounced clearly. The system uses local Offline STT for privacy and speed.
*   **Permissions**: On first run, Windows/macOS may ask for Screen Recording or Microphone permissions. You **MUST** allow these for HAL components to function.

