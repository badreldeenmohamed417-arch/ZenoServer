from __future__ import annotations
from pathlib import Path
import json

def load_dataset(path: str|Path="tests/evaluation_dataset.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))
