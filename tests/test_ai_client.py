import unittest

from src.ai_client import build_deepseek_payload, build_script_prompt, build_topics_prompt, extract_response_text, parse_script_json
from src.demo_core import ProductBrief


class AIClientTests(unittest.TestCase):
    def test_build_script_prompt_contains_fact_constraints(self):
        brief = ProductBrief(
            product_name="氨基酸洁面乳",
            selling_points="温和清洁",
            target_user="油敏肌女生",
            usage_scenario="早晚洁面",
            price_offer="618 活动价",
            proof_material="检测报告",
            platform="抖音",
            business_goal="转化",
            content_type="口播",
            script_count="3",
            compliance_notes="避免医疗化表达",
        )

        prompt = build_script_prompt(brief)

        self.assertIn("只基于以下已提供信息生成", prompt)
        self.assertIn("氨基酸洁面乳", prompt)
        self.assertIn("needs_confirmation", prompt)
        self.assertIn("外貌羞辱", prompt)

    def test_build_topics_prompt_uses_script_count(self):
        brief = ProductBrief(
            product_name="氨基酸洁面乳",
            selling_points="温和清洁",
            target_user="油敏肌女生",
            usage_scenario="早晚洁面",
            price_offer="618 活动价",
            proof_material="检测报告",
            platform="抖音",
            business_goal="转化",
            content_type="口播",
            script_count="3",
            compliance_notes="避免医疗化表达",
        )

        prompt = build_topics_prompt(brief, {"pain_points": ["洗后紧绷"]})

        self.assertIn("生成 3 个短视频选题方向", prompt)
        self.assertNotIn("4-6 个", prompt)

    def test_extract_response_text_supports_output_text_shortcut(self):
        payload = {"output_text": "{\"title\":\"脚本标题\"}"}

        self.assertEqual(extract_response_text(payload), "{\"title\":\"脚本标题\"}")

    def test_build_deepseek_payload_uses_chat_completions_json_mode(self):
        brief = ProductBrief(
            product_name="氨基酸洁面乳",
            selling_points="温和清洁",
            target_user="油敏肌女生",
            usage_scenario="早晚洁面",
            price_offer="618 活动价",
            proof_material="检测报告",
            platform="抖音",
            business_goal="转化",
            content_type="口播",
            compliance_notes="避免医疗化表达",
        )

        payload = build_deepseek_payload(brief, model="deepseek-v4-flash")

        self.assertEqual(payload["model"], "deepseek-v4-flash")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertIn("json", payload["messages"][0]["content"].lower())
        self.assertIn("贬损称呼", payload["messages"][0]["content"])

    def test_extract_response_text_supports_deepseek_chat_completion(self):
        payload = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "{\"title\":\"DeepSeek 脚本\"}",
                    }
                }
            ]
        }

        self.assertEqual(extract_response_text(payload), "{\"title\":\"DeepSeek 脚本\"}")

    def test_extract_response_text_supports_nested_output_content(self):
        payload = {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "第一段"},
                        {"type": "output_text", "text": "第二段"},
                    ]
                }
            ]
        }

        self.assertEqual(extract_response_text(payload), "第一段\n第二段")

    def test_parse_script_json_accepts_markdown_fenced_json(self):
        raw = "```json\n{\"title\":\"脚本标题\",\"storyboard\":[]}\n```"

        parsed = parse_script_json(raw)

        self.assertEqual(parsed["title"], "脚本标题")
        self.assertEqual(parsed["storyboard"], [])

    def test_parse_script_json_raises_helpful_error_for_bad_payload(self):
        with self.assertRaises(ValueError) as context:
            parse_script_json("不是 JSON")

        self.assertIn("AI 返回内容不是合法 JSON", str(context.exception))


if __name__ == "__main__":
    unittest.main()
