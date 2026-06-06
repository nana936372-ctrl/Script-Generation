from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import quote


TABLE_SUFFIXES = {
    "tasks": "tasks",
    "products": "products",
    "decompositions": "product_decompositions",
    "topics": "topics",
    "scripts": "scripts",
    "versions": "script_versions",
    "script_feedback": "script_feedback",
}

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_SCHEMA_READY = False
_SCHEMA_LOCK = Lock()


def load_tasks(path: Path) -> list[dict[str, Any]]:
    return _load_records("tasks", path)


def load_products(path: Path) -> list[dict[str, Any]]:
    return _load_records("products", path)


def load_decompositions(path: Path) -> list[dict[str, Any]]:
    return _load_records("decompositions", path)


def load_topics(path: Path) -> list[dict[str, Any]]:
    return _load_records("topics", path)


def load_scripts(path: Path) -> list[dict[str, Any]]:
    return _latest_records_by_id(_load_records("scripts", path))


def load_versions(path: Path) -> list[dict[str, Any]]:
    return _load_records("versions", path)


def load_campaign_results(path: Path) -> list[dict[str, Any]]:
    return load_script_feedback(path)


def load_script_feedback(path: Path) -> list[dict[str, Any]]:
    return _load_records("script_feedback", path)


def save_task(task: dict[str, Any], path: Path) -> dict[str, Any]:
    record = _record_with_defaults(task, "task")
    return _save_record("tasks", record, path)


def save_product(product: dict[str, Any], path: Path) -> dict[str, Any]:
    record = _record_with_defaults(product, "product", with_updated_at=True)
    return _save_record("products", record, path)


def save_decomposition(decomposition: dict[str, Any], path: Path) -> dict[str, Any]:
    record = _record_with_defaults(decomposition, "decomposition")
    return _save_record("decompositions", record, path)


def save_topic(topic: dict[str, Any], path: Path) -> dict[str, Any]:
    record = _record_with_defaults(topic, "topic", with_updated_at=True)
    return _save_record("topics", record, path)


def save_script(script: dict[str, Any], path: Path) -> dict[str, Any]:
    record = _record_with_defaults(script, "script", with_updated_at=True)
    record.setdefault("status", _script_status_from_review(record.get("review_status", "待审核")))
    return _save_record("scripts", record, path)


def save_script_version(version: dict[str, Any], path: Path) -> dict[str, Any]:
    record = _record_with_defaults(version, "version")
    record.setdefault("version_no", _next_version_no(record.get("script_id", ""), load_versions(path)))
    return _save_record("versions", record, path)


def save_campaign_result(result: dict[str, Any], path: Path) -> dict[str, Any]:
    record = _record_with_defaults(result, "campaign")
    return _save_record("script_feedback", record, path)


def save_script_feedback(feedback: dict[str, Any], path: Path) -> dict[str, Any]:
    record = _record_with_defaults(feedback, "feedback")
    return _save_record("script_feedback", record, path)


def mark_scripts_exported(scripts: list[dict[str, Any]], path: Path, exported_at: str) -> list[dict[str, Any]]:
    exported: list[dict[str, Any]] = []
    for script in scripts:
        record = dict(script)
        if record.get("status") != "废弃":
            record["status"] = "已导出"
        record["exported_at"] = exported_at
        exported.append(save_script(record, path))
    return exported


def using_supabase_storage() -> bool:
    backend = os.environ.get("STORAGE_BACKEND", "").strip().lower()
    if backend in {"jsonl", "local", "file"}:
        return False
    if backend == "supabase":
        return True
    return bool(_supabase_database_url())


def supabase_configured() -> bool:
    return bool(_supabase_database_url())


def supabase_database_url_preview() -> str:
    url = _supabase_database_url()
    if not url:
        return ""
    return re.sub(r":([^:@/?#]+)@", ":***@", url)


def _load_records(logical_name: str, path: Path) -> list[dict[str, Any]]:
    if using_supabase_storage():
        return _load_supabase_records(logical_name)
    return _load_jsonl_records(path)


def _save_record(logical_name: str, record: dict[str, Any], path: Path) -> dict[str, Any]:
    if using_supabase_storage():
        return _save_supabase_record(logical_name, record)
    _append_jsonl_record(record, path)
    return record


