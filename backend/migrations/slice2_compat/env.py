"""Use the regular application engine and transaction configuration."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parents[1] / 'env.py'))
