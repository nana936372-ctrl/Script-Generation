import csv
import io
import unittest

from src.demo_core import (
    ProductBrief,
    analyze_performance_feedback,
    build_review_flow,
    decompose_demo_selling_points,
    generate_demo_topics,
    generate_demo_script,
    scan_script_risks,
    scan_risks,
    score_script_quality,
    scripts_to_csv,
    scripts_to_excel_xml,
    validate_product_brief,
)


class DemoCoreTests(unittest.TestCase):
    def test_validate_product_brief_reports_required_missing_fields(self):
        brief = ProductBrief(
            product_name="",
            selling_points="温和清洁",
            target_user="",
            usage_scenario="早晚洁面",
            price_offer="",
            proof_material="",
            platform="抖音",
            business_goal="转化",
            content_type="口播",
            compliance_notes="避免医疗化表达",
        )

        errors = validate_product_brief(brief)

        self.assertIn("产品名称不能为空", errors)
        self.assertIn("目标用户不能为空", errors)
        self.assertNotIn("核心卖点不能为空", errors)

    def test_generate_demo_script_returns_structured_script_and_confirmations(self):
        brief = ProductBrief(
            product_name="氨基酸洁面乳",
            selling_points="氨基酸表活，温和清洁，洗后不紧绷",
            target_user="18-30 岁油敏肌女生",
            usage_scenario="早晚洁面、熬夜后出油",
            price_offer="",
            proof_material="",
            platform="抖音",
            business_goal="转化",
            content_type="口播",
            compliance_notes="不能承诺治疗或修复皮肤问题",
        )

        script = generate_demo_script(brief)

        self.assertEqual(script["generation_mode"], "demo")
        self.assertIn("氨基酸洁面乳", script["title"])
        self.assertTrue(script["hook"])
        self.assertTrue(script["spoken_script"])
        self.assertGreaterEqual(len(script["storyboard"]), 3)
        self.assertGreaterEqual(len(script["subtitle_points"]), 3)
        self.assertIn("价格权益需运营确认", script["needs_confirmation"])
        self.assertIn("证明材料需人工确认", script["needs_confirmation"])

    def test_decompose_demo_selling_points_returns_prd_fields(self):
        brief = ProductBrief(
            product_name="氨基酸洁面乳",
            selling_points="氨基酸表活，温和清洁，洗后不紧绷",
            target_user="18-30 岁油敏肌女生",
            usage_scenario="早晚洁面、熬夜后出油",
            price_offer="",
            proof_material="检测报告",
            platform="抖音",
            business_goal="转化",
            content_type="口播",
            compliance_notes="避免医疗化表达",
        )

        decomposition = decompose_demo_selling_points(brief)

        self.assertTrue(decomposition["pain_points"])
        self.assertTrue(decomposition["scenarios"])
        self.assertTrue(decomposition["benefits"])
        self.assertTrue(decomposition["proof_points"])
        self.assertTrue(decomposition["safe_expressions"])
        self.assertTrue(decomposition["risky_expressions"])
        self.assertIn("价格权益需运营确认", decomposition["needs_confirmation"])

    def test_generate_demo_topics_returns_selectable_topic_pool(self):
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
        decomposition = decompose_demo_selling_points(brief)

        topics = generate_demo_topics(brief, decomposition)

        self.assertEqual(len(topics), 3)
        self.assertEqual(topics[0]["platform"], "抖音")
        self.assertIn("title", topics[0])
        self.assertIn("hook", topics[0])
        self.assertIn("difficulty", topics[0])

    def test_generate_demo_topics_defaults_to_one_topic_for_invalid_count(self):
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
            script_count="abc",
            compliance_notes="避免医疗化表达",
        )

        topics = generate_demo_topics(brief, decompose_demo_selling_points(brief))

        self.assertEqual(len(topics), 1)

    def test_scan_risks_marks_high_risk_words_with_replacements(self):
        findings = scan_risks("这款产品是最好用的洁面，能立刻见效，彻底改善问题，别再像猪刚鬣。")

        words = {item["word"] for item in findings}
        categories = {item["category"] for item in findings}
        severities = {item["word"]: item["severity"] for item in findings}

        self.assertIn("最好", words)
        self.assertIn("立刻见效", words)
        self.assertIn("彻底", words)
        self.assertIn("猪刚鬣", words)
        self.assertIn("绝对化表达", categories)
        self.assertIn("贬损表达", categories)
        self.assertEqual(severities["猪刚鬣"], "high")
        self.assertTrue(all(item["replacement"] for item in findings))
        self.assertTrue(all(item["snippet"] for item in findings))
        self.assertTrue(all(isinstance(item["position"], int) for item in findings))

    def test_scan_script_risks_ignores_internal_risk_notes(self):
        script = generate_demo_script(
            ProductBrief(
                product_name="氨基酸洁面乳",
                selling_points="温和清洁",
                target_user="油敏肌女生",
                usage_scenario="早晚洁面",
                price_offer="618 活动价",
                proof_material="检测报告",
                compliance_notes="不能承诺治疗、根治、彻底改善",
            )
        )

        words = {item["word"] for item in scan_script_risks(script)}

        self.assertNotIn("治疗", words)
        self.assertNotIn("根治", words)
        self.assertNotIn("彻底", words)

        script["spoken_script"] += "\n这句口播故意写根治和彻底。"

        words = {item["word"] for item in scan_script_risks(script)}
        self.assertIn("根治", words)
        self.assertIn("彻底", words)

    def test_scripts_to_csv_exports_saved_scripts_with_readable_headers(self):
        records = [
            {
                "id": "script-1",
                "created_at": "2026-06-03T18:30:00",
                "generated_at": "2026-06-03T18:25:00",
                "saved_at": "2026-06-03T18:35:00",
                "product_name": "氨基酸洁面乳",
                "platform": "抖音",
                "title": "油敏肌洁面怎么选",
                "hook": "洗完脸总紧绷？",
                "spoken_script": "这条脚本\n包含换行",
                "conversion_cta": "点击了解",
                "generation_mode": "demo",
            }
        ]

        csv_text = scripts_to_csv(records, exported_at="2026-06-03T19:00:00")
        rows = list(csv.DictReader(io.StringIO(csv_text)))

        self.assertEqual(rows[0]["脚本ID"], "script-1")
        self.assertEqual(rows[0]["脚本生成时间"], "2026-06-03T18:25:00")
        self.assertEqual(rows[0]["版本保存时间"], "2026-06-03T18:35:00")
        self.assertEqual(rows[0]["文件导出时间"], "2026-06-03T19:00:00")
        self.assertEqual(rows[0]["产品名称"], "氨基酸洁面乳")
        self.assertEqual(rows[0]["口播脚本"], "这条脚本\n包含换行")

    def test_scripts_to_csv_exports_review_version_and_quality_fields(self):
        records = [
            {
                "id": "script-1",
                "created_at": "2026-06-03T18:30:00",
                "product_name": "氨基酸洁面乳",
                "platform": "抖音",
                "title": "油敏肌洁面怎么选",
                "hook": "洗完脸总紧绷？",
                "spoken_script": "口播内容",
                "conversion_cta": "点击了解",
                "generation_mode": "demo",
                "review_status": "小修后通过",
                "reviewer": "编导负责人",
                "version_no": 2,
                "quality_score": {"total_score": 88, "grade": "B"},
            }
        ]

        csv_text = scripts_to_csv(records)
        rows = list(csv.DictReader(io.StringIO(csv_text)))

        self.assertEqual(rows[0]["审核状态"], "小修后通过")
        self.assertEqual(rows[0]["审核人"], "编导负责人")
        self.assertEqual(rows[0]["版本号"], "2")
        self.assertIn("下一流程", rows[0])
        self.assertEqual(rows[0]["质量总分"], "88")
        self.assertEqual(rows[0]["质量等级"], "B")

    def test_scripts_to_csv_exports_hidden_ai_suggestion_fields(self):
        records = [
            {
                "id": "script-1",
                "title": "油敏肌洁面怎么选",
                "storyboard": [
                    {"time": "0-3s", "visual": "产品特写", "note": "字幕突出温和"},
                    {"time": "3-8s", "visual": "起泡使用", "note": "说明洗后不紧绷"},
                ],
                "subtitle_points": ["温和清洁", "洗后不紧绷"],
                "material_suggestions": ["产品实拍", "检测报告截图"],
                "risk_notes": ["避免医疗化表达"],
                "needs_confirmation": ["价格权益需运营确认"],
            }
        ]

        csv_text = scripts_to_csv(records)
        rows = list(csv.DictReader(io.StringIO(csv_text)))

        self.assertIn("分镜建议", rows[0])
        self.assertIn("字幕重点", rows[0])
        self.assertIn("素材建议", rows[0])
        self.assertIn("合规提醒", rows[0])
        self.assertIn("待确认信息", rows[0])
        self.assertIn("0-3s", rows[0]["分镜建议"])
        self.assertIn("产品特写", rows[0]["分镜建议"])
        self.assertIn("温和清洁", rows[0]["字幕重点"])
        self.assertIn("检测报告截图", rows[0]["素材建议"])

    def test_scripts_to_csv_falls_back_to_created_at_for_missing_generation_time(self):
        records = [{"id": "script-1", "created_at": "2026-06-03T18:30:00"}]

        csv_text = scripts_to_csv(records, exported_at="2026-06-03T19:00:00")
        rows = list(csv.DictReader(io.StringIO(csv_text)))

        self.assertEqual(rows[0]["脚本生成时间"], "2026-06-03T18:30:00")
        self.assertEqual(rows[0]["版本保存时间"], "2026-06-03T18:30:00")
        self.assertEqual(rows[0]["文件导出时间"], "2026-06-03T19:00:00")

    def test_scripts_to_excel_xml_exports_excel_readable_workbook(self):
        records = [
            {
                "id": "script-1",
                "created_at": "2026-06-03T18:30:00",
                "product_name": "氨基酸洁面乳",
                "platform": "抖音",
                "title": "油敏肌洁面怎么选",
                "hook": "洗完脸总紧绷？",
                "spoken_script": "口播内容",
                "conversion_cta": "点击了解",
                "generation_mode": "demo",
            }
        ]

        xml = scripts_to_excel_xml(records, exported_at="2026-06-03T19:00:00")

        self.assertIn("<?xml version=\"1.0\"?>", xml)
        self.assertIn("<Workbook", xml)
        self.assertIn("脚本生成时间", xml)
        self.assertIn("文件导出时间", xml)
        self.assertIn("2026-06-03T19:00:00", xml)
        self.assertIn("氨基酸洁面乳", xml)
        self.assertIn("油敏肌洁面怎么选", xml)

    def test_scripts_to_excel_xml_exports_quality_and_review_headers(self):
        records = [
            {
                "id": "script-1",
                "created_at": "2026-06-03T18:30:00",
                "product_name": "氨基酸洁面乳",
                "platform": "抖音",
                "title": "油敏肌洁面怎么选",
                "hook": "洗完脸总紧绷？",
                "spoken_script": "口播内容",
                "conversion_cta": "点击了解",
                "generation_mode": "demo",
                "review_status": "通过",
                "version_no": 1,
                "quality_score": {"total_score": 91, "grade": "A"},
            }
        ]

        xml = scripts_to_excel_xml(records)

        self.assertIn("审核状态", xml)
        self.assertIn("版本号", xml)
        self.assertIn("下一流程", xml)
        self.assertIn("质量总分", xml)
        self.assertIn("91", xml)
        self.assertIn("通过", xml)

    def test_scripts_to_excel_xml_exports_hidden_ai_suggestion_fields(self):
        records = [
            {
                "id": "script-1",
                "storyboard": [{"time": "0-3s", "visual": "产品特写", "note": "开场"}],
                "subtitle_points": ["温和清洁"],
                "material_suggestions": ["产品实拍"],
            }
        ]

        xml = scripts_to_excel_xml(records)

        self.assertIn("分镜建议", xml)
        self.assertIn("字幕重点", xml)
        self.assertIn("素材建议", xml)
        self.assertIn("0-3s", xml)
        self.assertIn("产品实拍", xml)

    def test_build_review_flow_maps_status_to_next_step(self):
        rewrite_flow = build_review_flow("退回 AI 重写")
        pass_flow = build_review_flow("通过")

        self.assertIn("退回 T5 脚本生成", rewrite_flow["steps"])
        self.assertEqual(rewrite_flow["next_action"], "回到 T5 重新生成脚本")
        self.assertEqual(pass_flow["next_action"], "保存版本并导出")

    def test_score_script_quality_returns_dimension_scores_and_gate(self):
        script = generate_demo_script(
            ProductBrief(
                product_name="氨基酸洁面乳",
                selling_points="氨基酸表活，温和清洁，洗后不紧绷",
                target_user="油敏肌女生",
                usage_scenario="早晚洁面",
                price_offer="618 活动价",
                proof_material="检测报告",
                platform="抖音",
                business_goal="转化",
                content_type="口播",
                compliance_notes="避免医疗化表达",
            )
        )

        score = score_script_quality(script)

        self.assertGreaterEqual(score["total_score"], 70)
        self.assertIn(score["grade"], {"A", "B", "C", "D"})
        self.assertIn("dimensions", score)
        self.assertEqual(len(score["dimensions"]), 6)
        self.assertIn("go_live_ready", score)
        self.assertTrue(score["suggestions"])

    def test_score_script_quality_uses_business_goal_specific_standard(self):
        script = {
            "title": "品牌故事脚本",
            "hook": "为什么这个品牌一直强调温和清洁？",
            "spoken_script": "用一个早晚洁面的真实场景，讲清楚品牌记忆点、品牌信任和长期价值。",
            "storyboard": [{"time": "0-3s", "visual": "生活场景", "note": "建立品牌印象"}],
            "subtitle_points": ["品牌记忆点", "温和清洁", "可信表达"],
            "material_suggestions": ["品牌视觉", "产品实拍"],
            "conversion_cta": "关注品牌故事，了解更多日常护理思路。",
            "risk_notes": ["不夸大功效"],
            "business_goal": "品牌曝光",
        }

        score = score_script_quality(script)
        goal_dimension = next(item for item in score["dimensions"] if item["key"] == "business_goal")

        self.assertEqual(goal_dimension["label"], "业务目标适配度")
        self.assertIn("品牌曝光", goal_dimension["rationale"])
        self.assertGreaterEqual(goal_dimension["score"], 10)

    def test_score_script_quality_reduces_compliance_when_risks_exist(self):
        script = generate_demo_script(
            ProductBrief(
                product_name="氨基酸洁面乳",
                selling_points="温和清洁",
                target_user="油敏肌女生",
                usage_scenario="早晚洁面",
                price_offer="618 活动价",
                proof_material="检测报告",
            )
        )
        script["spoken_script"] += "\n这款能根治敏感，永久修复。"

        score = score_script_quality(script)
        compliance = next(item for item in score["dimensions"] if item["key"] == "compliance")

        self.assertLess(compliance["score"], compliance["max_score"])
        self.assertFalse(score["go_live_ready"])

    def test_analyze_performance_feedback_builds_optimization_recommendations(self):
        scripts = [
            {
                "id": "script-1",
                "title": "痛点选题",
                "hook": "洗完脸总紧绷？",
                "topic": {"angle": "痛点型"},
                "quality_score": {"total_score": 88},
            },
            {
                "id": "script-2",
                "title": "测评选题",
                "hook": "真实使用感怎么讲？",
                "topic": {"angle": "测评型"},
                "quality_score": {"total_score": 72},
            },
        ]
        campaign_results = [
            {
                "script_id": "script-1",
                "impressions": 10000,
                "three_sec_rate": 0.42,
                "completion_rate": 0.31,
                "click_rate": 0.08,
                "conversion_rate": 0.025,
                "roi": 2.4,
            },
            {
                "script_id": "script-2",
                "impressions": 8000,
                "three_sec_rate": 0.24,
                "completion_rate": 0.16,
                "click_rate": 0.03,
                "conversion_rate": 0.008,
                "roi": 0.9,
            },
        ]

        feedback = analyze_performance_feedback(scripts, campaign_results)

        self.assertEqual(feedback["sample_size"], 2)
        self.assertEqual(feedback["best_script"]["script_id"], "script-1")
        self.assertTrue(feedback["top_patterns"])
        self.assertTrue(feedback["recommendations"])


if __name__ == "__main__":
    unittest.main()