def _load_jsonl_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _latest_records_by_id(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for index, record in enumerate(records):
        record_id = str(record.get("id") or "").strip()
        key = record_id or f"__row_{index}"
        if key in latest:
            order.remove(key)
        order.append(key)
        latest[key] = record
    return [latest[key] for key in order]


def _append_jsonl_record(record: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def _record_with_defaults(record: dict[str, Any], id_prefix: str, *, with_updated_at: bool = False) -> dict[str, Any]:
    saved = dict(record)
    saved.setdefault("id", f"{id_prefix}-{uuid.uuid4().hex[:10]}")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    saved.setdefault("created_at", now)
    if with_updated_at:
        saved["updated_at"] = now
    return saved


def _load_supabase_records(logical_name: str) -> list[dict[str, Any]]:
    psycopg, sql, dict_row, _jsonb = _require_psycopg()
    with _connect_with_retry(
        psycopg.connect,
        _required_supabase_database_url(),
        row_factory=dict_row,
        prepare_threshold=None,
    ) as connection:
        _ensure_supabase_schema(connection, sql)
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT payload FROM {} ORDER BY created_at ASC").format(
                    _qualified_table(sql, logical_name)
                )
            )
            return [_payload_to_dict(row["payload"]) for row in cursor.fetchall()]


def _save_supabase_record(logical_name: str, record: dict[str, Any]) -> dict[str, Any]:
    psycopg, sql, dict_row, jsonb = _require_psycopg()
    with _connect_with_retry(
        psycopg.connect,
        _required_supabase_database_url(),
        row_factory=dict_row,
        prepare_threshold=None,
    ) as connection:
        _ensure_supabase_schema(connection, sql)
        with connection.cursor() as cursor:
            columns = _supabase_columns(logical_name, record, jsonb)
            column_names = list(columns)
            cursor.execute(
                sql.SQL(
                    """
                    INSERT INTO {} ({})
                    VALUES ({})
                    ON CONFLICT (id) DO UPDATE SET
                      {}
                    RETURNING payload
                    """
                ).format(
                    _qualified_table(sql, logical_name),
                    sql.SQL(", ").join(sql.Identifier(column) for column in column_names),
                    sql.SQL(", ").join(sql.Placeholder() for _ in column_names),
                    sql.SQL(", ").join(
                        sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(column), sql.Identifier(column))
                        for column in column_names
                        if column != "id"
                    ),
                ),
                list(columns.values()),
            )
            row = cursor.fetchone()
    return _payload_to_dict(row["payload"]) if row else record


def _ensure_supabase_schema(connection: Any, sql: Any) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        schema_name = _schema_name()
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema_name)))
            for logical_name in TABLE_SUFFIXES:
                cursor.execute(_create_table_sql(sql, logical_name))
                for column_definition in _column_definitions(logical_name):
                    cursor.execute(
                        sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS {}").format(
                            _qualified_table(sql, logical_name),
                            sql.SQL(column_definition),
                        )
                    )
                cursor.execute(
                    sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(
                        _qualified_table(sql, logical_name)
                    )
                )
                cursor.execute(
                    sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (created_at)").format(
                        sql.Identifier(f"{_table_name(logical_name)}_created_at_idx"),
                        _qualified_table(sql, logical_name),
                    )
                )
            cursor.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (script_id)").format(
                    sql.Identifier(f"{_table_name('versions')}_script_id_idx"),
                    _qualified_table(sql, "versions"),
                )
            )
            cursor.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (script_id)").format(
                    sql.Identifier(f"{_table_name('script_feedback')}_script_id_idx"),
                    _qualified_table(sql, "script_feedback"),
                )
            )
            for logical_name in ("decompositions", "topics", "scripts"):
                cursor.execute(
                    sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (task_id)").format(
                        sql.Identifier(f"{_table_name(logical_name)}_task_id_idx"),
                        _qualified_table(sql, logical_name),
                    )
                )
            for logical_name in ("decompositions", "topics", "scripts"):
                cursor.execute(
                    sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (product_id)").format(
                        sql.Identifier(f"{_table_name(logical_name)}_product_id_idx"),
                        _qualified_table(sql, logical_name),
                    )
                )
        _SCHEMA_READY = True


def _create_table_sql(sql: Any, logical_name: str) -> Any:
    return sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
        _qualified_table(sql, logical_name),
        sql.SQL(", ".join(_column_definitions(logical_name))),
    )


