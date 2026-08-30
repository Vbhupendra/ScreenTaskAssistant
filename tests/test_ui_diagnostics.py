"""
test_ui_diagnostics.py
Automated assertions for UI properties not covered by existing test files.
Tests are grouped by inspection area from the diagnostic report.
Manual/visual checks are noted as skipped with explanations.
"""
import sys
import os
import json
import unittest
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.hal.overlay import (
    OverlayWindow,
    FG_TEXT, FG_SUBTEXT,
    BG_MANTLE, BG_CRUST, BG_SURFACE,
    COLOR_BLUE, COLOR_GREEN, COLOR_RED, COLOR_YELLOW, COLOR_PURPLE, COLOR_CYAN,
    COMPACT_WIDTH, COMPACT_HEIGHT,
    STANDARD_WIDTH, STANDARD_HEIGHT,
    EXPANDED_WIDTH, EXPANDED_HEIGHT,
    MIN_WIDTH, MIN_HEIGHT, MAX_WIDTH, MAX_HEIGHT,
    SHORT_THRESHOLD, NORMAL_THRESHOLD,
)
from src.core.config_manager import get_config_path

# ── Short response < SHORT_THRESHOLD chars ──────────────────────────────────
SHORT_RESPONSE  = "ANSWER: Yes.\nREASON: Simple case.\nACTION: None needed."
# ── Normal response: SHORT_THRESHOLD < len < NORMAL_THRESHOLD ───────────────
NORMAL_RESPONSE = ("ANSWER: Detailed answer here.\nREASON: Because of several factors.\n"
                   "ACTION: Fix the import.\n") + ("x" * 300)
# ── Long response > NORMAL_THRESHOLD chars ──────────────────────────────────
LONG_RESPONSE   = "ANSWER: " + ("Long explanation. " * 80)


class UITestBase(unittest.TestCase):
    """Common setUp / tearDown for all UI diagnostic test cases."""

    def setUp(self):
        self._config_path = get_config_path()
        self._orig = {}
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._orig = json.load(f)
            except Exception:
                pass
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
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._orig, f, indent=4)

    def _is_packed(self, widget) -> bool:
        """Return True if widget is currently packed using _is_widget_packed."""
        return self.overlay._is_widget_packed(widget)

    def _set_mode(self, mode: str):
        self.overlay.set_size_mode(mode)
        self.overlay.root.update()

    def _push_text(self, text: str):
        self.overlay.full_text = text
        self.overlay._render_text()
        self.overlay.root.update()

    def _push_status(self, status: str):
        self.overlay._update_status_ui(status)
        self.overlay.root.update()


# ════════════════════════════════════════════════════════════════════════════
# Area 2 — ANSWER / REASON / ACTION rendering
# ════════════════════════════════════════════════════════════════════════════

class TestTextRendering(UITestBase):

    def test_answer_section_appears_in_text_widget(self):
        """After rendering an ANSWER block, the text widget must contain 'ANSWER'."""
        self._set_mode("STANDARD")
        self._push_text("ANSWER: This is the answer.\nREASON: Because.\nACTION: Do this.")
        content = self.overlay.text_area.get("1.0", tk.END)
        self.assertIn("ANSWER", content, "text_area must contain ANSWER header")
        self.assertIn("REASON", content, "text_area must contain REASON header")
        self.assertIn("ACTION", content, "text_area must contain ACTION header")

    def test_answer_body_text_not_empty(self):
        """The body after ANSWER: must appear in the text widget."""
        self._set_mode("STANDARD")
        self._push_text("ANSWER: This is the body.\nREASON: r\nACTION: a")
        content = self.overlay.text_area.get("1.0", tk.END)
        self.assertIn("This is the body", content)

    def test_plain_text_renders_without_crash(self):
        """A response without ANSWER/REASON/ACTION must render as plain text."""
        self._set_mode("STANDARD")
        self._push_text("The screen looks fine. No issues detected.")
        content = self.overlay.text_area.get("1.0", tk.END)
        self.assertIn("The screen looks fine", content)

    def test_empty_response_does_not_crash(self):
        """Empty full_text must result in an empty (not crashed) text widget."""
        self._set_mode("STANDARD")
        self._push_text("")
        content = self.overlay.text_area.get("1.0", tk.END).strip()
        self.assertEqual(content, "")


