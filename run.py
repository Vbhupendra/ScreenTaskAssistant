import os
import sys

# Ensure the package environment is aligned for both source run and compiled EXE
if hasattr(sys, '_MEIPASS'):
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)
else:
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

from src.main import BlackBoxAgent

if __name__ == "__main__":
    agent = BlackBoxAgent()
    agent.start()
