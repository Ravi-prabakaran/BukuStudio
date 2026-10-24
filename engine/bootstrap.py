"""Make sure the print libraries are installed, in a virtual environment inside
the plugin folder, and print the Python to run print scripts with.

usage: python3 engine/bootstrap.py   ->  prints the path to the venv's python
"""
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / ".venv"
REQS = ROOT / "engine" / "requirements.txt"
MODULES = ("reportlab", "pypdf", "PIL", "pypdfium2", "requests", "svglib", "numpy", "resvg_py")


def python():
    return VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def ready():
    if not python().exists():
        return False
    code = "import " + ", ".join(MODULES)
    return subprocess.run([str(python()), "-c", code], capture_output=True).returncode == 0


def main():
    if not ready():
        print("Installing print libraries (one time)…", file=sys.stderr)
        if not python().exists():
            venv.create(VENV, with_pip=True)
        subprocess.run([str(python()), "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", str(REQS)], check=True)
    print(python())


if __name__ == "__main__":
    main()
