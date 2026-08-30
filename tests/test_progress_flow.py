import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.reasoning.intent_classifier import Intent

class TestProgressFlow(unittest.TestCase):
    @patch('src.main.VoiceOutput')
    @patch('src.main.OverlayWindow')
    @patch('src.main.get_vision_provider')
    @patch('src.main.ReasoningEngine')
    @patch('src.main.AudioProvider')
    @patch('src.main.TrayManager')
    @patch('src.main.AudioWorker')
    def setUp(self, mock_audio_worker, mock_tray, mock_audio, mock_brain, mock_vision, mock_overlay, mock_voice):
        # Create instances
        self.mock_voice_inst = mock_voice.return_value
        self.mock_overlay_inst = mock_overlay.return_value
        self.mock_vision_inst = mock_vision.return_value
        self.mock_brain_inst = mock_brain.return_value
        self.mock_tray_inst = mock_tray.return_value
        
        # Import BlackBoxAgent inside the test environment
        from src.main import BlackBoxAgent
        self.agent = BlackBoxAgent()
        
    def test_successful_execution_transitions(self):
        """Verify the progress state updates during a successful screen query pipeline."""
        # 1. Mock VLM to stream a proper ANSWER/REASON/ACTION block
        mock_chunks = ["ANSWER: Problems found\n", "REASON: syntax error\n", "ACTION: fix code"]
        def mock_analyze_stream(image_bytes, prompt):
            for chunk in mock_chunks:
                yield chunk
        self.agent.brain.analyze_stream.side_effect = mock_analyze_stream
        
        # Bind the real stream_to_overlay implementation to the mock instance
        from src.core.actions.voice_output import VoiceOutput
        self.mock_voice_inst.stream_to_overlay = VoiceOutput.stream_to_overlay.__get__(self.mock_voice_inst, VoiceOutput)
        
        # 2. Run the command
        self.agent._process_command("blackbox describe this", Intent.UNDERSTAND)
        
        # 3. Assert states transition in order
        expected_status_calls = [
            call('analyzing_screen'),
            call('understanding_context'),
            call('identifying_problems'),
            # When ACTION: arrives in the buffer:
            call('generating_solution'),
            call('completed')
        ]
        self.mock_overlay_inst.update_status.assert_has_calls(expected_status_calls, any_order=False)
        
        # 4. Assert tray manager thinking state was pulsed and then returned to idle
        expected_tray_calls = [
            call('thinking'),
            call('idle')
        ]
        self.mock_tray_inst.update_state.assert_has_calls(expected_tray_calls, any_order=False)

    def test_unknown_command_aborts_early(self):
        """Verify that an unknown command immediately aborts and does not start the pipeline."""
        self.agent._process_command("play some music", Intent.UNKNOWN)
        
        # Verify that screen analysis/context states were NEVER called
        # self.agent._process_command should call self.overlay.update_status('idle')
        self.mock_overlay_inst.update_status.assert_called_with('idle')
        self.mock_vision_inst.capture.assert_not_called()
        self.mock_brain_inst.analyze_stream.assert_not_called()

    def test_error_sets_error_state(self):
        """Verify that an exception in the reasoning engine is caught and sets status to error."""
        # Force an exception on analyze_stream
        self.agent.brain.analyze_stream.side_effect = Exception("API connection timeout")
        
        # Run command
        self.agent._process_command("blackbox fix this", Intent.SOLVE)
        
        # Assert overlay status transitions to 'error' at the end, and tray resets to idle
        self.mock_overlay_inst.update_status.assert_called_with('error')
        self.mock_tray_inst.update_state.assert_called_with('idle')
        
        # Ensure it does not report 'completed'
        for call_arg in self.mock_overlay_inst.update_status.call_args_list:
            self.assertNotEqual(call_arg[0][0], 'completed')

    def test_cancellation_flow(self):
        """Verify that a cancel command updates status to cancelled and resets the state."""
        self.agent._process_command("stop", Intent.CANCEL)
        
        # Verify cancel logic sets cancelled status
        self.mock_overlay_inst.update_status.assert_called_with('cancelled')
        self.mock_tray_inst.update_state.assert_called_with('idle')
        self.mock_voice_inst.stop_speaking.assert_called()

if __name__ == "__main__":
    unittest.main()
