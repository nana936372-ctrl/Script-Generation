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


if __name__ == "__main__":
    unittest.main()
