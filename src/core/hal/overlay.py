import tkinter as tk
from tkinter import scrolledtext
import threading
import queue

class OverlayWindow:
    """Thread-safe borderless floating response panel using Tkinter."""
    def __init__(self):
        self.queue = queue.Queue()
        self.root = None
        self.text_area = None
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        self.root = tk.Tk()
        self.root.title("BlackBox AI Response Panel")
        
        # Borderless window and stay on top
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        
        # Sleek dark styling (Catppuccin Mocha theme elements)
        self.root.configure(bg="#1e1e2e")
        
        # 1px vibrant blue border
        self.root.config(highlightbackground="#89b4fa", highlightcolor="#89b4fa", highlightthickness=1)
        
        # Geometry: 460x320 at bottom-right of screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w, h = 460, 320
        x = screen_w - w - 25
        y = screen_h - h - 65
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        # Custom title bar for dragging
        self.title_bar = tk.Frame(self.root, bg="#11111b", height=32)
        self.title_bar.pack(fill=tk.X, side=tk.TOP)
        self.title_bar.pack_propagate(False)
        
        # Title text
        self.title_label = tk.Label(
            self.title_bar, 
            text="✨ BlackBox AI - Response Panel", 
            bg="#11111b", 
            fg="#cdd6f4", 
            font=("Segoe UI", 9, "bold")
        )
        self.title_label.pack(side=tk.LEFT, padx=10)
        
        # Close button
        self.close_button = tk.Button(
            self.title_bar, 
            text=" ✕ ", 
            bg="#11111b", 
            fg="#f38ba8", 
            activebackground="#f38ba8", 
            activeforeground="#11111b", 
            bd=0, 
            font=("Segoe UI", 10, "bold"), 
            command=self.hide,
            cursor="hand2"
        )
        self.close_button.pack(side=tk.RIGHT, padx=8)
        
        # Drag bindings
        self.title_bar.bind("<Button-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._on_drag)
        self.title_label.bind("<Button-1>", self._start_drag)
        self.title_label.bind("<B1-Motion>", self._on_drag)
        
        # ScrolledText responder pane
        self.text_area = scrolledtext.ScrolledText(
            self.root, 
            wrap=tk.WORD, 
            bg="#181825", 
            fg="#cdd6f4", 
            insertbackground="#cdd6f4",
            font=("Segoe UI", 10), 
            bd=0, 
            highlightthickness=0
        )
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.text_area.config(state=tk.DISABLED)
        
        # Process task queue
        self._process_queue()
        
        # Hide initially
        self.root.withdraw()
        
        self.root.mainloop()

    def _start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def _on_drag(self, event):
        x = self.root.winfo_x() + (event.x - self.drag_x)
        y = self.root.winfo_y() + (event.y - self.drag_y)
        self.root.geometry(f"+{x}+{y}")

    def _process_queue(self):
        try:
            while True:
                task = self.queue.get_nowait()
                action = task[0]
                if action == "show_key_input":
                    callback = task[1]
                    self.on_save_callback = callback
                    
                    self.text_area.pack_forget()
                    self._create_byok_ui()
                    self.byok_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                    
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
                    self.text_area.config(state=tk.NORMAL)
                    self.text_area.delete("1.0", tk.END)
                    self.text_area.config(state=tk.DISABLED)
                elif action == "append":
                    text = task[1]
                    self.text_area.config(state=tk.NORMAL)
                    self.text_area.insert(tk.END, text)
                    self.text_area.see(tk.END)
                    self.text_area.config(state=tk.DISABLED)
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

    def _create_byok_ui(self):
        if hasattr(self, 'byok_frame') and self.byok_frame:
            return
            
        self.byok_frame = tk.Frame(self.root, bg="#1e1e2e")
        
        prompt = tk.Label(
            self.byok_frame,
            text="Google AI Studio Gemini API Key",
            bg="#1e1e2e",
            fg="#89b4fa",
            font=("Segoe UI", 11, "bold")
        )
        prompt.pack(pady=(15, 5))
        
        subtitle = tk.Label(
            self.byok_frame,
            text="Please enter your key to activate BlackBox Pro:",
            bg="#1e1e2e",
            fg="#cdd6f4",
            font=("Segoe UI", 9)
        )
        subtitle.pack(pady=(0, 10))
        
        self.key_entry = tk.Entry(
            self.byok_frame,
            bg="#181825",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#45475a",
            highlightcolor="#89b4fa"
        )
        self.key_entry.pack(fill=tk.X, padx=25, pady=5)
        
        self.status_label = tk.Label(
            self.byok_frame,
            text="Get a free key from: https://aistudio.google.com",
            bg="#1e1e2e",
            fg="#a6adc8",
            font=("Segoe UI", 8, "italic")
        )
        self.status_label.pack(pady=5, padx=25)
        
        self.save_button = tk.Button(
            self.byok_frame,
            text="Save & Activate",
            bg="#89b4fa",
            fg="#11111b",
            activebackground="#b4befe",
            activeforeground="#11111b",
            relief=tk.FLAT,
            font=("Segoe UI", 10, "bold"),
            command=self._on_save_clicked,
            cursor="hand2",
            bd=0,
            padx=20,
            pady=6
        )
        self.save_button.pack(pady=15)

    def _on_save_clicked(self):
        key = self.key_entry.get().strip()
        if not key:
            self.status_label.config(text="⚠️ Key cannot be empty!", fg="#f38ba8")
            return
            
        if hasattr(self, 'on_save_callback') and self.on_save_callback:
            success = self.on_save_callback(key)
            if success:
                self.byok_frame.pack_forget()
                self.text_area.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
                self.hide()
            else:
                self.status_label.config(text="⚠️ Failed to save key.", fg="#f38ba8")