# ════════════════════════════════════════════════════════════════════════════
# Area 3 — Text tag color configuration
# ════════════════════════════════════════════════════════════════════════════

class TestTextTagColors(UITestBase):

    def _tag_fg(self, tag: str) -> str:
        return self.overlay.text_area.tag_cget(tag, "foreground")

    def test_header_answer_color(self):
        self.assertEqual(self._tag_fg("header_answer"), COLOR_BLUE)

    def test_header_reason_color(self):
        self.assertEqual(self._tag_fg("header_reason"), COLOR_YELLOW)

    def test_header_action_color(self):
        self.assertEqual(self._tag_fg("header_action"), COLOR_PURPLE)

    def test_normal_text_color(self):
        self.assertEqual(self._tag_fg("normal"), FG_TEXT)

    def test_code_block_color(self):
        self.assertEqual(self._tag_fg("code_block"), COLOR_GREEN)

    def test_inline_code_color(self):
        self.assertEqual(self._tag_fg("inline_code"), COLOR_CYAN)

    def test_bullet_symbol_color(self):
        self.assertEqual(self._tag_fg("bullet_symbol"), COLOR_YELLOW)

    def test_bold_tag_color(self):
        self.assertEqual(self._tag_fg("bold"), COLOR_PURPLE)


# ════════════════════════════════════════════════════════════════════════════
# Area 4 & 5 — Font and wrap configuration
# ════════════════════════════════════════════════════════════════════════════

class TestFontAndWrap(UITestBase):

    def test_text_area_wrap_mode_is_word(self):
        """text_area must wrap on word boundaries to prevent horizontal overflow."""
        self.assertEqual(self.overlay.text_area.cget("wrap"), "word")

    def test_text_area_default_font_family(self):
        font_str = str(self.overlay.text_area.cget("font"))
        self.assertIn("Segoe UI", font_str, "text_area should use Segoe UI font")

    def test_compact_label_wraplength_positive(self):
        """After entering compact mode, compact label wraplength must be > 0."""
        self._set_mode("COMPACT")
        self.assertGreater(self.overlay._compact_lbl.cget("wraplength"), 0)


# ════════════════════════════════════════════════════════════════════════════
# Area 7 & 14–16 — Widget visibility by layout mode
# ════════════════════════════════════════════════════════════════════════════

class TestWidgetLayoutVisibility(UITestBase):

    def test_standard_pipeline_frame_is_visible(self):
        """STANDARD: pipeline_frame must be a pack slave of root."""
        self._set_mode("STANDARD")
        self.assertTrue(
            self._is_packed(self.overlay.pipeline_frame),
            "pipeline_frame must be managed in STANDARD mode"
        )

    def test_standard_text_area_is_visible(self):
        """STANDARD: text_area must be a pack slave of root."""
        self._set_mode("STANDARD")
        self.assertTrue(
            self._is_packed(self.overlay.text_area),
            "text_area must be managed in STANDARD mode"
        )

    def test_standard_compact_label_is_hidden(self):
        """STANDARD: compact label must not be a pack slave of root."""
        self._set_mode("COMPACT")  # Force compact first to create the widget
        self._set_mode("STANDARD")
        if hasattr(self.overlay, "_compact_lbl"):
            self.assertFalse(
                self._is_packed(self.overlay._compact_lbl),
                "_compact_lbl must not be a pack slave in STANDARD mode"
            )

    def test_expanded_pipeline_frame_is_visible(self):
        """EXPANDED: pipeline_frame must be a pack slave of root."""
        self._set_mode("EXPANDED")
        self.assertTrue(self._is_packed(self.overlay.pipeline_frame))

    def test_expanded_text_area_is_visible(self):
        """EXPANDED: text_area must be a pack slave of root."""
        self._set_mode("EXPANDED")
        self.assertTrue(self._is_packed(self.overlay.text_area))

    def test_compact_pipeline_frame_is_hidden(self):
        """COMPACT: pipeline_frame must NOT be a pack slave of root."""
        self._set_mode("COMPACT")
        self.assertFalse(
            self._is_packed(self.overlay.pipeline_frame),
            "pipeline_frame must be hidden in COMPACT mode"
        )

    def test_compact_text_area_is_hidden(self):
        """COMPACT: text_area must NOT be a pack slave of root."""
        self._set_mode("COMPACT")
        self.assertFalse(
            self._is_packed(self.overlay.text_area),
            "text_area must not be a pack slave in COMPACT mode"
        )

    def test_compact_label_is_visible_in_compact_mode(self):
        """COMPACT: _compact_lbl must be a pack slave of root."""
        self._set_mode("COMPACT")
        self.assertTrue(
            self._is_packed(self.overlay._compact_lbl),
            "_compact_lbl must be a pack slave in COMPACT mode"
        )


