"""
test_progress_visual_states.py
Verify that every backend status maps to the correct pipeline visual state
(PENDING/ACTIVE/COMPLETED/ERROR/CANCELLED) on all step labels and connectors.
"""
import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.hal.overlay import (
    OverlayWindow,
    FG_SUBTEXT, COLOR_BLUE, COLOR_GREEN, COLOR_RED, COLOR_YELLOW,
    BG_SURFACE,
    COMPACT_WIDTH, COMPACT_HEIGHT,
)
from src.core.config_manager import get_config_path


class TestProgressVisualStates(unittest.TestCase):
    """Verify pipeline label colours and connector arrow colours for every status."""

    def setUp(self):
        # Backup original config so tests are isolated
        self._config_path = get_config_path()
        self._orig = {}
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._orig = json.load(f)
            except Exception:
                pass
        # Write a clean test config while preserving existing key if present
        cfg = dict(self._orig)
        if "api_key" not in cfg and "GEMINI_API_KEY" not in cfg:
            cfg["GEMINI_API_KEY"] = ""
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)

        self.overlay = OverlayWindow()
        self.overlay.root.deiconify()
        self.overlay.root.update()

    def tearDown(self):
        self.overlay.root.destroy()
        # Restore original config
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._orig, f, indent=4)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _push_status(self, status: str):
        """Send a status update directly through the UI path (bypasses queue)."""
        self.overlay._update_status_ui(status)
        self.overlay.root.update()

    def _label_fg(self, idx: int) -> str:
        return self.overlay.step_labels[idx].cget("fg")

    def _connector_fg(self, idx: int) -> str:
        return self.overlay.step_connectors[idx].cget("fg")

    def _label_font(self, idx: int):
        return self.overlay.step_labels[idx].cget("font")

    # ── IDLE ─────────────────────────────────────────────────────────────────

    def test_idle_all_labels_subdued(self):
        """IDLE: every step and connector should be fully subdued."""
        self._push_status("idle")
        for i in range(5):
            self.assertEqual(self._label_fg(i), FG_SUBTEXT, f"Step {i} should be subdued on IDLE")
        for i in range(4):
            self.assertEqual(self._connector_fg(i), BG_SURFACE, f"Connector {i} should be off on IDLE")

    # ── ANALYZING_SCREEN ─────────────────────────────────────────────────────

    def test_analyzing_screen(self):
        """ANALYZING_SCREEN: step 0 (Screen) is ACTIVE-blue; steps 1-4 pending."""
        self._push_status("analyzing_screen")
        self.assertEqual(self._label_fg(0), COLOR_BLUE, "Step 0 should be ACTIVE (blue)")
        for i in range(1, 5):
            self.assertEqual(self._label_fg(i), FG_SUBTEXT, f"Step {i} should be PENDING")
        for i in range(4):
            self.assertEqual(self._connector_fg(i), BG_SURFACE, "No connectors lit yet")

    # ── UNDERSTANDING_CONTEXT ─────────────────────────────────────────────────

    def test_understanding_context(self):
        """UNDERSTANDING_CONTEXT: step 0 completed-green, step 1 ACTIVE-blue."""
        self._push_status("analyzing_screen")
        self._push_status("understanding_context")
        self.assertEqual(self._label_fg(0), COLOR_GREEN, "Step 0 should be COMPLETED (green)")
        self.assertEqual(self._label_fg(1), COLOR_BLUE,  "Step 1 should be ACTIVE (blue)")
        for i in range(2, 5):
            self.assertEqual(self._label_fg(i), FG_SUBTEXT, f"Step {i} should be PENDING")
        # Connector 0 (between step 0 and step 1) should now be green
        self.assertEqual(self._connector_fg(0), COLOR_GREEN, "Connector 0 should be lit green")
        for i in range(1, 4):
            self.assertEqual(self._connector_fg(i), BG_SURFACE, f"Connector {i} should still be off")

    # ── IDENTIFYING_PROBLEMS ─────────────────────────────────────────────────

    def test_identifying_problems(self):
        """IDENTIFYING_PROBLEMS: steps 0,1 green; step 2 ACTIVE-yellow (special accent)."""
        for s in ("analyzing_screen", "understanding_context", "identifying_problems"):
            self._push_status(s)
        self.assertEqual(self._label_fg(0), COLOR_GREEN,  "Step 0 should be COMPLETED")
        self.assertEqual(self._label_fg(1), COLOR_GREEN,  "Step 1 should be COMPLETED")
        self.assertEqual(self._label_fg(2), COLOR_YELLOW, "Step 2 (Problems) should be ACTIVE-yellow")
        for i in range(3, 5):
            self.assertEqual(self._label_fg(i), FG_SUBTEXT, f"Step {i} should be PENDING")
        self.assertEqual(self._connector_fg(0), COLOR_GREEN)
        self.assertEqual(self._connector_fg(1), COLOR_GREEN)
        self.assertEqual(self._connector_fg(2), BG_SURFACE)

    # ── GENERATING_SOLUTION ──────────────────────────────────────────────────

    def test_generating_solution(self):
        """GENERATING_SOLUTION: steps 0-2 green; step 3 ACTIVE-blue."""
        for s in ("analyzing_screen", "understanding_context",
                  "identifying_problems", "generating_solution"):
            self._push_status(s)
        for i in range(3):
            self.assertEqual(self._label_fg(i), COLOR_GREEN, f"Step {i} should be COMPLETED")
        self.assertEqual(self._label_fg(3), COLOR_BLUE,  "Step 3 (Solution) should be ACTIVE-blue")
        self.assertEqual(self._label_fg(4), FG_SUBTEXT,  "Step 4 should still be PENDING")
        for i in range(3):
            self.assertEqual(self._connector_fg(i), COLOR_GREEN, f"Connector {i} should be lit")
        self.assertEqual(self._connector_fg(3), BG_SURFACE, "Connector 3 should be off")

    # ── COMPLETED ────────────────────────────────────────────────────────────

    def test_completed(self):
        """COMPLETED: all steps green; all connectors green."""
        for s in ("analyzing_screen", "understanding_context",
                  "identifying_problems", "generating_solution", "completed"):
            self._push_status(s)
        for i in range(5):
            self.assertEqual(self._label_fg(i), COLOR_GREEN, f"Step {i} should be COMPLETED-green")
        for i in range(4):
            self.assertEqual(self._connector_fg(i), COLOR_GREEN, f"Connector {i} should be lit green")

    # ── ERROR ─────────────────────────────────────────────────────────────────

    def test_error_after_second_step(self):
        """ERROR after UNDERSTANDING_CONTEXT: step 0 green, step 1 red, rest subdued."""
        self._push_status("analyzing_screen")
        self._push_status("understanding_context")
        self._push_status("error")
        self.assertEqual(self._label_fg(0), COLOR_GREEN, "Step 0 should remain COMPLETED-green")
        self.assertEqual(self._label_fg(1), COLOR_RED,   "Step 1 should be ERROR-red")
        for i in range(2, 5):
            self.assertEqual(self._label_fg(i), FG_SUBTEXT, f"Step {i} should be subdued")
        self.assertEqual(self._connector_fg(0), COLOR_GREEN, "Connector 0 should be lit green")
        for i in range(1, 4):
            self.assertEqual(self._connector_fg(i), BG_SURFACE, f"Connector {i} should be off")

    def test_error_at_first_step(self):
        """ERROR at step 0 (ANALYZING_SCREEN): step 0 red, all others subdued."""
        self._push_status("analyzing_screen")
        self._push_status("error")
        self.assertEqual(self._label_fg(0), COLOR_RED, "Step 0 should be ERROR-red")
        for i in range(1, 5):
            self.assertEqual(self._label_fg(i), FG_SUBTEXT, f"Step {i} should be subdued")
        for i in range(4):
            self.assertEqual(self._connector_fg(i), BG_SURFACE, "No connectors lit on early error")

    # ── CANCELLED ────────────────────────────────────────────────────────────

    def test_cancelled_mid_flow(self):
        """CANCELLED mid-flow: steps up-to-and-including active step show amber, rest subdued."""
        self._push_status("analyzing_screen")
        self._push_status("understanding_context")
        self._push_status("cancelled")
        # Steps 0 and 1 (≤ active_idx=1) should be amber
        self.assertEqual(self._label_fg(0), COLOR_YELLOW, "Step 0 should be CANCELLED-amber")
        self.assertEqual(self._label_fg(1), COLOR_YELLOW, "Step 1 should be CANCELLED-amber")
        for i in range(2, 5):
            self.assertEqual(self._label_fg(i), FG_SUBTEXT, f"Step {i} should be subdued")
        # Connector 0 (< active_idx=1) should be amber
        self.assertEqual(self._connector_fg(0), COLOR_YELLOW, "Connector 0 should be amber")
        for i in range(1, 4):
            self.assertEqual(self._connector_fg(i), BG_SURFACE, f"Connector {i} should be off")

    # ── IDLE resets pipeline ──────────────────────────────────────────────────

    def test_idle_resets_after_completed(self):
        """IDLE after COMPLETED resets all steps and connectors to subdued."""
        for s in ("analyzing_screen", "understanding_context",
                  "identifying_problems", "generating_solution", "completed"):
            self._push_status(s)
        self._push_status("idle")
        for i in range(5):
            self.assertEqual(self._label_fg(i), FG_SUBTEXT, f"Step {i} should be reset")
        for i in range(4):
            self.assertEqual(self._connector_fg(i), BG_SURFACE, f"Connector {i} should be reset")
        self.assertEqual(self.overlay._current_active_idx, -1)


if __name__ == "__main__":
    unittest.main()
