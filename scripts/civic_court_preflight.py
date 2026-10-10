import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_arena as B
import civic_court_geometry as C
C.apply(B)