# ════════════════════════════════════════════════════════════════════════════
# Area 8 & 9 — Active step font size vs pending/completed
# ════════════════════════════════════════════════════════════════════════════

class TestPipelineFontDistinction(UITestBase):

    def _font_size(self, idx: int) -> int:
        font_str = str(self.overlay.step_labels[idx].cget("font"))
        # Font string is like "Segoe UI 8 bold" or "{Segoe UI} 8 bold"
        parts = font_str.replace("{", "").replace("}", "").split()
        for part in parts:
            if part.isdigit():
                return int(part)
        return -1

    def test_active_step_font_larger_than_pending(self):
        """Active step font size (8) must be greater than pending step font size (7)."""
        self.overlay._update_status_ui("analyzing_screen")
        self.overlay.root.update()
        active_size  = self._font_size(0)  # step 0 is active
        pending_size = self._font_size(1)  # step 1 is pending
        self.assertGreater(active_size, pending_size,
            "Active step label should have larger font than pending step")

    def test_completed_step_same_size_as_pending(self):
        """Completed-but-not-current steps should be same font size as pending (7)."""
        self.overlay._update_status_ui("analyzing_screen")
        self.overlay._update_status_ui("understanding_context")
        self.overlay.root.update()
        completed_size = self._font_size(0)  # step 0 is now completed
        pending_size   = self._font_size(2)  # step 2 is pending
        self.assertEqual(completed_size, pending_size,
            "Completed step font size should match pending step font size")

    def test_final_completed_step_font_standard_weight(self):
        """On COMPLETED status, step 4 font should be size 7 (standard completed weight, distinct from ACTIVE 8pt)."""
        for s in ("analyzing_screen", "understanding_context",
                  "identifying_problems", "generating_solution", "completed"):
            self.overlay._update_status_ui(s)
        self.overlay.root.update()
        final_size = self._font_size(4)
        self.assertEqual(final_size, 7,
            "Final Complete step should have font size 7 on COMPLETED")


# ════════════════════════════════════════════════════════════════════════════
# Area 10 & 11 — Status indicator label text
# ════════════════════════════════════════════════════════════════════════════

