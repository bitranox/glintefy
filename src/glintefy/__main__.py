"""Module entry point for python -m execution.

Purpose
-------
Provide the ``python -m glintefy`` path mandated by the
project's packaging guidelines. This delegates to the CLI main function
ensuring consistent behavior between module execution and console scripts.

System Role
-----------
Lives in the adapters layer. It bridges CPython's module execution entry
point to the shared CLI helper defined in cli.py.
"""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
