# Black Box AI - User Guide

## Running the System (Background Mode)

The Black Box AI Assistant now runs as a **System Tray Application**. This allows it to stay active in the background without needing an open terminal.

To start the assistant:
1.  Run the command: `python src/main.py`.
2.  Look for the **Green Icon** in your system tray (Windows Taskbar / macOS Menu Bar).
3.  The system will notify you that it is online.

### Tray Icon Status Indicators
*   🟢 **Green**: Idle & Listening for the wake word.
*   🔵 **Blue**: Thinking (Reasoning with Gemini).
*   🟡 **Yellow**: Speaking (TTS Output).

### Stopping the System
Right-click the tray icon and select **Exit**.

---

## Interaction & Triggering

The system implements a **Strict Wake-Word Trigger**. It will only process your commands if you say the word:

> "**BlackBox**"
00000000000000000000000000
### Examples:
*   "**BlackBox**, what is on my screen"
*   "**BlackBox**, look at this code and explain it"
*   "**BlackBox**, read the first paragraph"

---

## Vision & Analysis

By default, the system optimizes performance by only "seeing" the screen if pixels have changed > 5%. However, using **Vision Keywords** forces the AI to look at the screen immediately:

*   **Look** / **See** / **Read** / **Describe** / **Analyze**

**Example**:
> **You**: "BlackBox, read this."
> **AI**: (Bypasses delta check) "The text on screen says..."

---

## Troubleshooting

*   **Icon not appearing**: Ensure `Pillow` and `pystray` are installed (run `pip install -r requirements.txt`).
*   **Not responding**: Ensure "BlackBox" is pronounced clearly. The system uses local Offline STT for privacy and speed.
*   **Permissions**: On first run, Windows/macOS may ask for Screen Recording or Microphone permissions. You **MUST** allow these for HAL components to function.
