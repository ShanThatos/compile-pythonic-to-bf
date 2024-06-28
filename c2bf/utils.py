import sys
from pathlib import Path

data_path = ""
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    data_path = str(Path(getattr(sys, "_MEIPASS")).resolve())

def get_data_path(path: str):
    if data_path:
        return str(Path(data_path).joinpath(path))
    return path