def _column_definitions(logical_name: str) -> list[str]:
    columns_by_table = {
        "tasks": [
            "id text PRIMARY KEY",
            "task_name text",
            "business_goal text",
            "platform text",
            "content_type text",
            "target_user text",
            "script_count text",
            "owner text",
            "reviewer text",
            "status text",
            "payload jsonb NOT NULL",
            "created_at timestamptz NOT NULL DEFAULT now()",
            "updated_at timestamptz",
        ],
        "products": [
            "id text PRIMARY KEY",
            "task_id text",
            "product_name text",
            "platform text",
            "payload jsonb NOT NULL",
            "created_at timestamptz NOT NULL DEFAULT now()",
            "updated_at timestamptz",
        ],
        "decompositions": [
            "id text PRIMARY KEY",
            "task_id text",
            "product_id text",
            "payload jsonb NOT NULL",
            "created_at timestamptz NOT NULL DEFAULT now()",
        ],
        "topics": [
            "id text PRIMARY KEY",
            "task_id text",
            "product_id text",
            "decomposition_id text",
            "title text",
            "angle text",
            "difficulty text",
            "selected boolean DEFAULT false",
            "payload jsonb NOT NULL",
            "created_at timestamptz NOT NULL DEFAULT now()",
            "updated_at timestamptz",
        ],
        "scripts": [
            "id text PRIMARY KEY",
            "task_id text",
            "topic_id text",
            "product_id text",
            "title text",
            "product_name text",
            "platform text",
            "generated_at timestamptz",
            "saved_at timestamptz",
            "exported_at timestamptz",
            "status text",
            "review_status text",
            "reviewer text",
            "reject_reason text",
            "version_no integer",
            "quality_total_score integer",
            "quality_grade text",
            "payload jsonb NOT NULL",
            "created_at timestamptz NOT NULL DEFAULT now()",
            "updated_at timestamptz",
        ],
        "versions": [
            "id text PRIMARY KEY",
            "script_id text",
            "version_no integer",
            "source text",
            "review_status text",
            "saved_at timestamptz",
            "payload jsonb NOT NULL",
            "created_at timestamptz NOT NULL DEFAULT now()",
        ],
        "script_feedback": [
            "id text PRIMARY KEY",
            "script_id text",
            "effect_tag text",
            "payload jsonb NOT NULL",
            "created_at timestamptz NOT NULL DEFAULT now()",
        ],
    }
    return columns_by_table[logical_name]


def _supabase_columns(logical_name: str, record: dict[str, Any], jsonb: Any) -> dict[str, Any]:
    columns: dict[str, Any] = {
        "id": record["id"],
        "payload": jsonb(record),
        "created_at": record.get("created_at"),
    }
    if logical_name == "tasks":
        columns.update(
            {
                "task_name": record.get("task_name"),
                "business_goal": record.get("business_goal"),
                "platform": record.get("platform"),
                "content_type": record.get("content_type"),
                "target_user": record.get("target_user"),
                "script_count": str(record.get("script_count")) if record.get("script_count") is not None else None,
                "owner": record.get("owner"),
                "reviewer": record.get("reviewer"),
                "status": record.get("status"),
                "updated_at": record.get("updated_at"),
            }
        )
    elif logical_name == "products":
        columns.update(
            {
                "task_id": record.get("task_id"),
                "product_name": record.get("product_name"),
                "platform": record.get("platform"),
                "updated_at": record.get("updated_at"),
            }
        )
    elif logical_name == "decompositions":
        columns.update(
            {
                "task_id": record.get("task_id"),
                "product_id": record.get("product_id"),
            }
        )
    elif logical_name == "topics":
        columns.update(
            {
                "task_id": record.get("task_id"),
                "product_id": record.get("product_id"),
                "decomposition_id": record.get("decomposition_id"),
                "title": record.get("title"),
                "angle": record.get("angle"),
                "difficulty": record.get("difficulty"),
                "selected": bool(record.get("selected")),
                "updated_at": record.get("updated_at"),
            }
        )
    elif logical_name == "scripts":
        quality_score = record.get("quality_score") if isinstance(record.get("quality_score"), dict) else {}
        columns.update(
            {
                "task_id": record.get("task_id"),
                "topic_id": record.get("topic_id"),
                "product_id": record.get("product_id"),
                "title": record.get("title"),
                "product_name": record.get("product_name"),
                "platform": record.get("platform"),
                "generated_at": record.get("generated_at"),
                "saved_at": record.get("saved_at"),
                "exported_at": record.get("exported_at"),
                "status": record.get("status"),
                "review_status": record.get("review_status"),
                "reviewer": record.get("reviewer"),
                "reject_reason": record.get("reject_reason"),
                "version_no": record.get("version_no"),
                "quality_total_score": quality_score.get("total_score"),
                "quality_grade": quality_score.get("grade"),
                "updated_at": record.get("updated_at"),
            }
        )
    elif logical_name == "versions":
        columns.update(
            {
                "script_id": record.get("script_id"),
                "version_no": record.get("version_no"),
                "source": record.get("source"),
                "review_status": record.get("review_status"),
                "saved_at": record.get("saved_at"),
            }
        )
    elif logical_name == "script_feedback":
        columns.update({"script_id": record.get("script_id"), "effect_tag": record.get("effect_tag")})
    return {key: value for key, value in columns.items() if value is not None}


