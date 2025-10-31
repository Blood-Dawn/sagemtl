# Kheiven D'Haiti — sagemtl.cli
from __future__ import annotations
import argparse
from importlib.metadata import version

def main() -> None:
    ap = argparse.ArgumentParser(prog="sagemtl", description="SageMTL toolchain")
    ap.add_argument("--version", action="store_true", help="show version and exit")
    args = ap.parse_args()
    if args.version:
        print("sagemtl", version("sagemtl"))
        return
    ap.print_help()
