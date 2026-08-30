import tkinter as tk
from tkinter import scrolledtext
import queue
import json
import os

# ── Colour palette ───────────────────────────────────────────────────────────
# Slightly warmer dark tones to improve legibility on consumer displays.
BG_BASE    = "#0d0d14"   # Window background
BG_MANTLE  = "#13131e"   # Text-area background
BG_CRUST   = "#090910"   # Title/footer bar background
BG_SURFACE = "#1c1c2a"   # Separators, raised elements

FG_TEXT    = "#e8e8f0"   # Primary body text — slightly off-white for comfort
FG_SUBTEXT = "#8888a0"   # Muted/secondary text

COLOR_BLUE   = "#5b9cf6"  # Primary accent
COLOR_PURPLE = "#9b6ef7"  # Secondary accent
COLOR_GREEN  = "#3ddc84"  # Success / completed
COLOR_RED    = "#e8607a"  # Error / listening
COLOR_YELLOW = "#f5c842"  # Warning / problems
COLOR_CYAN   = "#3dd6f5"  # Speaking

# ── Centralized sizing constants ─────────────────────────────────────────────
MIN_WIDTH  = 340
MAX_WIDTH  = 820
MIN_HEIGHT = 130
MAX_HEIGHT = 660

COMPACT_WIDTH  = 360
COMPACT_HEIGHT = 130

STANDARD_WIDTH  = 480
STANDARD_HEIGHT = 390

EXPANDED_WIDTH  = 680
EXPANDED_HEIGHT = 540

# AUTO mode text-length thresholds (characters of clean readable text)
SHORT_THRESHOLD  = 160   # < 160  → COMPACT
NORMAL_THRESHOLD = 620   # 160–620 → STANDARD
# > 620 → EXPANDED (scrolling enabled when content overflows)
LONG_THRESHOLD   = 1500

# Status label abbreviations to keep title bar tidy at all widths
_STATUS_LABELS = {
    "idle":                "● IDLE",
    "listening":           "● LISTENING",
    "thinking":            "● THINKING",
    "speaking":            "● SPEAKING",
    "analyzing_screen":    "● ANALYZING",
    "understanding_context": "● UNDERSTANDING",
    "identifying_problems":  "● IDENTIFYING",
    "generating_solution":   "● GENERATING",
    "completed":           "● DONE",
    "error":               "● ERROR",
    "cancelled":           "● CANCELLED",
}

_STATUS_COLORS = {
    "idle":                COLOR_GREEN,
    "listening":           COLOR_RED,
    "thinking":            COLOR_PURPLE,
    "speaking":            COLOR_CYAN,
    "analyzing_screen":    COLOR_BLUE,
    "understanding_context": COLOR_PURPLE,
    "identifying_problems":  COLOR_YELLOW,
    "generating_solution":   COLOR_GREEN,
    "completed":           COLOR_GREEN,
    "error":               COLOR_RED,
    "cancelled":           COLOR_YELLOW,
}

# Pipeline stage → step index mapping
# -1 = no pipeline change for this status
_STAGE_INDEX = {
    "analyzing_screen":      0,
    "listening":             0,
    "understanding_context": 1,
    "identifying_problems":  2,
    "thinking":              2,
    "generating_solution":   3,
    "speaking":              3,
    "completed":             4,
    # Terminal states that freeze at current step
    "cancelled":            -1,
    "error":                -1,
    "idle":                 -1,
}


