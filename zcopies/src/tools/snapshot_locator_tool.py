import json
from pathlib import Path
from typing import Optional
from langchain_core.tools import tool
import asyncio


@tool
async def find_locator(page_name: str, label: str, role: Optional[str] = None) -> Optional[str]:
    """
    Search the snapshot file for the given page_name and return the locator string for the element
    matching the label (and optionally role).
    """
    # Find the snapshot file for the page
    snapshot_dir = Path("output/snapshots")
    # Try to match file by page_name in filename
    for file in snapshot_dir.glob(f"*{page_name.replace(' ', '_')}*.json"):
        data = json.loads(file.read_text(encoding="utf-8"))
        for action in data.get("actions", []):
            if action["label"].lower() == label.lower() and (role is None or action["role"] == role):
                return action["locator"]
    return None

# Example usage:
# locator = find_locator("Accounts Page", "Home", "link")
# print(locator)  # page.getByRole('link', { name: 'Home' })
