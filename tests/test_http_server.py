import http.client
import json
import threading
import unittest
from unittest.mock import patch

from src.demo_core import ProductBrief
from src.http_server import DemoRequestHandler, ThreadingHTTPServer
from src.http_server import _attach_script_context


class HttpServerErrorHandlingTests(unittest.TestCase):
    def test_get_api_returns_json_error_when_storage_fails(self):
        with patch("src.http_server.load_scripts", side_effect=RuntimeError("storage unavailable")):
            status, payload = self._get_json("/api/scripts")

        self.assertEqual(status, 500)
        self.assertEqual(payload["error"], "storage unavailable")

    def _get_json(self, path):
        server = ThreadingHTTPServer(("127.0.0.1", 0), DemoRequestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            connection.request("GET", path)
            response = connection.getresponse()
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


class ScriptContextTests(unittest.TestCase):
    def test_attach_script_context_builds_specific_storyboard_when_ai_omits_it(self):
        brief = ProductBrief(
            product_name="氨基酸洁面乳",
            selling_points="氨基酸表活，温和清洁，洗后不紧绷",
            target_user="18-30 岁油敏肌女生",
            usage_scenario="早晚洁面、换季清洁",
            proof_material="温和清洁检测报告",
            platform="抖音",
            business_goal="转化",
            content_type="口播",
        )
        topic = {
            "id": "topic-1",
            "title": "换季洗脸不刺痛",
            "hook": "换季洗脸像受刑？",
            "angle": "痛点型",
            "task_id": "task-1",
            "product_id": "product-1",
        }
        decomposition = {
            "task_id": "task-1",
            "product_id": "product-1",
            "pain_points": ["脸颊泛红刺痛"],
            "scenarios": ["早上 T 区油光"],
            "benefits": ["温和清洁"],
            "proof_points": ["温和清洁检测报告"],
        }

        record = _attach_script_context({"storyboard": []}, brief, topic, decomposition)
        storyboard_text = json.dumps(record["storyboard"], ensure_ascii=False)

        self.assertNotIn("人物口播开场", storyboard_text)
        self.assertNotIn("展示产品和使用场景", storyboard_text)
        self.assertIn("换季洗脸不刺痛", storyboard_text)
        self.assertIn("脸颊泛红刺痛", storyboard_text)
        self.assertIn("氨基酸表活", storyboard_text)
        self.assertIn("早上 T 区油光", storyboard_text)


if __name__ == "__main__":
    unittest.main()
