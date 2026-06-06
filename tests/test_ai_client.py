import unittest
from unittest.mock import patch

from src.ai_client import (
    build_decomposition_prompt,
    build_deepseek_payload,
    build_script_prompt,
    build_topic_script_prompt,
    build_topics_prompt,
    extract_response_text,
    generate_script,
    generate_script_from_topic,
    parse_script_json,
)
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

    def test_core_prompts_include_platform_strategy_matrix(self):
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
        decomposition = {"pain_points": ["洗后紧绷"], "benefits": ["温和清洁"]}
        topic = {"title": "油敏肌洁面怎么选", "hook": "洗完脸总紧绷？", "angle": "痛点型"}

        prompts = [
            build_decomposition_prompt(brief),
            build_topics_prompt(brief, decomposition),
            build_script_prompt(brief),
            build_topic_script_prompt(brief, topic, decomposition),
        ]

        for prompt in prompts:
            self.assertIn("平台策略矩阵", prompt)
            self.assertIn("抖音：", prompt)
            self.assertIn("小红书：", prompt)
            self.assertIn("视频号：", prompt)
            self.assertIn("快手：", prompt)
            self.assertIn("B站：", prompt)

    def test_topic_script_prompt_adds_current_platform_execution_rules(self):
        brief = ProductBrief(
            product_name="氨基酸洁面乳",
            selling_points="温和清洁",
            target_user="油敏肌女生",
            usage_scenario="早晚洁面",
            price_offer="618 活动价",
            proof_material="检测报告",
            platform="小红书",
            business_goal="种草",
            content_type="口播",
            script_count="3",
            compliance_notes="避免医疗化表达",
        )

        prompt = build_topic_script_prompt(
            brief,
            {"title": "油敏肌洁面怎么选", "hook": "洗完脸总紧绷？", "angle": "测评型"},
            {"pain_points": ["洗后紧绷"], "benefits": ["温和清洁"]},
        )

        self.assertIn("当前平台执行要求", prompt)
        self.assertIn("真实体验", prompt)
        self.assertIn("避免硬广", prompt)
        self.assertIn("转化强度", prompt)

    def test_topic_script_prompt_adds_goal_and_content_execution_rules(self):
        brief = ProductBrief(
            product_name="氨基酸洁面乳",
            selling_points="温和清洁",
            target_user="油敏肌女生",
            usage_scenario="早晚洁面",
            price_offer="618 活动价",
            proof_material="检测报告",
            platform="快手、B站",
            business_goal="直播引流",
            content_type="直播切片",
            script_count="3",
            compliance_notes="避免医疗化表达",
        )

        prompt = build_topic_script_prompt(
            brief,
            {"title": "今晚直播间洁面怎么讲", "hook": "先看你是不是适合抢的人", "angle": "直播引流型"},
            {"pain_points": ["洗后紧绷"], "benefits": ["温和清洁"]},
        )

        self.assertIn("当前平台：快手、B站", prompt)
        self.assertIn("当前业务目标：直播引流", prompt)
        self.assertIn("直播间承接", prompt)
        self.assertIn("当前内容形式：直播切片", prompt)
        self.assertIn("直播片段", prompt)
        self.assertIn("内容形式策略矩阵", prompt)

    def test_topic_script_prompt_rejects_generic_storyboard_placeholders(self):
        brief = ProductBrief(
            product_name="氨基酸洁面乳",
            selling_points="氨基酸表活，温和清洁",
            target_user="油敏肌女生",
            usage_scenario="换季清洁",
            proof_material="检测报告",
            platform="抖音",
            business_goal="转化",
            content_type="口播",
            compliance_notes="避免医疗化表达",
        )

        prompt = build_topic_script_prompt(
            brief,
            {"title": "换季洗脸不刺痛", "hook": "换季洗脸像受刑？", "angle": "痛点型"},
            {"pain_points": ["脸颊泛红刺痛"], "scenarios": ["早上 T 区油光"], "benefits": ["温和清洁"]},
        )

        self.assertIn("分镜不得使用通用占位描述", prompt)
        self.assertIn("每条 storyboard 必须结合已选选题、用户痛点、产品卖点、使用场景", prompt)
        self.assertIn("人物口播开场", prompt)
        self.assertIn("展示产品和使用场景", prompt)

    def test_brand_awareness_prompt_uses_goal_specific_standards(self):
        brief = ProductBrief(
            product_name="氨基酸洁面乳",
            selling_points="温和清洁",
            target_user="油敏肌女生",
            usage_scenario="早晚洁面",
            price_offer="618 活动价",
            proof_material="检测报告",
            platform="视频号",
            business_goal="品牌曝光",
            content_type="剧情",
            script_count="3",
            compliance_notes="避免医疗化表达",
        )

        prompt = build_topics_prompt(brief, {"pain_points": ["洗后紧绷"]})

        self.assertIn("业务目标策略矩阵", prompt)
        self.assertIn("当前业务目标：品牌曝光", prompt)
        self.assertIn("品牌记忆点", prompt)
        self.assertIn("剧情冲突", prompt)

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

    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"})
    @patch(
        "src.ai_client._post_deepseek_chat",
        return_value={
            "choices": [
                {
                    "message": {
                        "content": (
                            "{\"title\":\"AI 脚本\",\"hook\":\"为什么品牌一直强调温和清洁？\","
                            "\"spoken_script\":\"品牌记忆点和品牌信任。\",\"storyboard\":[],"
                            "\"subtitle_points\":[],\"material_suggestions\":[],"
                            "\"conversion_cta\":\"关注品牌故事。\",\"risk_notes\":[],"
                            "\"needs_confirmation\":[]}"
                        )
                    }
                }
            ]
        },
    )
    def test_ai_generated_script_preserves_task_context(self, _post):
        brief = ProductBrief(
            product_name="氨基酸洁面乳",
            selling_points="温和清洁",
            target_user="油敏肌女生",
            usage_scenario="早晚洁面",
            platform="快手、B站",
            business_goal="品牌曝光",
            content_type="剧情",
        )

        direct_script = generate_script(brief)
        topic_script = generate_script_from_topic(
            brief,
            {"title": "品牌故事", "hook": "为什么强调温和清洁？"},
            {"pain_points": ["洗后紧绷"]},
        )

        for script in [direct_script, topic_script]:
            self.assertEqual(script["platform"], "快手、B站")
            self.assertEqual(script["business_goal"], "品牌曝光")
            self.assertEqual(script["content_type"], "剧情")


if __name__ == "__main__":
    unittest.main()
