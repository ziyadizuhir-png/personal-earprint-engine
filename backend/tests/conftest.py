import sys
from pathlib import Path


backend_root = Path(__file__).resolve().parents[1]
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(project_root))
