"""Export the FastAPI OpenAPI schema to a static JSON file."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402

schema = app.openapi()
output_path = Path(__file__).resolve().parent.parent / "openapi.json"
output_path.write_text(json.dumps(schema, indent=2))
print(f"OpenAPI schema written to {output_path}")
