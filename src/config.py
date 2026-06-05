from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: Path, *, override: bool = False, protected_keys: set[str] | None = None) -> None:
    if not path.exists():
        return
    protected = protected_keys or set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_quotes(value.strip())
        if key and key not in protected and (override or key not in os.environ):
            os.environ[key] = value


def load_project_env(root: Path) -> None:
    protected_keys = set(os.environ)
    load_env_file(root / ".env", protected_keys=protected_keys)
    load_env_file(root / ".env.local", override=True, protected_keys=protected_keys)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
