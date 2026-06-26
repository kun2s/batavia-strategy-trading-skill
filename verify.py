#!/usr/bin/env python3
"""Run the portable Batavia acceptance checks available without CMC history."""
from pathlib import Path
import importlib.util
import py_compile
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent


def run(label, command):
    print(f"\n== {label} ==", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def require_dependencies():
    missing = [
        package for package in ("jsonschema",)
        if importlib.util.find_spec(package) is None
    ]
    if missing:
        names = ", ".join(missing)
        print("\n== dependency check ==", flush=True)
        print(f"Missing required package: {names}")
        print("Install review dependencies with: pip install -r requirements.txt")
        raise SystemExit(2)


def main():
    require_dependencies()
    run("unit tests", [sys.executable, "-m", "unittest", "discover", "-v"])
    run("strategy demo", [sys.executable, "demo.py"])
    run("synthetic regimes", [sys.executable, "backtest/synthetic.py"])
    print("\n== syntax check ==", flush=True)
    with tempfile.TemporaryDirectory(prefix="batavia-compile-") as tmp:
        cache = Path(tmp)
        for path in sorted(ROOT.rglob("*.py")):
            if ".git" not in path.parts:
                relative = path.relative_to(ROOT)
                compiled = cache / relative.with_suffix(".pyc")
                compiled.parent.mkdir(parents=True, exist_ok=True)
                py_compile.compile(str(path), cfile=str(compiled), doraise=True)
    print("OK all portable acceptance checks passed")


if __name__ == "__main__":
    main()
