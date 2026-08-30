import sys
import os
import time
import json
import unittest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.hal.overlay import (
    OverlayWindow,
    COMPACT_WIDTH, COMPACT_HEIGHT,
    STANDARD_WIDTH, STANDARD_HEIGHT,
    EXPANDED_WIDTH, EXPANDED_HEIGHT,
    SHORT_THRESHOLD, NORMAL_THRESHOLD,
    MIN_WIDTH, MIN_HEIGHT
)
from src.core.config_manager import get_config_path

class TestSizeModes(unittest.TestCase):
    def setUp(self):
        # Read and backup original config
        config_path = get_config_path()
        self.original_config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self.original_config = json.load(f)
            except Exception:
                pass
                
        # Write clean temporary config for isolation
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"GEMINI_API_KEY": "test_key"}, f, indent=4)
        except Exception:
            pass

    def tearDown(self):
        # Restore original config file
        config_path = get_config_path()
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.original_config, f, indent=4)
        except Exception:
            pass

    def test_static_size_modes_apply_geometry(self):
        """Verify window dimensions match hardcoded static values for each mode."""
        overlay = OverlayWindow()
        overlay.root.deiconify()
        
        # Test STANDARD mode
        overlay.set_size_mode("STANDARD")
        overlay.root.update()
        w = int(overlay.root.geometry().split("x")[0])
        h = int(overlay.root.geometry().split("x")[1].split("+")[0])
        self.assertEqual(w, STANDARD_WIDTH)
        self.assertEqual(h, STANDARD_HEIGHT)
        
        # Test EXPANDED mode
        overlay.set_size_mode("EXPANDED")
        overlay.root.update()
        w = int(overlay.root.geometry().split("x")[0])
        h = int(overlay.root.geometry().split("x")[1].split("+")[0])
        self.assertEqual(w, EXPANDED_WIDTH)
        self.assertEqual(h, EXPANDED_HEIGHT)
        
        # Test COMPACT mode
        overlay.set_size_mode("COMPACT")
        overlay.root.update()
        w = int(overlay.root.geometry().split("x")[0])
        h = int(overlay.root.geometry().split("x")[1].split("+")[0])
        self.assertEqual(w, COMPACT_WIDTH)
        self.assertEqual(h, COMPACT_HEIGHT)
        
        overlay.root.destroy()

    def test_auto_mode_adaptive_sizing(self):
        """Verify content character lengths map correctly to sizing modes in AUTO."""
        overlay = OverlayWindow()
        overlay.root.deiconify()
        overlay.set_size_mode("AUTO")
        
        # 1. Short content -> COMPACT
        overlay.full_text = "Short text answer."
        overlay._last_status = "completed"
        overlay.apply_geometry()
        overlay.root.update()
        w = int(overlay.root.geometry().split("x")[0])
        h = int(overlay.root.geometry().split("x")[1].split("+")[0])
        self.assertEqual(w, COMPACT_WIDTH)
        self.assertEqual(h, COMPACT_HEIGHT)
        
        # 2. Normal content -> STANDARD
        overlay.full_text = "This response is moderately long. " * 10 # ~350 chars
        overlay._last_status = "completed"
        overlay.apply_geometry()
        overlay.root.update()
        w = int(overlay.root.geometry().split("x")[0])
        h = int(overlay.root.geometry().split("x")[1].split("+")[0])
        self.assertEqual(w, STANDARD_WIDTH)
        self.assertEqual(h, STANDARD_HEIGHT)
        
        # 3. Long content -> EXPANDED
        overlay.full_text = "This response is very long, explaining many things in detail. " * 30 # ~1800 chars
        overlay._last_status = "completed"
        overlay.apply_geometry()
        overlay.root.update()
        w = int(overlay.root.geometry().split("x")[0])
        h = int(overlay.root.geometry().split("x")[1].split("+")[0])
        self.assertEqual(w, EXPANDED_WIDTH)
        self.assertEqual(h, EXPANDED_HEIGHT)
        
        overlay.root.destroy()

    def test_settings_persistence(self):
        """Verify UI preferences (selected mode and manual sizes) persist to config.json."""
        overlay = OverlayWindow()
        overlay.root.deiconify()
        overlay.set_size_mode("EXPANDED")
        
        # Check if saved to file
        config_path = get_config_path()
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data.get("ui_size_mode"), "EXPANDED")
            
        # Test loading back on a fresh window
        overlay2 = OverlayWindow()
        overlay2.root.deiconify()
        self.assertEqual(overlay2.size_mode, "EXPANDED")
        
        # Simulate manual resize & verify dimensions persist
        overlay2.is_manual_resized = True
        overlay2.pref_width = 550
        overlay2.pref_height = 450
        overlay2._save_ui_settings()
        
        overlay3 = OverlayWindow()
        overlay3.root.deiconify()
        self.assertTrue(overlay3.is_manual_resized)
        self.assertEqual(overlay3.pref_width, 550)
        self.assertEqual(overlay3.pref_height, 450)
        
        overlay.root.destroy()
        overlay2.root.destroy()
        overlay3.root.destroy()

    def test_manual_drag_positioning(self):
        """Verify that dragging the window sets manual positioning and persists correctly."""
        overlay = OverlayWindow()
        overlay.root.deiconify()
        
        # Simulate dragging the window to a custom screen position
        class MockEvent:
            x = 100
            y = 120
        overlay._start_drag(MockEvent())
        
        # Mock actual tk window coordinates for drag motion math
        overlay.root.geometry("+300+400")
        overlay.root.update()
        
        class MockMotionEvent:
            x = 150
            y = 170
        overlay._on_drag(MockMotionEvent())
        
        self.assertTrue(overlay.is_manual_positioned)
        self.assertEqual(overlay.pref_x, 350)
        self.assertEqual(overlay.pref_y, 450)
        
        # Verify persistence saves correctly
        overlay._end_drag(None)
        config_path = get_config_path()
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data.get("ui_pref_x"), 350)
            self.assertEqual(data.get("ui_pref_y"), 450)
            
        overlay.root.destroy()

    def test_compact_height_locked(self):
        """Verify that compact mode locks height to COMPACT_HEIGHT even when manual resize is active."""
        overlay = OverlayWindow()
        overlay.root.deiconify()
        
        overlay.size_mode = "COMPACT"
        overlay.is_manual_resized = True
        overlay.pref_width = 600
        overlay.pref_height = 500  # set a large height
        
        overlay.apply_geometry()
        overlay.root.update()
        
        w = int(overlay.root.geometry().split("x")[0])
        h = int(overlay.root.geometry().split("x")[1].split("+")[0])
        
        # Width should follow the manual preferred width (or default clamp),
        # but height should be strictly locked to COMPACT_HEIGHT
        self.assertEqual(w, 600)
        self.assertEqual(h, COMPACT_HEIGHT)
        
        overlay.root.destroy()

if __name__ == "__main__":
    unittest.main()
