"""Start Claude Pet (double-click: runs without a console window)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pet.app import main

main()