class OverlayWindow:
    """Thread-safe borderless floating panel with premium styling and adaptive sizing."""

    def __init__(self):
        self.queue = queue.Queue()
        self.root = None
        self.text_area = None

        self.size_mode = "AUTO"
        self._last_status = "idle"       # stored in its original case
        self._current_active_idx = -1

        self.pref_width = None
        self.pref_height = None
        self.is_manual_resized = False

        self.pref_x = None
        self.pref_y = None
        self.is_manual_positioned = False

        # Debounce resize-save: only persist after drag ends
        self._resize_save_pending = False

        self._on_read_callback = None
        self._on_save_report_callback = None

        self._load_ui_settings()
        self._initialize_gui()

    # ── Settings persistence ─────────────────────────────────────────────────

    def _load_ui_settings(self):
        try:
            from src.core.config_manager import get_config_path
            p = get_config_path()
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.size_mode  = data.get("ui_size_mode", "AUTO").upper()
                pw = data.get("ui_pref_width")
                ph = data.get("ui_pref_height")
                if pw and ph:
                    self.pref_width  = int(pw)
                    self.pref_height = int(ph)
                    self.is_manual_resized = True
                px = data.get("ui_pref_x")
                py = data.get("ui_pref_y")
                if px is not None and py is not None:
                    self.pref_x = int(px)
                    self.pref_y = int(py)
                    self.is_manual_positioned = True
        except Exception as e:
            print(f"UI settings load error: {e}")

    def _save_ui_settings(self):
        try:
            from src.core.config_manager import get_config_path
            p = get_config_path()
            data = {}
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["ui_size_mode"] = self.size_mode
            if self.is_manual_resized and self.pref_width and self.pref_height:
                data["ui_pref_width"]  = self.pref_width
                data["ui_pref_height"] = self.pref_height
            else:
                data.pop("ui_pref_width",  None)
                data.pop("ui_pref_height", None)
            if self.is_manual_positioned and self.pref_x is not None and self.pref_y is not None:
                data["ui_pref_x"] = self.pref_x
                data["ui_pref_y"] = self.pref_y
            else:
                data.pop("ui_pref_x", None)
                data.pop("ui_pref_y", None)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"UI settings save error: {e}")

    # ── GUI bootstrap ────────────────────────────────────────────────────────

    def _initialize_gui(self):
        self.root = tk.Tk()
        self.root.title("BlackBox Pro")
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.configure(bg=BG_BASE)
        # Single-pixel border using the root's highlight; colour matches accent
        self.root.config(
            highlightbackground=BG_SURFACE,
            highlightcolor=BG_SURFACE,
            highlightthickness=1,
        )

        self.full_text = ""

        self._build_title_bar()
        self._build_pipeline_bar()
        self._build_text_area()
        self._build_action_bar()

        # Bind configure event for automatic label wrapping on resize
        self.root.bind("<Configure>", self._on_configure)

        self.apply_geometry()
        self._process_queue()
        self.root.withdraw()

    # ── Title bar ────────────────────────────────────────────────────────────

    def _build_title_bar(self):
        self.title_bar = tk.Frame(self.root, bg=BG_CRUST, height=32)
        self.title_bar.pack(fill=tk.X, side=tk.TOP)
        self.title_bar.pack_propagate(False)

        # App title
        self.title_label = tk.Label(
            self.title_bar, text="BlackBox Pro",
            bg=BG_CRUST, fg=FG_TEXT, font=("Segoe UI", 9, "bold"),
        )
        self.title_label.pack(side=tk.LEFT, padx=(12, 0))

        # Close button — right-most
        self.close_button = tk.Button(
            self.title_bar, text="✕",
            bg=BG_CRUST, fg=FG_SUBTEXT,
            activebackground=COLOR_RED, activeforeground=BG_CRUST,
            bd=0, font=("Segoe UI", 9), cursor="hand2",
            padx=8, pady=0,
            command=self.hide,
        )
        self.close_button.pack(side=tk.RIGHT)
        self.close_button.bind("<Enter>", lambda e: self.close_button.config(fg=COLOR_RED))
        self.close_button.bind("<Leave>", lambda e: self.close_button.config(fg=FG_SUBTEXT))

        # Status dot — right of close
        self.status_indicator = tk.Label(
            self.title_bar, text="● IDLE",
            bg=BG_CRUST, fg=COLOR_GREEN,
            font=("Segoe UI", 8, "bold"),
        )
        self.status_indicator.pack(side=tk.RIGHT, padx=(0, 8))

        # Size-mode micro-buttons
        self.size_frame = tk.Frame(self.title_bar, bg=BG_CRUST)
        self.size_frame.pack(side=tk.RIGHT, padx=(0, 10))

        self.size_buttons = {}
        for mode in ("COMPACT", "AUTO", "STANDARD", "EXPANDED"):
            btn = tk.Button(
                self.size_frame, text=mode[0],
                bg=BG_CRUST, fg=FG_SUBTEXT,
                activebackground=BG_SURFACE, activeforeground=FG_TEXT,
                bd=0, font=("Segoe UI", 7, "bold"),
                cursor="hand2", padx=3, pady=1,
                command=lambda m=mode: self.set_size_mode(m),
            )
            btn.pack(side=tk.LEFT, padx=1)
            self.size_buttons[mode] = btn
        self._update_size_buttons()

        # Drag support
        for w in (self.title_bar, self.title_label):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)
            w.bind("<ButtonRelease-1>", self._end_drag)

        # Title-bar separator
        tk.Frame(self.root, bg=BG_SURFACE, height=1).pack(fill=tk.X, side=tk.TOP)

    # ── Pipeline progress bar ─────────────────────────────────────────────────

    def _build_pipeline_bar(self):
        self.pipeline_frame = tk.Frame(self.root, bg=BG_CRUST, height=24)
        self.pipeline_frame.pack(fill=tk.X, side=tk.TOP)
        self.pipeline_frame.pack_propagate(False)

        # Centre the steps using a nested frame + pack fill/expand trick
        inner = tk.Frame(self.pipeline_frame, bg=BG_CRUST)
        inner.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.steps = ["Screen", "Context", "Problems", "Solution", "Complete"]
        self.step_labels = []
        self.step_connectors = []   # ‹ store arrow labels for dynamic recoloring

        for idx, name in enumerate(self.steps):
            lbl = tk.Label(
                inner, text=name,
                bg=BG_CRUST, fg=FG_SUBTEXT,
                font=("Segoe UI", 7, "bold"),
            )
            lbl.grid(row=0, column=idx * 2)
            self.step_labels.append(lbl)
            if idx < len(self.steps) - 1:
                arrow = tk.Label(
                    inner, text="›",
                    bg=BG_CRUST, fg=BG_SURFACE,
                    font=("Segoe UI", 9),
                )
                arrow.grid(row=0, column=idx * 2 + 1, padx=4)
                self.step_connectors.append(arrow)

        # Separator below pipeline
        self.pipeline_separator = tk.Frame(self.root, bg=BG_SURFACE, height=1)
        self.pipeline_separator.pack(fill=tk.X, side=tk.TOP)

    # ── Text area ─────────────────────────────────────────────────────────────

    def _build_text_area(self):
        self.text_area = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            bg=BG_MANTLE, fg=FG_TEXT,
            insertbackground=FG_TEXT,
            font=("Segoe UI", 10),
            bd=0, highlightthickness=0,
            padx=12, pady=10,        # internal padding; avoids separate padx in pack
            spacing1=2, spacing2=3, spacing3=2,
        )
        try:
            self.text_area.vbar.config(
                bg=BG_MANTLE, activebackground=BG_SURFACE,
                troughcolor=BG_CRUST,
                borderwidth=0, width=6, relief=tk.FLAT,
            )
        except Exception:
            pass

        # Text tags
        self.text_area.tag_config("normal",
            font=("Segoe UI", 10), foreground=FG_TEXT)
        self.text_area.tag_config("bold",
            font=("Segoe UI", 10, "bold"), foreground=COLOR_PURPLE)
        self.text_area.tag_config("header",
            font=("Segoe UI", 11, "bold"), foreground=COLOR_BLUE,
            spacing1=6, spacing3=2)
        self.text_area.tag_config("code_block",
            font=("Consolas", 9), foreground=COLOR_GREEN,
            background=BG_CRUST, lmargin1=12, lmargin2=12, rmargin=12,
            spacing1=2, spacing3=2)
        self.text_area.tag_config("inline_code",
            font=("Consolas", 9), foreground=COLOR_CYAN,
            background=BG_SURFACE)
        self.text_area.tag_config("bullet_symbol",
            font=("Segoe UI", 10), foreground=COLOR_YELLOW)

        # ANSWER / REASON / ACTION section headers
        self.text_area.tag_config("header_answer",
            font=("Segoe UI", 10, "bold"), foreground=COLOR_BLUE,
            spacing1=10, spacing3=2)
        self.text_area.tag_config("header_reason",
            font=("Segoe UI", 10, "bold"), foreground=COLOR_YELLOW,
            spacing1=10, spacing3=2)
        self.text_area.tag_config("header_action",
            font=("Segoe UI", 10, "bold"), foreground=COLOR_PURPLE,
            spacing1=10, spacing3=2)

    # ── Action / footer bar ───────────────────────────────────────────────────

    def _build_action_bar(self):
        self.action_bar_separator = tk.Frame(self.root, bg=BG_SURFACE, height=1)
        self.action_bar_separator.pack(fill=tk.X, side=tk.BOTTOM)

        self.action_bar = tk.Frame(self.root, bg=BG_CRUST, height=38)
        self.action_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.action_bar.pack_propagate(False)

        btn_defaults = dict(
            bg=BG_SURFACE, relief=tk.FLAT, bd=0, cursor="hand2",
            font=("Segoe UI", 8, "bold"), padx=12, pady=5,
        )

        self.read_btn = tk.Button(
            self.action_bar, text="🔊 Read Summary",
            fg=COLOR_BLUE, activebackground=COLOR_BLUE, activeforeground=BG_CRUST,
            command=self._on_read_clicked, **btn_defaults,
        )
        self.read_btn.pack(side=tk.LEFT, padx=(8, 3), pady=5)

        self.save_report_btn = tk.Button(
            self.action_bar, text="💾 Save Report",
            fg=COLOR_GREEN, activebackground=COLOR_GREEN, activeforeground=BG_CRUST,
            command=self._on_save_report_clicked, **btn_defaults,
        )
        self.save_report_btn.pack(side=tk.LEFT, padx=3, pady=5)

        def _make_hover(btn, fg_normal, fg_hover_bg):
            btn.bind("<Enter>", lambda e: btn.config(bg=fg_hover_bg, fg=BG_CRUST))
            btn.bind("<Leave>", lambda e: btn.config(bg=BG_SURFACE, fg=fg_normal))

        _make_hover(self.read_btn,       COLOR_BLUE,  COLOR_BLUE)
        _make_hover(self.save_report_btn, COLOR_GREEN, COLOR_GREEN)

        # Resize grip — bottom-right corner
        self.resize_grip = tk.Label(
            self.action_bar, text="◢",
            bg=BG_CRUST, fg=BG_SURFACE,
            cursor="size_nw_se", font=("Segoe UI", 7),
        )
        self.resize_grip.pack(side=tk.RIGHT, anchor=tk.SE, padx=3, pady=3)
        self.resize_grip.bind("<Button-1>",   self._start_resize)
        self.resize_grip.bind("<B1-Motion>",  self._on_resize)
        self.resize_grip.bind("<ButtonRelease-1>", self._end_resize)
        self.resize_grip.bind("<Enter>", lambda e: self.resize_grip.config(fg=FG_SUBTEXT))
        self.resize_grip.bind("<Leave>", lambda e: self.resize_grip.config(fg=BG_SURFACE))

    # ── Drag ──────────────────────────────────────────────────────────────────

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")
        self.pref_x = x
        self.pref_y = y
        self.is_manual_positioned = True

    def _end_drag(self, event):
        if self.is_manual_positioned:
            self._save_ui_settings()

    # ── Resize grip ───────────────────────────────────────────────────────────

    def _start_resize(self, event):
        self._rx0 = event.x_root
        self._ry0 = event.y_root
        self._rw0 = self.root.winfo_width()
        self._rh0 = self.root.winfo_height()
        # Keep track of initial coordinates to anchor resizing relative to bottom-right
        self._rx_win = self.root.winfo_x()
        self._ry_win = self.root.winfo_y()

    def _on_resize(self, event):
        dx = event.x_root - self._rx0
        dy = event.y_root - self._ry0
        nw = max(MIN_WIDTH,  min(MAX_WIDTH,  self._rw0 + dx))
        nh = max(MIN_HEIGHT, min(MAX_HEIGHT, self._rh0 + dy))
        
        self.is_manual_resized = True
        self.pref_width  = nw
        self.pref_height = nh
        
        if not self.is_manual_positioned:
            # Anchored to bottom-right: offset x and y dynamically by size change
            dw = nw - self._rw0
            dh = nh - self._rh0
            nx = self._rx_win - dw
            ny = self._ry_win - dh
            self.root.geometry(f"{nw}x{nh}+{nx}+{ny}")
        else:
            # Free floating: keep top-left corner fixed
            self.root.geometry(f"{nw}x{nh}")

    def _end_resize(self, event):
        if self.is_manual_resized:
            self._save_ui_settings()

    # ── Size configure callback ───────────────────────────────────────────────

    def _on_configure(self, event):
        # Respond ONLY to root window resize events to avoid reacting to child widget moves
        if event.widget == self.root:
            if hasattr(self, "_compact_lbl") and self._compact_lbl.winfo_manager():
                w = self.root.winfo_width()
                self._compact_lbl.config(wraplength=max(100, w - 28))

    # ── Size modes ────────────────────────────────────────────────────────────

    def set_size_mode(self, mode: str):
        self.size_mode = mode.upper()
        self.is_manual_resized = False
        self.pref_width  = None
        self.pref_height = None
        self.is_manual_positioned = False
        self.pref_x = None
        self.pref_y = None
        self._update_size_buttons()
        self.apply_geometry()
        self._save_ui_settings()

    def _update_size_buttons(self):
        for mode, btn in self.size_buttons.items():
            active = (mode == self.size_mode)
            btn.config(
                fg=COLOR_BLUE if active else FG_SUBTEXT,
                bg=BG_SURFACE if active else BG_CRUST,
            )

    def _get_auto_mode_for_content(self) -> str:
        # During active streaming phases always stay STANDARD (stable)
        if self._last_status.lower() in (
            "listening", "analyzing_screen", "understanding_context",
        ):
            return "STANDARD"
        if not self.full_text:
            return "STANDARD"
        clean_len = len(self._extract_readable_text())
        if clean_len < SHORT_THRESHOLD:
            return "COMPACT"
        if clean_len < NORMAL_THRESHOLD:
            return "STANDARD"
        return "EXPANDED"

    def apply_geometry(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        effective = self.size_mode
        if effective == "AUTO":
            effective = self._get_auto_mode_for_content()

        # Pack/unpack heavy widgets based on mode — done ONCE here
        if effective == "COMPACT":
            self._set_compact_layout()
            w = self.pref_width  if self.is_manual_resized else COMPACT_WIDTH
            h = COMPACT_HEIGHT   # Lock compact height to lock visual design
        else:
            self._set_full_layout()
            if effective == "STANDARD":
                w = self.pref_width  if self.is_manual_resized else STANDARD_WIDTH
                h = self.pref_height if self.is_manual_resized else STANDARD_HEIGHT
            else:  # EXPANDED
                w = self.pref_width  if self.is_manual_resized else EXPANDED_WIDTH
                h = self.pref_height if self.is_manual_resized else EXPANDED_HEIGHT

        w = max(MIN_WIDTH,  min(MAX_WIDTH,  w))
        h = max(MIN_HEIGHT, min(MAX_HEIGHT, h))

        if self.is_manual_positioned and self.pref_x is not None and self.pref_y is not None:
            # Preserve user's manually dragged position
            x = self.pref_x
            y = self.pref_y
        else:
            # Anchor to bottom-right of the screen
            x = sw - w - 25
            y = sh - h - 65

        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _is_widget_packed(self, widget) -> bool:
        """Check if widget is packed in parent cavity using pack_info.
        (Avoids ScrolledText winfo_manager quirk where internal scrollbar frame returns 'pack').
        """
        try:
            widget.pack_info()
            return True
        except Exception:
            return False

    def _set_compact_layout(self):
        """Switch to compact layout: hide pipeline + text area, show preview label."""
        if self._is_widget_packed(self.pipeline_frame):
            self.pipeline_frame.pack_forget()
        if self._is_widget_packed(self.pipeline_separator):
            self.pipeline_separator.pack_forget()
        if self._is_widget_packed(self.text_area):
            self.text_area.pack_forget()

        cw = self.pref_width if self.is_manual_resized else COMPACT_WIDTH

        if not hasattr(self, "_compact_lbl"):
            self._compact_lbl = tk.Label(
                self.root,
                bg=BG_MANTLE, fg=FG_SUBTEXT,
                font=("Segoe UI", 9), anchor=tk.W,
                justify=tk.LEFT, padx=12, pady=8,
                wraplength=max(100, cw - 28),
            )
        else:
            self._compact_lbl.config(wraplength=max(100, cw - 28))

        if not self._is_widget_packed(self._compact_lbl):
            # Insert between title bar and action bar
            self._compact_lbl.pack(fill=tk.BOTH, expand=True)

        self._update_compact_label()

    def _update_compact_label(self):
        txt = self._extract_readable_text()
        if not txt:
            txt = "Listening…"
        
        # Filter lines to get the first actual response content
        first_line = "Listening…"
        for line in txt.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            # Skip Command / query headers and separators
            if "Command:" in line_str or line_str.startswith("🔍") or line_str.startswith("─"):
                continue
            # Strip ANSWER/REASON/ACTION tags for clean preview if they exist in the line
            clean_line = line_str
            for tag in ("ANSWER:", "REASON:", "ACTION:"):
                if clean_line.upper().startswith(tag):
                    clean_line = clean_line[len(tag):].strip()
                    break
            if clean_line:
                first_line = clean_line
                break
                
        if len(first_line) > 70:
            first_line = first_line[:70] + "…"
        if hasattr(self, "_compact_lbl"):
            self._compact_lbl.config(text=first_line)

    def _set_full_layout(self):
        """Restore full layout: pipeline + text area visible, preview hidden."""
        if hasattr(self, "_compact_lbl") and self._is_widget_packed(self._compact_lbl):
            self._compact_lbl.pack_forget()

        if not self._is_widget_packed(self.pipeline_frame):
            # Re-pack in correct top-down order
            self.pipeline_frame.pack(fill=tk.X, side=tk.TOP)
            self.pipeline_separator.pack(fill=tk.X, side=tk.TOP)

        if not self._is_widget_packed(self.text_area):
            self.text_area.pack(fill=tk.BOTH, expand=True)

    # ── Text rendering ────────────────────────────────────────────────────────

    def _render_text(self):
        """Re-render full_text into the styled text widget."""
        ta = self.text_area

        # Capture scroll position before clearing
        yview_before = ta.yview()
        at_bottom = yview_before[1] >= 0.98

        ta.config(state=tk.NORMAL)
        ta.delete("1.0", tk.END)

        in_code_block = False
        for line in self.full_text.split("\n"):
            # Code fence toggle
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                ta.insert(tk.END, line + "\n", "code_block")
                continue

            stripped = line.strip()
            upper = stripped.upper()

            # Section headers — ANSWER / REASON / ACTION
            if upper.startswith("ANSWER:"):
                body = line[line.upper().index("ANSWER:") + 7:].strip()
                ta.insert(tk.END, "ANSWER\n", "header_answer")
                if body:
                    self._insert_inline(body + "\n")
                continue
            if upper.startswith("REASON:"):
                body = line[line.upper().index("REASON:") + 7:].strip()
                ta.insert(tk.END, "REASON\n", "header_reason")
                if body:
                    self._insert_inline(body + "\n")
                continue
            if upper.startswith("ACTION:"):
                body = line[line.upper().index("ACTION:") + 7:].strip()
                ta.insert(tk.END, "ACTION\n", "header_action")
                if body:
                    self._insert_inline(body + "\n")
                continue

            # Markdown headers
            if stripped.startswith("#"):
                ta.insert(tk.END, stripped.lstrip("#").strip() + "\n", "header")
                continue

            # Bullet points
            if stripped.startswith("- ") or stripped.startswith("* "):
                ta.insert(tk.END, "  •  ", "bullet_symbol")
                self._insert_inline(stripped[2:] + "\n")
                continue

            # Regular line
            self._insert_inline(line + "\n")

        ta.config(state=tk.DISABLED)

        if at_bottom:
            ta.see(tk.END)

        # Compact mode: update preview label
        if self.size_mode == "COMPACT" or (
            self.size_mode == "AUTO" and
            self._get_auto_mode_for_content() == "COMPACT"
        ):
            self._update_compact_label()

    def _insert_inline(self, text: str):
        """Parse **bold** and `inline_code` within a text segment."""
        import re
        parts = re.split(r"(\*\*.*?\*\*|`[^`]+`)", text)
        for part in parts:
            if part.startswith("**") and part.endswith("**") and len(part) > 4:
                self.text_area.insert(tk.END, part[2:-2], "bold")
            elif part.startswith("`") and part.endswith("`") and len(part) > 2:
                self.text_area.insert(tk.END, part[1:-1], "inline_code")
            else:
                self.text_area.insert(tk.END, part, "normal")

    # ── Queue processor ───────────────────────────────────────────────────────

    def _process_queue(self):
        try:
            while True:
                task = self.queue.get_nowait()
                self._handle_task(task)
                self.queue.task_done()
        except queue.Empty:
            pass
        if self.root:
            self.root.after(40, self._process_queue)

    def _handle_task(self, task):
        action = task[0]
        if action == "show":
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
        elif action == "hide":
            if hasattr(self, "byok_frame") and self.byok_frame.winfo_manager():
                import os as _os; _os._exit(0)
            self.root.withdraw()
        elif action == "clear":
            self.full_text = ""
            self.text_area.config(state=tk.NORMAL)
            self.text_area.delete("1.0", tk.END)
            self.text_area.config(state=tk.DISABLED)
        elif action == "append":
            self.full_text += task[1]
            self._render_text()
        elif action == "status":
            self._update_status_ui(task[1])
        elif action == "show_key_input":
            self._show_byok(task[1])

    # ── Status / pipeline ─────────────────────────────────────────────────────

    def _update_status_ui(self, status: str):
        self._last_status = status
        key = status.lower()
        label = _STATUS_LABELS.get(key, "● IDLE")
        color = _STATUS_COLORS.get(key, COLOR_GREEN)
        self.status_indicator.config(text=label, fg=color)
        self._update_pipeline(key)

        # Trigger geometry reflow only at terminal/idle states and query start states
        # (completed/error/cancelled/idle/listening/analyzing_screen/understanding_context)
        # or when a non-AUTO mode is active (user chose explicit mode)
        if key in (
            "completed", "error", "cancelled", "idle", 
            "listening", "analyzing_screen", "understanding_context"
        ) or self.size_mode != "AUTO":
            self.apply_geometry()

    def _update_pipeline(self, status_key: str):
        """Update pipeline step labels to reflect PENDING/ACTIVE/COMPLETED/ERROR/CANCELLED."""
        is_error     = (status_key == "error")
        is_cancelled = (status_key == "cancelled")
        is_idle      = (status_key == "idle")

        # Advance the tracked active index only for forward-moving states
        new_idx = _STAGE_INDEX.get(status_key, -1)
        if new_idx >= 0:
            self._current_active_idx = new_idx

        active_idx = self._current_active_idx

        # ── Reset all to idle when returning to IDLE ─────────────────────────
        if is_idle:
            self._current_active_idx = -1
            for lbl in self.step_labels:
                lbl.config(fg=FG_SUBTEXT, font=("Segoe UI", 7, "bold"))
            for arrow in self.step_connectors:
                arrow.config(fg=BG_SURFACE)
            return

        for idx, lbl in enumerate(self.step_labels):
            if is_error:
                # ERROR: freeze steps — completed stay green, failing step turns red,
                # subsequent steps go back to subdued
                if idx < active_idx:
                    lbl.config(fg=COLOR_GREEN,  font=("Segoe UI", 7, "bold"))
                elif idx == active_idx:
                    lbl.config(fg=COLOR_RED,    font=("Segoe UI", 7, "bold"))
                else:
                    lbl.config(fg=FG_SUBTEXT,   font=("Segoe UI", 7, "bold"))

            elif is_cancelled:
                # CANCELLED: freeze steps — completed stay dimmed amber,
                # active step and beyond turn muted yellow-grey
                if idx <= active_idx:
                    lbl.config(fg=COLOR_YELLOW, font=("Segoe UI", 7, "bold"))
                else:
                    lbl.config(fg=FG_SUBTEXT,   font=("Segoe UI", 7, "bold"))

            elif status_key == "completed":
                # Final COMPLETED status: all steps completed green, standard weight (not active 8pt)
                lbl.config(fg=COLOR_GREEN, font=("Segoe UI", 7, "bold"))

            elif idx < active_idx:
                # COMPLETED prior steps: green, normal weight
                lbl.config(fg=COLOR_GREEN,  font=("Segoe UI", 7, "bold"))

            elif idx == active_idx:
                # ACTIVE step: brighter color + heavier 8pt label (ACTIVE emphasis)
                if idx == 2:  # Problems — yellow accent
                    lbl.config(fg=COLOR_YELLOW, font=("Segoe UI", 8, "bold"))
                else:
                    lbl.config(fg=COLOR_BLUE,   font=("Segoe UI", 8, "bold"))

            else:
                # PENDING steps: subdued
                lbl.config(fg=FG_SUBTEXT,   font=("Segoe UI", 7, "bold"))

        # ── Update connector arrows ──────────────────────────────────────────
        for c_idx, arrow in enumerate(self.step_connectors):
            # Arrow between step c_idx and c_idx+1 lights up when step c_idx is done
            if is_error:
                arrow.config(fg=COLOR_GREEN if c_idx < active_idx else BG_SURFACE)
            elif is_cancelled:
                arrow.config(fg=COLOR_YELLOW if c_idx < active_idx else BG_SURFACE)
            elif status_key == "completed":
                arrow.config(fg=COLOR_GREEN)   # all arrows lit on completion
            else:
                arrow.config(fg=COLOR_GREEN if c_idx < active_idx else BG_SURFACE)

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self):
        if self.root:
            self.root.mainloop()

    def show(self):                     self.queue.put(("show",))
    def hide(self):                     self.queue.put(("hide",))
    def clear(self):                    self.queue.put(("clear",))
    def append(self, text: str):        self.queue.put(("append", text))
    def update_status(self, status: str): self.queue.put(("status", status))
    def show_key_input(self, cb):       self.queue.put(("show_key_input", cb))

    def set_callbacks(self, on_read=None, on_save_report=None):
        self._on_read_callback      = on_read
        self._on_save_report_callback = on_save_report

    # ── Text extraction ───────────────────────────────────────────────────────

    def _extract_readable_text(self) -> str:
        import re
        t = self.full_text
        t = re.sub(r"```[\s\S]*?```", "", t)
        t = re.sub(r"`([^`]*)`",  r"\1", t)
        t = re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", t)
        t = re.sub(r"^#+\s*",   "", t, flags=re.MULTILINE)
        t = re.sub(r"^[-─]{3,}$", "", t, flags=re.MULTILINE)
        t = re.sub(r"\n{3,}", "\n\n", t)
        return t.strip()

    # ── Button handlers ───────────────────────────────────────────────────────

    def _on_read_clicked(self):
        if not self.full_text.strip():
            return
        readable = self._extract_readable_text()
        if self._on_read_callback:
            import threading
            threading.Thread(target=self._on_read_callback,
                             args=(readable,), daemon=True).start()

    def _on_save_report_clicked(self):
        if not self.full_text.strip():
            return
        if self._on_save_report_callback:
            self._on_save_report_callback(self.full_text)

    # ── BYOK setup ────────────────────────────────────────────────────────────

    def _show_byok(self, callback):
        self.on_save_callback = callback

        # Hide all normal content
        for w in (self.text_area, self.pipeline_frame,
                  self.pipeline_separator):
            if w.winfo_manager():
                w.pack_forget()
        if hasattr(self, "_compact_lbl") and self._compact_lbl.winfo_manager():
            self._compact_lbl.pack_forget()
        if self.action_bar.winfo_manager():
            self.action_bar.pack_forget()
        if self.action_bar_separator.winfo_manager():
            self.action_bar_separator.pack_forget()

        self._create_byok_ui()
        self.byok_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w, h = 400, 250
        self.root.geometry(f"{w}x{h}+{sw - w - 25}+{sh - h - 65}")
        self.key_entry.delete(0, tk.END)
        self.key_entry.focus_set()

        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)

    def _create_byok_ui(self):
        if hasattr(self, "byok_frame") and self.byok_frame.winfo_exists():
            return

        self.byok_frame = tk.Frame(self.root, bg=BG_BASE)

        tk.Label(self.byok_frame, text="BlackBox Pro  —  Setup",
                 bg=BG_BASE, fg=FG_TEXT,
                 font=("Segoe UI", 11, "bold")).pack(pady=(20, 4))

        tk.Label(self.byok_frame,
                 text="Enter your Google AI Studio API key:",
                 bg=BG_BASE, fg=FG_SUBTEXT,
                 font=("Segoe UI", 9)).pack(pady=(0, 12))

        self.key_entry = tk.Entry(
            self.byok_frame,
            bg=BG_MANTLE, fg=FG_TEXT,
            insertbackground=FG_TEXT,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BG_SURFACE,
            highlightcolor=COLOR_BLUE,
        )
        self.key_entry.pack(fill=tk.X, padx=28, pady=4)
        self.key_entry.bind("<Return>", lambda e: self._on_save_clicked())

        self.byok_status = tk.Label(
            self.byok_frame,
            text="aistudio.google.com  ↗",
            bg=BG_BASE, fg=FG_SUBTEXT,
            font=("Segoe UI", 8),
            cursor="hand2",
        )
        self.byok_status.pack(pady=6)

        import webbrowser
        self.byok_status.bind("<Button-1>",
            lambda e: webbrowser.open("https://aistudio.google.com"))
        self.byok_status.bind("<Enter>",
            lambda e: self.byok_status.config(fg=COLOR_BLUE))
        self.byok_status.bind("<Leave>",
            lambda e: self.byok_status.config(fg=FG_SUBTEXT))

        self.save_button = tk.Button(
            self.byok_frame, text="Save & Activate",
            bg=COLOR_BLUE, fg=BG_CRUST,
            activebackground=COLOR_PURPLE, activeforeground=BG_CRUST,
            relief=tk.FLAT, bd=0,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2", padx=22, pady=7,
            command=self._on_save_clicked,
        )
        self.save_button.pack(pady=18)
        self.save_button.bind("<Enter>",
            lambda e: self.save_button.config(bg=COLOR_PURPLE))
        self.save_button.bind("<Leave>",
            lambda e: self.save_button.config(bg=COLOR_BLUE))

    def _on_save_clicked(self):
        key = self.key_entry.get().strip()
        if not key:
            self.byok_status.config(text="⚠  Key cannot be empty.", fg=COLOR_RED)
            return
        if hasattr(self, "on_save_callback") and self.on_save_callback:
            success = self.on_save_callback(key)
            if success:
                self.byok_frame.pack_forget()
                self.apply_geometry()
                self.hide()
            else:
                self.byok_status.config(text="⚠  Failed to save key.", fg=COLOR_RED)

    # Alias kept for test compatibility
    @property
    def status_label(self):
        return getattr(self, "byok_status", None)
