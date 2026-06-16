from __future__ import annotations

import json
from pathlib import Path

from .model import Workspace


def load_workspace(path: str | Path) -> Workspace:
    with Path(path).open("r", encoding="utf-8") as file:
        return Workspace.from_json(json.load(file))


def save_workspace(workspace: Workspace, path: str | Path) -> None:
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(workspace.to_json(), file, indent=2)
        file.write("\n")