def _script_status_from_review(review_status: Any) -> str:
    if review_status in {"通过", "小修后通过"}:
        return "已通过"
    if review_status == "退回 AI 重写":
        return "已退回"
    if review_status == "废弃":
        return "废弃"
    return "待审核"


def _require_psycopg() -> tuple[Any, Any, Any, Any]:
    try:
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row
        from psycopg.types.json import Jsonb
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Supabase storage requires psycopg. Run `python -m pip install -r requirements.txt`."
        ) from error
    return psycopg, sql, dict_row, Jsonb


def _connect_with_retry(connect: Any, *args: Any, retries: int = 5, delay_seconds: float = 0.35, **kwargs: Any) -> Any:
    last_error: Exception | None = None
    configured_retries = int(os.environ.get("SUPABASE_CONNECT_RETRIES", str(retries)))
    for attempt in range(configured_retries):
        try:
            return connect(*args, **kwargs)
        except Exception as error:
            last_error = error
            if attempt == configured_retries - 1:
                break
            time.sleep(delay_seconds * (attempt + 1))
    if last_error:
        raise last_error
    raise RuntimeError("Unable to create Supabase database connection.")


def _required_supabase_database_url() -> str:
    url = _supabase_database_url()
    if not url:
        raise RuntimeError(
            "Supabase storage is enabled but no database connection was configured. "
            "Set SUPABASE_DB_URL, or set SUPABASE_DB_HOST/SUPABASE_DB_USER/SUPABASE_DB_PASSWORD."
        )
    return url


def _supabase_database_url() -> str:
    direct_url = os.environ.get("SUPABASE_DB_URL", "").strip()
    if direct_url:
        return direct_url

    host = os.environ.get("SUPABASE_DB_HOST", "").strip()
    password = os.environ.get("SUPABASE_DB_PASSWORD", "")
    if not host or not password:
        return ""

    user = os.environ.get("SUPABASE_DB_USER", "postgres")
    port = os.environ.get("SUPABASE_DB_PORT", "5432")
    database = os.environ.get("SUPABASE_DB_NAME", "postgres")
    sslmode = os.environ.get("SUPABASE_DB_SSLMODE", "require")
    return (
        "postgresql://"
        f"{quote(user, safe='')}:{quote(password, safe='')}"
        f"@{host}:{port}/{database}?sslmode={quote(sslmode, safe='')}"
    )


def _schema_name() -> str:
    return _valid_identifier(os.environ.get("SUPABASE_DB_SCHEMA", "app_private"), "SUPABASE_DB_SCHEMA")


def _table_name(logical_name: str) -> str:
    prefix = _valid_identifier(os.environ.get("SUPABASE_TABLE_PREFIX", "ai_script"), "SUPABASE_TABLE_PREFIX")
    return f"{prefix}_{TABLE_SUFFIXES[logical_name]}"


def _qualified_table(sql: Any, logical_name: str) -> Any:
    return sql.Identifier(_schema_name(), _table_name(logical_name))


def _valid_identifier(value: str, env_name: str) -> str:
    identifier = value.strip()
    if not IDENTIFIER_PATTERN.fullmatch(identifier):
        raise ValueError(f"{env_name} must be a valid PostgreSQL identifier.")
    return identifier


def _payload_to_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        return json.loads(payload)
    return dict(payload)


def _next_version_no(script_id: str, versions: list[dict[str, Any]]) -> int:
    existing = [int(item.get("version_no", 0)) for item in versions if item.get("script_id") == script_id]
    return max(existing, default=0) + 1
