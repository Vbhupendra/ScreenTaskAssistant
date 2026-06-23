import sys
import os

# Add root to path
sys.path.append(os.getcwd())

print("Testing Black Box Optimizations...")

try:
    import src.config
    print("[OK] src.config imported")
    
    import src.core.host_agent.senses.audio.wake_word
    print("[OK] wake_word imported")
    
    import src.core.host_agent.senses.audio.listener
    print("[OK] listener imported (Optimized)")
    
    import src.core.host_agent.senses.vision.capture
    print("[OK] capture imported")
    
    import src.core.host_agent.actions.speech.speaker
    print("[OK] speaker imported (Threaded)")
    
    import src.core.reasoning.llm
    print("[OK] reasoning.llm imported (Modular)")
    
    print("\noptimization verification successful!")

except ImportError as e:
    print(f"\n[FAIL] Import Failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n[FAIL] Error: {e}")
    sys.exit(1)
