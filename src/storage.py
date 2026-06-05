from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_scripts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def load_versions(path: Path) -> list[dict[str, Any]]:
    return load_scripts(path)


def load_campaign_results(path: Path) -> list[dict[str, Any]]:
    return load_scripts(path)


def save_script(script: dict[str, Any], path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = dict(script)
    record.setdefault("id", f"script-{uuid.uuid4().hex[:10]}")
    record.setdefault("created_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def save_script_version(version: dict[str, Any], path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = dict(version)
    record.setdefault("id", f"version-{uuid.uuid4().hex[:10]}")
    record.setdefault("created_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    record.setdefault("version_no", _next_version_no(record.get("script_id", ""), load_versions(path)))
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def save_campaign_result(result: dict[str, Any], path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = dict(result)
    record.setdefault("id", f"campaign-{uuid.uuid4().hex[:10]}")
    record.setdefault("created_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _next_version_no(script_id: str, versions: list[dict[str, Any]]) -> int:
    existing = [int(item.get("version_no", 0)) for item in versions if item.get("script_id") == script_id]
    return max(existing, default=0) + 1
