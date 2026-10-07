import sys
sys.path.insert(0, '/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests')
from network_guard import install
install()
import os, time
os.write(1, b"stdout-before-timeout\xff\n")
os.write(2, b"stderr-before-timeout\xfe\n")
time.sleep(60)
