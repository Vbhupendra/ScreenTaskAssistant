# Black Box AI - Refactor Plan (Thread Orchestration)

This document details the transition from a terminal-loop orchestrator to a non-blocking system tray application.

## Thread Architecture

The system is split into two primary execution context:

### 1. Main Thread (System Tray)
- **Role**: Manages the UI lifecycle and user interaction.
- **Library**: `pystray`
- **Entry Point**: `pystray.Icon(...).run()`
- **Responsibility**:
    - Renders the taskbar icon.
    - Handles status color changes (Green, Red/Blue, Yellow).
    - Manages the right-click menu and "Exit" logic.
    - Responds to system signals to ensure a clean shutdown.

### 2. Daemon Thread (Audio Worker)
- **Role**: Continuous Passive Listening.
- **Library**: `threading.Thread` (as a separate Class)
- **Responsibility**:
    - Polls the `AudioProvider` (Vosk) for speech.
    - Implements the strict "BlackBox" trigger.
    - Triggers the Vision + Reasoning pipeline via a callback when the wake word is detected.

## Trigger Logic

The system operates in a `Continuous-Passive-Listen` state but remains dormant until the specific phrase is heard:

```python
if "blackbox" in audio_text.lower():
    start_analysis()
```

## Visual Status States

| State | Color | Description |
| :--- | :--- | :--- |
| **Idle** | Green | Monitoring for "BlackBox". |
| **Thinking** | Blue/Red Pulse | LLM is processing the screen context. |
| **Speaking** | Yellow | Assistant is outputting voice. |
