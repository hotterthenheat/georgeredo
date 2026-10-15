"""Build the contract lifecycle archive (lc.archive) for roots; resumable by month."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lc import archive
for root in sys.argv[1].split(','):
    archive.build(root, log=lambda m: print(time.strftime('%H:%M:%S'), m, flush=True))
