import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def dry_run_test():
    print("=== Black Box Dry Run Test ===")
    
    # Patch components before importing or instantiating BlackBoxAgent
    with patch('src.core.actions.voice_output.VoiceOutput'), \
         patch('src.core.hal.overlay.OverlayWindow'), \
         patch('src.core.hal.vision.get_vision_provider'), \
         patch('src.core.reasoning.vlm.ReasoningEngine'), \
         patch('src.core.hal.audio.AudioProvider') as mock_audio_class, \
         patch('src.core.hal.tray.TrayManager'), \
         patch('src.core.hal.audio_worker.AudioWorker'):
         
        # Set up mock audio provider instance
        mock_ear = MagicMock()
        mock_ear.get_command.side_effect = ["hello", "blackbox analyze screen", None]
        mock_audio_class.return_value = mock_ear
        
        from src.main import BlackBoxAgent
        
        agent = BlackBoxAgent()
        
        # Override brain mock to check calls
        agent.brain = MagicMock()
        # Set is_speaking mock return value to False to avoid infinite wait loop
        agent.speaker.is_speaking.return_value = False
        
        print("Agent initialized with patched dependencies.")
        
        # Simulate a trigger callback
        print("Simulating wake word trigger...")
        agent._on_wake_word("blackbox what is this")
        
        # Verify if analyze_stream was called during the processing pipeline
        if agent.brain.analyze_stream.called:
            print("PASS: brain.analyze_stream was called after wake word.")
        else:
            print("FAIL: brain.analyze_stream was not called.")

    print("=== Test Complete ===")

if __name__ == "__main__":
    dry_run_test()
