import os
import tempfile
import unittest
from pathlib import Path

from src.storage import (
    _supabase_database_url,
    load_decompositions,
    load_products,
    load_script_feedback,
    load_tasks,
    load_topics,
    load_campaign_results,
    load_scripts,
    load_versions,
    save_decomposition,
    save_product,
    save_campaign_result,
    save_script_feedback,
    save_script,
    save_script_version,
    save_task,
    save_topic,
    supabase_database_url_preview,
    using_supabase_storage,
    _connect_with_retry,
)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.old_backend = os.environ.get("STORAGE_BACKEND")
        os.environ["STORAGE_BACKEND"] = "jsonl"

    def tearDown(self):
        if self.old_backend is None:
            os.environ.pop("STORAGE_BACKEND", None)
        else:
            os.environ["STORAGE_BACKEND"] = self.old_backend

    def test_save_task_persists_jsonl(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.jsonl"

            saved = save_task({"task_name": "618 洁面乳", "status": "产品信息待录入"}, path)
            records = load_tasks(path)

            self.assertTrue(saved["id"].startswith("task-"))
            self.assertEqual(records[0]["task_name"], "618 洁面乳")
            self.assertEqual(records[0]["status"], "产品信息待录入")

    def test_save_script_adds_id_created_at_and_persists_jsonl(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "saved_scripts.jsonl"

            saved = save_script({"title": "脚本标题", "product_name": "洁面乳"}, path)
            records = load_scripts(path)

            self.assertTrue(saved["id"].startswith("script-"))
            self.assertIn("created_at", saved)
            self.assertEqual(records[0]["title"], "脚本标题")
            self.assertEqual(records[0]["id"], saved["id"])

    def test_load_scripts_returns_empty_list_when_file_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing.jsonl"

            self.assertEqual(load_scripts(path), [])

    def test_save_script_version_records_reviewed_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "script_versions.jsonl"

            version = save_script_version(
                {
                    "script_id": "script-1",
                    "source": "人工审核",
                    "content_json": {"title": "审核后脚本"},
                    "change_summary": "人工小修后通过",
                    "editor": "编导",
                },
                path,
            )
            versions = load_versions(path)

            self.assertEqual(version["version_no"], 1)
            self.assertEqual(versions[0]["script_id"], "script-1")
            self.assertEqual(versions[0]["source"], "人工审核")
            self.assertIn("created_at", versions[0])

    def test_save_campaign_result_persists_delivery_metrics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "campaign_results.jsonl"

            saved = save_campaign_result(
                {
                    "script_id": "script-1",
                    "impressions": 10000,
                    "three_sec_rate": 0.42,
                    "completion_rate": 0.31,
                    "click_rate": 0.08,
                    "conversion_rate": 0.025,
                    "roi": 2.4,
                },
                path,
            )
            records = load_campaign_results(path)

            self.assertTrue(saved["id"].startswith("campaign-"))
            self.assertEqual(records[0]["script_id"], "script-1")
            self.assertIn("created_at", records[0])

    def test_product_decomposition_topic_and_feedback_records_persist_jsonl(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            product = save_product(
                {
                    "task_id": "task-1",
                    "product_name": "氨基酸洁面乳",
                    "selling_points": "温和清洁",
                    "platform": "抖音",
                },
                root / "products.jsonl",
            )
            decomposition = save_decomposition(
                {
                    "task_id": "task-1",
                    "product_id": product["id"],
                    "pain_points": ["油敏肌易泛红"],
                    "benefits": ["温和清洁"],
                },
                root / "product_decompositions.jsonl",
            )
            topic = save_topic(
                {
                    "task_id": "task-1",
                    "product_id": product["id"],
                    "decomposition_id": decomposition["id"],
                    "title": "油敏肌早晚洁面",
                    "angle": "痛点切入",
                    "difficulty": "低",
                    "selected": True,
                },
                root / "topics.jsonl",
            )
            feedback = save_script_feedback(
                {
                    "script_id": "script-1",
                    "views": 1000,
                    "completion_rate": 0.31,
                    "effect_tag": "高转化",
                    "review_summary": "痛点切入有效",
                },
                root / "script_feedback.jsonl",
            )

            self.assertTrue(product["id"].startswith("product-"))
            self.assertTrue(decomposition["id"].startswith("decomposition-"))
            self.assertTrue(topic["id"].startswith("topic-"))
            self.assertTrue(feedback["id"].startswith("feedback-"))
            self.assertEqual(load_products(root / "products.jsonl")[0]["product_name"], "氨基酸洁面乳")
            self.assertEqual(load_decompositions(root / "product_decompositions.jsonl")[0]["product_id"], product["id"])
            self.assertTrue(load_topics(root / "topics.jsonl")[0]["selected"])
            self.assertEqual(load_script_feedback(root / "script_feedback.jsonl")[0]["effect_tag"], "高转化")


class SupabaseStorageConfigTests(unittest.TestCase):
    ENV_KEYS = {
        "STORAGE_BACKEND",
        "SUPABASE_DB_URL",
        "SUPABASE_DB_HOST",
        "SUPABASE_DB_PORT",
        "SUPABASE_DB_NAME",
        "SUPABASE_DB_USER",
        "SUPABASE_DB_PASSWORD",
        "SUPABASE_DB_SSLMODE",
    }

    def setUp(self):
        self.old_values = {key: os.environ.get(key) for key in self.ENV_KEYS}
        for key in self.ENV_KEYS:
            os.environ.pop(key, None)

    def tearDown(self):
        for key in self.ENV_KEYS:
            if self.old_values[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = self.old_values[key]

    def test_supabase_backend_requires_backend_or_connection_settings(self):
        self.assertFalse(using_supabase_storage())

        os.environ["SUPABASE_DB_HOST"] = "aws-0-ap-southeast-1.pooler.supabase.com"
        os.environ["SUPABASE_DB_PASSWORD"] = "secret"

        self.assertTrue(using_supabase_storage())

    def test_storage_backend_jsonl_disables_supabase_even_when_configured(self):
        os.environ["STORAGE_BACKEND"] = "jsonl"
        os.environ["SUPABASE_DB_URL"] = "postgresql://postgres:secret@example.supabase.co:5432/postgres"

        self.assertFalse(using_supabase_storage())

    def test_database_url_can_be_built_from_parts(self):
        os.environ["SUPABASE_DB_HOST"] = "aws-0-ap-southeast-1.pooler.supabase.com"
        os.environ["SUPABASE_DB_PORT"] = "5432"
        os.environ["SUPABASE_DB_NAME"] = "postgres"
        os.environ["SUPABASE_DB_USER"] = "postgres.projectref"
        os.environ["SUPABASE_DB_PASSWORD"] = "p@ss word"
        os.environ["SUPABASE_DB_SSLMODE"] = "require"

        self.assertEqual(
            _supabase_database_url(),
            "postgresql://postgres.projectref:p%40ss%20word@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require",
        )

    def test_database_url_preview_masks_password(self):
        os.environ["SUPABASE_DB_URL"] = "postgresql://postgres.projectref:secret@example.supabase.co:5432/postgres"

        self.assertEqual(
            supabase_database_url_preview(),
            "postgresql://postgres.projectref:***@example.supabase.co:5432/postgres",
        )

    def test_connect_with_retry_recovers_from_transient_failures(self):
        attempts = {"count": 0}

        def flaky_connect(*args, **kwargs):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("failed to resolve host")
            return "connected"

        self.assertEqual(
            _connect_with_retry(flaky_connect, "postgresql://example", retries=3, delay_seconds=0),
            "connected",
        )
        self.assertEqual(attempts["count"], 3)


if __name__ == "__main__":
    unittest.main()