class TestStatusIndicator(UITestBase):

    def _indicator_text(self) -> str:
        return self.overlay.status_indicator.cget("text")

    def _indicator_fg(self) -> str:
        return self.overlay.status_indicator.cget("fg")

    def test_idle_status_indicator(self):
        self._push_status("idle")
        self.assertIn("IDLE", self._indicator_text())
        self.assertEqual(self._indicator_fg(), COLOR_GREEN)

    def test_error_status_indicator_text_and_color(self):
        self._push_status("analyzing_screen")
        self._push_status("error")
        self.assertIn("ERROR", self._indicator_text())
        self.assertEqual(self._indicator_fg(), COLOR_RED)

    def test_cancelled_status_indicator_text_and_color(self):
        self._push_status("analyzing_screen")
        self._push_status("cancelled")
        self.assertIn("CANCELLED", self._indicator_text())
        self.assertEqual(self._indicator_fg(), COLOR_YELLOW)

    def test_completed_status_indicator_text_and_color(self):
        for s in ("analyzing_screen", "understanding_context",
                  "identifying_problems", "generating_solution", "completed"):
            self._push_status(s)
        self.assertIn("DONE", self._indicator_text())
        self.assertEqual(self._indicator_fg(), COLOR_GREEN)

    def test_analyzing_status_indicator(self):
        self._push_status("analyzing_screen")
        self.assertIn("ANALYZING", self._indicator_text())
        self.assertEqual(self._indicator_fg(), COLOR_BLUE)


# ════════════════════════════════════════════════════════════════════════════
# Area 12 — Connector count
# ════════════════════════════════════════════════════════════════════════════

class TestConnectorCount(UITestBase):

    def test_exactly_four_connectors(self):
        """5 steps → exactly 4 connector arrows."""
        self.assertEqual(len(self.overlay.step_connectors), 4)

    def test_exactly_five_step_labels(self):
        self.assertEqual(len(self.overlay.step_labels), 5)


# ════════════════════════════════════════════════════════════════════════════
# Area 13 — Button configuration
# ════════════════════════════════════════════════════════════════════════════

class TestButtonConfiguration(UITestBase):

    def test_read_button_text_non_empty(self):
        text = self.overlay.read_btn.cget("text")
        self.assertTrue(len(text) > 0, "Read button must have non-empty text")
        self.assertIn("Read", text)

    def test_save_report_button_text_non_empty(self):
        text = self.overlay.save_report_btn.cget("text")
        self.assertTrue(len(text) > 0)
        self.assertIn("Save", text)

    def test_read_button_cursor_hand(self):
        self.assertEqual(self.overlay.read_btn.cget("cursor"), "hand2")

    def test_save_report_button_cursor_hand(self):
        self.assertEqual(self.overlay.save_report_btn.cget("cursor"), "hand2")

    def test_read_button_no_crash_on_empty_text(self):
        """Read button click with empty full_text must not raise an exception."""
        self.overlay.full_text = ""
        try:
            self.overlay._on_read_clicked()
        except Exception as e:
            self.fail(f"_on_read_clicked raised {e} on empty full_text")

    def test_save_report_button_no_crash_on_empty_text(self):
        """Save report click with empty full_text must not raise an exception."""
        self.overlay.full_text = ""
        try:
            self.overlay._on_save_report_clicked()
        except Exception as e:
            self.fail(f"_on_save_report_clicked raised {e} on empty full_text")

    def test_buttons_packed_in_action_bar(self):
        """Both action buttons must be managed widgets inside action_bar."""
        self.assertTrue(bool(self.overlay.read_btn.winfo_manager()))
        self.assertTrue(bool(self.overlay.save_report_btn.winfo_manager()))


# ════════════════════════════════════════════════════════════════════════════
# Area 14 — Compact label content quality
# ════════════════════════════════════════════════════════════════════════════

class TestCompactLabelContent(UITestBase):

    def test_compact_label_strips_answer_prefix(self):
        """Compact preview must not start with raw 'ANSWER:' header."""
        self._set_mode("COMPACT")
        self.overlay.full_text = "ANSWER: The fix is to reload the module.\nREASON: stale cache\nACTION: restart"
        self.overlay._update_compact_label()
        text = self.overlay._compact_lbl.cget("text")
        self.assertFalse(
            text.upper().startswith("ANSWER:"),
            f"Compact label should strip ANSWER: prefix, got: {text!r}"
        )

    def test_compact_label_strips_command_header(self):
        """Compact preview must not display a raw 'Command:' header line."""
        self._set_mode("COMPACT")
        self.overlay.full_text = "🔍 Command: describe this\n─────\nANSWER: The screen is clean."
        self.overlay._update_compact_label()
        text = self.overlay._compact_lbl.cget("text")
        self.assertNotIn("Command:", text)

    def test_compact_label_truncates_long_first_line(self):
        """Compact label must truncate at 70 chars with ellipsis."""
        self._set_mode("COMPACT")
        long_line = "A" * 100
        self.overlay.full_text = f"ANSWER: {long_line}"
        self.overlay._update_compact_label()
        text = self.overlay._compact_lbl.cget("text")
        self.assertLessEqual(len(text), 73,  # 70 chars + "…" + small buffer
            "Compact label must truncate long lines")
        self.assertTrue(text.endswith("…"), "Truncated label must end with ellipsis")


