import pystray
from PIL import Image, ImageDraw
import os
import time
import threading
from plyer import notification

class TrayManager:
    def __init__(self, on_exit_callback, on_restart_callback=None):
        self.on_exit_callback = on_exit_callback
        self.on_restart_callback = on_restart_callback
        self.icon = None
        self._pulse_thread = None
        self._pulsing = False
        self._current_state = 'idle'
        self._setup_tray()

    def _setup_tray(self):
        # Initial image
        image = self._generate_icon('green')
        menu = pystray.Menu(
            pystray.MenuItem("BlackBox Pro: Active", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Show", self._on_show),
            pystray.MenuItem("Hide", self._on_hide),
            pystray.MenuItem("Restart", self._on_restart),
            pystray.MenuItem("Quit", self._on_exit)
        )
        self.icon = pystray.Icon("BlackBoxAI", image, "BlackBox Pro", menu)

    def _generate_icon(self, color, size=(64, 64)):
        """Generate a sleek, vibrant circular icon."""
        image = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Color mapping
        colors = {
            'green': (46, 204, 113),  # Emerald
            'red': (231, 76, 60),    # Alizarin
            'blue': (52, 152, 219),   # Peter River
            'yellow': (241, 196, 15)  # Sun Flower
        }
        
        fill_color = colors.get(color, (127, 140, 141))
        
        # Draw main circle
        margin = 4
        draw.ellipse([margin, margin, size[0]-margin, size[1]-margin], fill=fill_color, outline=(255, 255, 255, 100), width=2)
        
        # Add a subtle gloss effect
        draw.ellipse([size[0]//4, size[1]//8, size[0]//1.5, size[1]//2], fill=(255, 255, 255, 60))
        
        return image

    def _on_show(self, icon, item):
        self.notify("BlackBox Pro", "Assistant is visible and active.")

    def _on_hide(self, icon, item):
        self.notify("BlackBox Pro", "Assistant running in background.")

    def _on_restart(self, icon, item):
        if self.on_restart_callback:
            self.on_restart_callback()

    def _on_exit(self, icon, item):
        self._pulsing = False
        self.icon.stop()
        if self.on_exit_callback:
            self.on_exit_callback()

    def update_state(self, state):
        """Update icon based on state: 'idle', 'listening', 'thinking', 'speaking'"""
        if self._current_state == state and state != 'thinking':
            return
            
        self._current_state = state
        self._pulsing = False # Stop any active pulse
        
        if state == 'thinking':
            self._start_thinking_pulse()
        elif state == 'listening':
            self.icon.icon = self._generate_icon('red')
        elif state == 'speaking':
            self.icon.icon = self._generate_icon('yellow')
        else: # idle
            self.icon.icon = self._generate_icon('green')

    def _start_thinking_pulse(self):
        self._pulsing = True
        if self._pulse_thread and self._pulse_thread.is_alive():
            return
            
        def pulse():
            import time
            blue_icon = self._generate_icon('blue')
            dim_blue = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(dim_blue)
            draw.ellipse([8, 8, 56, 56], fill=(41, 128, 185, 150)) # Dimmer blue
            
            while self._pulsing:
                if not self.icon: break
                self.icon.icon = blue_icon
                time.sleep(0.6)
                if not self._pulsing: break
                self.icon.icon = dim_blue
                time.sleep(0.6)
        
        self._pulse_thread = threading.Thread(target=pulse, daemon=True)
        self._pulse_thread.start()

    def notify(self, title, message):
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Black Box AI",
                timeout=5
            )
        except Exception as e:
            print(f"Warning: Notification failed to display: {e}")


    def run(self):
        # Run pystray in a background thread so the main thread is free for Tkinter
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()

