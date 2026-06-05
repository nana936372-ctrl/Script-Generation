import tempfile
import unittest
from pathlib import Path

from src.storage import (
    load_campaign_results,
    load_scripts,
    load_versions,
    save_campaign_result,
    save_script,
    save_script_version,
)


class StorageTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