# ════════════════════════════════════════════════════════════════════════════
# Area 17 — AUTO streaming lock
# ════════════════════════════════════════════════════════════════════════════

class TestAutoStreamingLock(UITestBase):

    def test_auto_locks_to_standard_during_analyzing_screen(self):
        """AUTO must resolve to STANDARD during analyzing_screen regardless of full_text."""
        self.overlay.set_size_mode("AUTO")
        self.overlay.full_text = "x"  # would be COMPACT if completed
        self.overlay._last_status = "analyzing_screen"
        mode = self.overlay._get_auto_mode_for_content()
        self.assertEqual(mode, "STANDARD",
            "AUTO should lock to STANDARD during active streaming states")

    def test_auto_resolves_short_content_to_compact_when_completed(self):
        self.overlay.set_size_mode("AUTO")
        self.overlay.full_text = "Yes."
        self.overlay._last_status = "completed"
        mode = self.overlay._get_auto_mode_for_content()
        self.assertEqual(mode, "COMPACT")

    def test_auto_resolves_long_content_to_expanded(self):
        self.overlay.set_size_mode("AUTO")
        self.overlay.full_text = "word " * 500  # > NORMAL_THRESHOLD
        self.overlay._last_status = "completed"
        mode = self.overlay._get_auto_mode_for_content()
        self.assertEqual(mode, "EXPANDED")


# ════════════════════════════════════════════════════════════════════════════
# Area 19 — Dimension clamping (MIN/MAX enforcement)
# ════════════════════════════════════════════════════════════════════════════

class TestDimensionClamping(UITestBase):

    def test_width_clamped_to_max(self):
        """Setting pref_width beyond MAX_WIDTH must be clamped in apply_geometry."""
        self.overlay.set_size_mode("STANDARD")
        self.overlay.is_manual_resized = True
        self.overlay.pref_width  = MAX_WIDTH + 500
        self.overlay.pref_height = STANDARD_HEIGHT
        self.overlay.apply_geometry()
        self.overlay.root.update()
        w = int(self.overlay.root.geometry().split("x")[0])
        self.assertLessEqual(w, MAX_WIDTH, f"Width {w} should not exceed MAX_WIDTH {MAX_WIDTH}")

    def test_width_clamped_to_min(self):
        """Setting pref_width below MIN_WIDTH must be clamped in apply_geometry."""
        self.overlay.set_size_mode("STANDARD")
        self.overlay.is_manual_resized = True
        self.overlay.pref_width  = MIN_WIDTH - 100
        self.overlay.pref_height = STANDARD_HEIGHT
        self.overlay.apply_geometry()
        self.overlay.root.update()
        w = int(self.overlay.root.geometry().split("x")[0])
        self.assertGreaterEqual(w, MIN_WIDTH, f"Width {w} should not be below MIN_WIDTH {MIN_WIDTH}")

    def test_height_clamped_to_max(self):
        self.overlay.set_size_mode("EXPANDED")
        self.overlay.is_manual_resized = True
        self.overlay.pref_width  = EXPANDED_WIDTH
        self.overlay.pref_height = MAX_HEIGHT + 500
        self.overlay.apply_geometry()
        self.overlay.root.update()
        h = int(self.overlay.root.geometry().split("x")[1].split("+")[0])
        self.assertLessEqual(h, MAX_HEIGHT)

    def test_height_clamped_to_min(self):
        self.overlay.set_size_mode("STANDARD")
        self.overlay.is_manual_resized = True
        self.overlay.pref_width  = STANDARD_WIDTH
        self.overlay.pref_height = MIN_HEIGHT - 50
        self.overlay.apply_geometry()
        self.overlay.root.update()
        h = int(self.overlay.root.geometry().split("x")[1].split("+")[0])
        self.assertGreaterEqual(h, MIN_HEIGHT)


