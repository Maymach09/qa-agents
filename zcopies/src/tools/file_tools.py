# src/tools/file_tools.py

from pathlib import Path
from typing import Dict, Any
import json


class FileTools:
    """
    Simple filesystem utilities exposed to agents.
    """

    def __init__(self, base_dir: str = "artifacts"):
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write_markdown(self, relative_path: str, content: str) -> Dict[str, Any]:
        file_path = self.base_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(content, encoding="utf-8")

        return {
            "action": "write_markdown",
            "path": str(file_path),
            "bytes_written": len(content.encode("utf-8"))
        }

    def write_json(self, relative_path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.base_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8"
        )

        return {
            "action": "write_json",
            "path": str(file_path)
        }

    def read_file(self, relative_path: str) -> Dict[str, Any]:
        file_path = self.base_path / relative_path

        return {
            "action": "read_file",
            "path": str(file_path),
            "content": file_path.read_text(encoding="utf-8")
        }