import tkinter as tk
from tkinter import scrolledtext
import threading
import queue

# Catppuccin Mocha Palette
BG_BASE = "#1e1e2e"
BG_MANTLE = "#181825"
BG_CRUST = "#11111b"
BG_SURFACE = "#313244"
FG_TEXT = "#cdd6f4"
FG_SUBTEXT = "#a6adc8"
COLOR_BLUE = "#89b4fa"
COLOR_GREEN = "#a6e3a1"
COLOR_RED = "#f38ba8"
COLOR_YELLOW = "#f9e2af"
COLOR_PINK = "#f5c2e7"
COLOR_ROSEWATER = "#f5e0dc"

class OverlayWindow:
    """Thread-safe borderless floating response panel using Tkinter."""
    def __init__(self):
        self.queue = queue.Queue()
        self.root = None
        self.text_area = None
        # External callbacks — set via set_callbacks() after init
        self._on_read_callback = None
        self._on_save_report_callback = None
        self._initialize_gui()

    def _initialize_gui(self):
        self.root = tk.Tk()
        self.root.title("BlackBox AI Response Panel")
        
        # Borderless window and stay on top
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        
        self.root.configure(bg=BG_BASE)
        
        # 1px vibrant blue border
        self.root.config(highlightbackground=COLOR_BLUE, highlightcolor=COLOR_BLUE, highlightthickness=1)
        
        # Geometry: 480x360 at bottom-right of screen (slightly larger for premium look)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w, h = 480, 360
        x = screen_w - w - 25
        y = screen_h - h - 65
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        # Custom title bar for dragging
        self.title_bar = tk.Frame(self.root, bg=BG_CRUST, height=34)
        self.title_bar.pack(fill=tk.X, side=tk.TOP)
        self.title_bar.pack_propagate(False)
        
        # Title text
        self.title_label = tk.Label(
            self.title_bar, 
            text="✨ BlackBox Pro", 
            bg=BG_CRUST, 
            fg=FG_TEXT, 
            font=("Segoe UI", 9, "bold")
        )
        self.title_label.pack(side=tk.LEFT, padx=12)
        
        # Close button with hover animation
        self.close_button = tk.Button(
            self.title_bar, 
            text=" ✕ ", 
            bg=BG_CRUST, 
            fg=COLOR_RED, 
            activebackground=COLOR_RED, 
            activeforeground=BG_CRUST, 
            bd=0, 
            font=("Segoe UI", 10, "bold"), 
            command=self.hide,
            cursor="hand2"
        )
        self.close_button.pack(side=tk.RIGHT, padx=8)
        
        def on_close_enter(e):
            self.close_button.config(bg=COLOR_RED, fg=BG_CRUST)
        def on_close_leave(e):
            self.close_button.config(bg=BG_CRUST, fg=COLOR_RED)
        self.close_button.bind("<Enter>", on_close_enter)
        self.close_button.bind("<Leave>", on_close_leave)
        
        # Status indicator label
        self.status_indicator = tk.Label(
            self.title_bar,
            text="● IDLE",
            bg=BG_CRUST,
            fg=COLOR_GREEN,
            font=("Segoe UI", 9, "bold")
        )
        self.status_indicator.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Thin boundary separator between title bar and content area
        self.separator = tk.Frame(self.root, bg=BG_SURFACE, height=1)
        self.separator.pack(fill=tk.X, side=tk.TOP)
        
        # Drag bindings
        self.title_bar.bind("<Button-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._on_drag)
        self.title_label.bind("<Button-1>", self._start_drag)
        self.title_label.bind("<B1-Motion>", self._on_drag)
        
        # scrolledText responder pane
        self.text_area = scrolledtext.ScrolledText(
            self.root, 
            wrap=tk.WORD, 
            bg=BG_MANTLE, 
            fg=FG_TEXT, 
            insertbackground=FG_TEXT,
            font=("Segoe UI", 10), 
            bd=0, 
            highlightthickness=0
        )
        # Customizing vertical scrollbar colors
        try:
            self.text_area.vbar.config(
                bg=BG_MANTLE, 
                activebackground=BG_SURFACE, 
                troughcolor=BG_CRUST, 
                borderwidth=0, 
                width=10, 
                relief=tk.FLAT
            )
        except Exception:
            pass
            
        # Configure tags for markdown rendering
        self.text_area.tag_config("normal", font=("Segoe UI", 10), foreground=FG_TEXT)
        self.text_area.tag_config("bold", font=("Segoe UI", 10, "bold"), foreground=COLOR_PINK)
        self.text_area.tag_config("header", font=("Segoe UI", 11, "bold"), foreground=COLOR_BLUE)
        self.text_area.tag_config("code_block", font=("Consolas", 9), foreground=COLOR_GREEN, background=BG_CRUST)
        self.text_area.tag_config("inline_code", font=("Consolas", 9, "bold"), foreground=COLOR_ROSEWATER, background=BG_SURFACE)
        self.text_area.tag_config("bullet_symbol", font=("Segoe UI", 10, "bold"), foreground=COLOR_YELLOW)
        
        # Initialize text buffer
        self.full_text = ""

        # ── Bottom action button bar ──────────────────────────────────────────
        # Pack this first so it reserves its space at the bottom of the window
        self.action_bar = tk.Frame(self.root, bg=BG_CRUST, height=42)
        self.action_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.action_bar.pack_propagate(False)

        # Thin separator above the button bar
        self.action_bar_separator = tk.Frame(self.root, bg=BG_SURFACE, height=1)
        self.action_bar_separator.pack(fill=tk.X, side=tk.BOTTOM)

        self.read_btn = tk.Button(
            self.action_bar,
            text="🔊  Read Summary",
            bg=BG_SURFACE,
            fg=COLOR_BLUE,
            activebackground=COLOR_BLUE,
            activeforeground=BG_CRUST,
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            bd=0,
            padx=14,
            pady=6,
            command=self._on_read_clicked
        )
        self.read_btn.pack(side=tk.LEFT, padx=(10, 4), pady=6)

        self.save_report_btn = tk.Button(
            self.action_bar,
            text="💾  Save Report",
            bg=BG_SURFACE,
            fg=COLOR_GREEN,
            activebackground=COLOR_GREEN,
            activeforeground=BG_CRUST,
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            bd=0,
            padx=14,
            pady=6,
            command=self._on_save_report_clicked
        )
        self.save_report_btn.pack(side=tk.LEFT, padx=4, pady=6)

        # Hover effects for action buttons
        def _make_hover(btn, normal_fg, hover_bg, hover_fg):
            btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg, fg=hover_fg))
            btn.bind("<Leave>", lambda e: btn.config(bg=BG_SURFACE, fg=normal_fg))

        _make_hover(self.read_btn, COLOR_BLUE, COLOR_BLUE, BG_CRUST)
        _make_hover(self.save_report_btn, COLOR_GREEN, COLOR_GREEN, BG_CRUST)
        # ─────────────────────────────────────────────────────────────────────
        
        # Process task queue
        self._process_queue()
        
        # Hide initially
        self.root.withdraw()

    def run(self):
        """Starts the Tkinter main loop on the main thread."""
        if self.root:
            self.root.mainloop()

    def _start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def _on_drag(self, event):
        x = self.root.winfo_x() + (event.x - self.drag_x)
        y = self.root.winfo_y() + (event.y - self.drag_y)
        self.root.geometry(f"+{x}+{y}")

    def _render_text(self):
        """Parses self.full_text and renders it with rich styling (tags)."""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete("1.0", tk.END)
        
        lines = self.full_text.split("\n")
        in_code_block = False
        
        for i, line in enumerate(lines):
            # Check for code block boundary
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
                
            if in_code_block:
                self.text_area.insert(tk.END, line + "\n", "code_block")
                continue
                
            # Parse line-level headers
            if line.strip().startswith("#"):
                header_text = line.lstrip("#").strip()
                self.text_area.insert(tk.END, header_text + "\n", "header")
                continue
                
            # Parse line-level bullet points
            if line.strip().startswith("- ") or line.strip().startswith("* "):
                bullet_symbol = "  •  "
                content = line.strip()[2:]
                self.text_area.insert(tk.END, bullet_symbol, "bullet_symbol")
                self._insert_formatted_inline(content + "\n")
                continue
                
            # Regular line, parse inline elements (bold, code)
            self._insert_formatted_inline(line + "\n")
            
        # Pack the text area to expand into all remaining window space above the bottom bar
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))
        self.text_area.config(state=tk.DISABLED, spacing1=3, spacing2=4, spacing3=3)
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)

    def _insert_formatted_inline(self, text: str):
        """Helper to parse bold (**) and inline code (`) and insert them with proper tags."""
        import re
        # Regex to match bold (**...**) or inline code (`...`)
        pattern = re.compile(r"(\*\*.*?\*\*|`.*?`)")
        parts = pattern.split(text)
        
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                content = part[2:-2]
                self.text_area.insert(tk.END, content, "bold")
            elif part.startswith("`") and part.endswith("`"):
                content = part[1:-1]
                self.text_area.insert(tk.END, content, "inline_code")
            else:
                self.text_area.insert(tk.END, part, "normal")

    def _process_queue(self):
        try:
            while True:
                task = self.queue.get_nowait()
                action = task[0]
                if action == "show_key_input":
                    callback = task[1]
                    self.on_save_callback = callback
                    
                    self.text_area.pack_forget()
                    # Hide action bar and separator during BYOK setup
                    if hasattr(self, 'action_bar'):
                        self.action_bar.pack_forget()
                    if hasattr(self, 'action_bar_separator'):
                        self.action_bar_separator.pack_forget()
                    self._create_byok_ui()
                    self.byok_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
                    
                    self.key_entry.delete(0, tk.END)
                    self.key_entry.focus_set()
                    
                    self.root.deiconify()
                    self.root.lift()
                    self.root.attributes("-topmost", True)
                elif action == "show":
                    self.root.deiconify()
                    self.root.lift()
                    self.root.attributes("-topmost", True)
                elif action == "hide":
                    if hasattr(self, 'byok_frame') and self.byok_frame and self.byok_frame.winfo_manager():
                        import os
                        print(">> Key entry cancelled. Exiting application.")
                        os._exit(0)
                    self.root.withdraw()
                elif action == "clear":
                    self.full_text = ""
                    self.text_area.config(state=tk.NORMAL)
                    self.text_area.delete("1.0", tk.END)
                    self.text_area.config(state=tk.DISABLED)
                elif action == "append":
                    text = task[1]
                    self.full_text += text
                    self._render_text()
                elif action == "status":
                    status_text = task[1]
                    self._update_status_ui(status_text)
                    
                self.queue.task_done()
        except queue.Empty:
            pass
        
        if self.root:
            self.root.after(40, self._process_queue)

    def show(self):
        self.queue.put(("show",))

    def hide(self):
        self.queue.put(("hide",))

    def clear(self):
        self.queue.put(("clear",))

    def append(self, text: str):
        self.queue.put(("append", text))

    def show_key_input(self, on_save_callback):
        self.queue.put(("show_key_input", on_save_callback))

    def update_status(self, status: str):
        self.queue.put(("status", status))

    def set_callbacks(self, on_read=None, on_save_report=None):
        """Register external callbacks for the action buttons.

        Args:
            on_read:        Called with (str) when the Read Summary button is clicked.
                            The string is the cleaned, speakable text (no code blocks).
            on_save_report: Called with (str) when the Save Report button is clicked.
                            The string is the full markdown text.
        """
        self._on_read_callback = on_read
        self._on_save_report_callback = on_save_report

    # ──────────────────────────── Action Button Handlers ──────────────────────

    def _extract_readable_text(self) -> str:
        """Strip code blocks and markdown symbols to produce clean speakable text."""
        import re
        text = self.full_text
        # Remove fenced code blocks entirely — not useful for speech
        text = re.sub(r"```[\s\S]*?```", "", text)
        # Remove inline code backticks
        text = re.sub(r"`([^`]*)`", r"\1", text)
        # Remove markdown bold/italic markers
        text = re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", text)
        # Remove markdown header markers
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        # Remove horizontal rules
        text = re.sub(r"^[-─]+$", "", text, flags=re.MULTILINE)
        # Collapse excess blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _on_read_clicked(self):
        """Triggered by the Read Summary button — fires the registered callback."""
        if not self.full_text.strip():
            return
        readable = self._extract_readable_text()
        if self._on_read_callback:
            import threading
            threading.Thread(
                target=self._on_read_callback,
                args=(readable,),
                daemon=True
            ).start()

    def _on_save_report_clicked(self):
        """Triggered by the Save Report button — fires the registered callback."""
        if not self.full_text.strip():
            return
        if self._on_save_report_callback:
            self._on_save_report_callback(self.full_text)

    def _update_status_ui(self, status: str):
        status = status.lower()
        if status == "listening":
            self.status_indicator.config(text="● LISTENING", fg=COLOR_RED)
        elif status == "thinking":
            self.status_indicator.config(text="● THINKING", fg=COLOR_BLUE)
        elif status == "speaking":
            self.status_indicator.config(text="● SPEAKING", fg=COLOR_YELLOW)
        else:
            self.status_indicator.config(text="● IDLE", fg=COLOR_GREEN)

    def _create_byok_ui(self):
        if hasattr(self, 'byok_frame') and self.byok_frame:
            return
            
        self.byok_frame = tk.Frame(self.root, bg=BG_BASE)
        
        prompt = tk.Label(
            self.byok_frame,
            text="✨ BlackBox Pro - Setup",
            bg=BG_BASE,
            fg=COLOR_BLUE,
            font=("Segoe UI", 12, "bold")
        )
        prompt.pack(pady=(20, 5))
        
        subtitle = tk.Label(
            self.byok_frame,
            text="Please enter your Google AI Studio Gemini API Key:",
            bg=BG_BASE,
            fg=FG_TEXT,
            font=("Segoe UI", 9)
        )
        subtitle.pack(pady=(0, 15))
        
        self.key_entry = tk.Entry(
            self.byok_frame,
            bg=BG_MANTLE,
            fg=FG_TEXT,
            insertbackground=FG_TEXT,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BG_SURFACE,
            highlightcolor=COLOR_BLUE
        )
        self.key_entry.pack(fill=tk.X, padx=30, pady=5)
        
        self.status_label = tk.Label(
            self.byok_frame,
            text="Get a free key from: https://aistudio.google.com",
            bg=BG_BASE,
            fg=FG_SUBTEXT,
            font=("Segoe UI", 8, "italic")
        )
        self.status_label.pack(pady=8, padx=30)
        
        # Link bindings to make the text actual clickable URL
        import webbrowser
        self.status_label.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com"))
        self.status_label.bind("<Enter>", lambda e: self.status_label.config(font=("Segoe UI", 8, "italic", "underline"), cursor="hand2"))
        self.status_label.bind("<Leave>", lambda e: self.status_label.config(font=("Segoe UI", 8, "italic"), cursor="arrow"))
        
        self.save_button = tk.Button(
            self.byok_frame,
            text="Save & Activate",
            bg=COLOR_BLUE,
            fg=BG_CRUST,
            activebackground=COLOR_PINK,
            activeforeground=BG_CRUST,
            relief=tk.FLAT,
            font=("Segoe UI", 10, "bold"),
            command=self._on_save_clicked,
            cursor="hand2",
            bd=0,
            padx=24,
            pady=8
        )
        self.save_button.pack(pady=20)
        
        # Hover effect for Save button
        def on_btn_enter(e):
            self.save_button.config(bg=COLOR_PINK)
        def on_btn_leave(e):
            self.save_button.config(bg=COLOR_BLUE)
        self.save_button.bind("<Enter>", on_btn_enter)
        self.save_button.bind("<Leave>", on_btn_leave)

    def _on_save_clicked(self):
        key = self.key_entry.get().strip()
        if not key:
            self.status_label.config(text="⚠️ Key cannot be empty!", fg=COLOR_RED)
            return
            
        if hasattr(self, 'on_save_callback') and self.on_save_callback:
            success = self.on_save_callback(key)
            if success:
                self.byok_frame.pack_forget()
                # Restore widgets in correct order (bottom-first, then fill)
                if hasattr(self, 'action_bar'):
                    self.action_bar.pack(fill=tk.X, side=tk.BOTTOM)
                if hasattr(self, 'action_bar_separator'):
                    self.action_bar_separator.pack(fill=tk.X, side=tk.BOTTOM)
                self.text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))
                self.hide()
            else:
                self.status_label.config(text="⚠️ Failed to save key.", fg=COLOR_RED)