# ════════════════════════════════════════════════════════════════════════════
# Area 22 — Short vs very long response behavior
# ════════════════════════════════════════════════════════════════════════════

class TestShortAndLongResponses(UITestBase):

    def test_short_response_in_auto_gives_compact_geometry(self):
        self.overlay.set_size_mode("AUTO")
        self.overlay._last_status = "completed"
        self._push_text(SHORT_RESPONSE)
        self.overlay.apply_geometry()
        self.overlay.root.update()
        h = int(self.overlay.root.geometry().split("x")[1].split("+")[0])
        self.assertEqual(h, COMPACT_HEIGHT, "Short response in AUTO should produce COMPACT height")

    def test_long_response_in_auto_gives_expanded_geometry(self):
        self.overlay.set_size_mode("AUTO")
        self.overlay._last_status = "completed"
        self._push_text(LONG_RESPONSE)
        self.overlay.apply_geometry()
        self.overlay.root.update()
        w = int(self.overlay.root.geometry().split("x")[0])
        h = int(self.overlay.root.geometry().split("x")[1].split("+")[0])
        self.assertEqual(w, EXPANDED_WIDTH)
        self.assertEqual(h, EXPANDED_HEIGHT)

    def test_long_response_content_present_in_text_widget(self):
        """Very long response must still appear in text_area (not silently dropped)."""
        self._set_mode("EXPANDED")
        self._push_text(LONG_RESPONSE)
        content = self.overlay.text_area.get("1.0", tk.END)
        self.assertIn("Long explanation", content)

    def test_empty_response_text_area_empty(self):
        self._set_mode("STANDARD")
        self._push_text("")
        content = self.overlay.text_area.get("1.0", tk.END).strip()
        self.assertEqual(content, "")

    @unittest.skip("MANUAL: Verify text_area yview()[1] < 1.0 with very long content — requires screen rendering")
    def test_long_response_requires_scrolling(self):
        """Very long response must not fit entirely in the text_area view (yview < 1.0)."""
        pass

    @unittest.skip("MANUAL: Verify no horizontal scrollbar appears for any response length — requires visual check")
    def test_no_horizontal_overflow(self):
        pass


# ════════════════════════════════════════════════════════════════════════════
# Manual checks as documented skips
# ════════════════════════════════════════════════════════════════════════════

class TestManualVisualChecks(UITestBase):

    @unittest.skip("MANUAL D1: Verify FG_TEXT on BG_MANTLE is perceptually readable")
    def test_contrast_fg_on_bg(self): pass

    @unittest.skip("MANUAL D3: Verify no text clipping at any supported window size")
    def test_no_text_clipping(self): pass

    @unittest.skip("MANUAL D4: Verify no horizontal scrollbar appears with long words")
    def test_no_horizontal_scrollbar(self): pass

    @unittest.skip("MANUAL D6: Verify resize grip is visible in bottom-right corner")
    def test_resize_grip_position(self): pass

    @unittest.skip("MANUAL D8: Verify pipeline bar is horizontally centered in panel")
    def test_pipeline_bar_centered(self): pass

    @unittest.skip("MANUAL D9: Verify button hover effects are visible")
    def test_button_hover_effects(self): pass

    @unittest.skip("MANUAL D12: Verify long response scrolls cleanly without layout jumps")
    def test_scroll_without_layout_jumps(self): pass


if __name__ == "__main__":
    unittest.main()
