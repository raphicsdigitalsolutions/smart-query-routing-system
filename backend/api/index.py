"""Vercel ASGI entrypoint for the Smart Query backend.

The application itself lives in ``app/main.py``. Vercel's file-based Python
runtime loads this module, so expose the same FastAPI instance here and make the
backend root importable for the ``app`` package.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

__all__ = ["app"]
