import sys
import os
import time
import threading

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.hal.overlay import OverlayWindow

def test_byok_ui_programmatic():
    print("=== Programmatic BYOK UI Test ===")
    overlay = OverlayWindow()
    
    # Wait for tkinter loop to start
    time.sleep(1)
    
    key_saved = threading.Event()
    saved_key_val = None
    
    def on_save(k):
        nonlocal saved_key_val
        saved_key_val = k
        key_saved.set()
        return True
        
    overlay.show_key_input(on_save)
    time.sleep(1) # wait for queue to process and widgets to render
    
    # Access and simulate tkinter interaction safely inside the tkinter thread
    def simulate_user_input():
        try:
            print("Simulating user entering API key...")
            overlay.key_entry.insert(0, "AIzaSyTestKey12345")
            print("Simulating user clicking 'Save' button...")
            overlay.save_button.invoke()
        except Exception as e:
            print(f"Error during simulation: {e}")
            
    overlay.root.after(100, simulate_user_input)
    
    # Wait for the save callback to trigger
    success = key_saved.wait(timeout=5)
    if success and saved_key_val == "AIzaSyTestKey12345":
        print("PASS: BYOK UI successfully processed input and triggered callback programmatically!")
    else:
        print("FAIL: BYOK UI failed or timed out.")
        
    # Clean up tkinter
    overlay.root.quit()
    print("=== Test Complete ===")

if __name__ == "__main__":
    test_byok_ui_programmatic()
