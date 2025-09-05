import sys
from pathlib import Path

# Support both `python -m novic` (package context) and `python main.py` (script).
if __package__ in (None, ""):
    # We're being executed as a script; ensure parent (src) is on sys.path
    pkg_dir = Path(__file__).resolve().parent  # .../src/novic
    src_dir = pkg_dir.parent  # .../src
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    from novic.app import NovicApplication  # absolute import after path fix
else:
    from .app import NovicApplication  # normal package relative import


def main():
    app = NovicApplication(sys.argv)
    return app.run()

if __name__ == "__main__":  # allows `python main.py` when invoked directly
    import sys as _sys
    _sys.exit(main())