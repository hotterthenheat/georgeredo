"""Entry point for lc.pull_tier_d under `python3 -I` (isolated mode ignores the working directory on sys.path)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lc.pull_tier_d import main
main()
