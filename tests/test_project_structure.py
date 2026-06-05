import unittest
from pathlib import Path


class ProjectStructureTests(unittest.TestCase):
    def test_http_server_module_owns_runtime_paths(self):
        from src import http_server

        self.assertEqual(http_server.DATA_DIR.name, "runtime")
        self.assertEqual(http_server.DATA_FILE.parent, http_server.DATA_DIR)
        self.assertEqual(http_server.TASKS_FILE.parent, http_server.DATA_DIR)
        self.assertEqual(http_server.VERSIONS_FILE.parent, http_server.DATA_DIR)

    def test_root_server_is_thin_launcher(self):
        server_source = Path("server.py").read_text(encoding="utf-8")

        self.assertIn("from src.http_server import main", server_source)
        self.assertLess(len(server_source.splitlines()), 20)

    def test_product_docs_live_under_docs_prd(self):
        self.assertTrue(Path("docs/prd/AI编导脚本生成工具_PRD.md").exists())
        self.assertTrue(Path("docs/prd/AI编导脚本生成工具_PRD.docx").exists())

    def test_review_save_writes_system_saved_time(self):
        server_source = Path("src/http_server.py").read_text(encoding="utf-8")

        self.assertIn("saved_at = _now_iso()", server_source)
        self.assertIn("script[\"saved_at\"] = saved_at", server_source)
        self.assertIn("\"saved_at\": saved_at", server_source)

    def test_export_filter_selects_requested_script_ids_only(self):
        from src.http_server import _filter_scripts_for_export

        scripts = [
            {"id": "script-a", "title": "A"},
            {"id": "script-b", "title": "B"},
            {"id": "script-c", "title": "C"},
        ]

        self.assertEqual(
            [script["id"] for script in _filter_scripts_for_export(scripts, {"script-c", "script-a"})],
            ["script-a", "script-c"],
        )
        self.assertEqual(_filter_scripts_for_export(scripts, set()), scripts)
        scripts_with_duplicates = [
            {"id": "script-a", "title": "A"},
            {"id": "script-a", "title": "A duplicate"},
        ]
        self.assertEqual(
            [script["title"] for script in _filter_scripts_for_export(scripts_with_duplicates, {"script-a"})],
            ["A"],
        )

    def test_export_routes_parse_selected_ids(self):
        server_source = Path("src/http_server.py").read_text(encoding="utf-8")

        self.assertIn("parse_qs", server_source)
        self.assertIn("_export_selected_ids", server_source)
        self.assertIn("_filter_scripts_for_export", server_source)

    def test_attach_script_context_fills_missing_ai_fields_from_topic(self):
        from src.demo_core import ProductBrief
        from src.http_server import _attach_script_context

        brief = ProductBrief(
            product_name="氨基酸洁面乳",
            selling_points="温和清洁，洗后不紧绷",
            target_user="油敏肌女生",
            usage_scenario="早晚洁面",
            platform="抖音",
        )
        topic = {
            "id": "topic-1",
            "title": "油敏肌洁面怎么选",
            "hook": "洗完脸总紧绷？",
            "angle": "换季敏感",
        }

        record = _attach_script_context({"title": "", "hook": "", "spoken_script": ""}, brief, topic, {})

        self.assertEqual(record["title"], "油敏肌洁面怎么选")
        self.assertEqual(record["hook"], "洗完脸总紧绷？")
        self.assertIn("温和清洁，洗后不紧绷", record["spoken_script"])
        self.assertIn("换季敏感", record["spoken_script"])

    def test_env_example_documents_supabase_storage(self):
        env_example = Path(".env.example").read_text(encoding="utf-8")

        self.assertIn("STORAGE_BACKEND=jsonl", env_example)
        self.assertIn("SUPABASE_DB_PASSWORD=", env_example)
        self.assertIn("SUPABASE_DB_SCHEMA=app_private", env_example)

    def test_supabase_schema_tracks_prd_entities(self):
        schema = Path("docs/supabase/storage_schema.sql").read_text(encoding="utf-8")

        self.assertIn("ai_script_products", schema)
        self.assertIn("ai_script_product_decompositions", schema)
        self.assertIn("ai_script_topics", schema)
        self.assertIn("ai_script_script_feedback", schema)
        self.assertIn("status text", schema)
        self.assertIn("updated_at timestamptz", schema)


if __name__ == "__main__":
    unittest.main()
