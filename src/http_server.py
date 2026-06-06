from __future__ import annotations

import json
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from src.ai_client import decompose_selling_points, generate_script, generate_script_from_topic, generate_topics
from src.config import load_project_env
from src.demo_core import (
    ProductBrief,
    analyze_performance_feedback,
    build_review_flow,
    scan_script_risks,
    scan_risks,
    score_script_quality,
    scripts_to_csv,
    scripts_to_excel_xml,
    validate_product_brief,
)
from src.storage import (
    load_decompositions,
    load_campaign_results,
    load_products,
    load_scripts,
    load_topics,
    load_tasks,
    load_versions,
    mark_scripts_exported,
    save_campaign_result,
    save_decomposition,
    save_product,
    save_script,
    save_script_feedback,
    save_script_version,
    save_task,
    save_topic,
    supabase_configured,
    supabase_database_url_preview,
    using_supabase_storage,
)


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
DATA_DIR = ROOT / "data" / "runtime"
DATA_FILE = DATA_DIR / "saved_scripts.jsonl"
TASKS_FILE = DATA_DIR / "tasks.jsonl"
PRODUCTS_FILE = DATA_DIR / "products.jsonl"
DECOMPOSITIONS_FILE = DATA_DIR / "product_decompositions.jsonl"
TOPICS_FILE = DATA_DIR / "topics.jsonl"
VERSIONS_FILE = DATA_DIR / "script_versions.jsonl"
SCRIPT_FEEDBACK_FILE = DATA_DIR / "script_feedback.jsonl"
CAMPAIGN_RESULTS_FILE = SCRIPT_FEEDBACK_FILE


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stamp_generated_at(script: dict) -> dict:
    script.setdefault("generated_at", _now_iso())
    return script


def _first_non_empty(*values: object) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _status_from_review(review_status: str) -> str:
    if review_status in {"通过", "小修后通过"}:
        return "已通过"
    if review_status == "退回 AI 重写":
        return "已退回"
    if review_status == "废弃":
        return "废弃"
    return "待审核"


def _product_record_from_brief(payload: dict, brief: ProductBrief) -> dict:
    return {
        "id": payload.get("product_id") or payload.get("id") or "",
        "task_id": payload.get("task_id", ""),
        "product_name": brief.product_name,
        "selling_points": brief.selling_points,
        "target_user": brief.target_user,
        "usage_scenarios": brief.usage_scenario,
        "price_info": brief.price_offer,
        "proof_material": brief.proof_material,
        "compliance_rules": brief.compliance_notes,
        "platform": brief.platform,
    }


def _topic_record(topic: dict, *, task_id: str = "", product_id: str = "", decomposition_id: str = "") -> dict:
    record = dict(topic)
    topic_id = str(record.get("id", ""))
    if topic_id.startswith("topic-") and topic_id[6:].isdigit():
        record["source_topic_id"] = topic_id
        record.pop("id", None)
    record.setdefault("task_id", task_id)
    record.setdefault("product_id", product_id)
    record.setdefault("decomposition_id", decomposition_id)
    record.setdefault("selected", False)
    return record


def _attach_script_context(
    script: dict,
    brief: ProductBrief,
    topic: dict,
    decomposition: dict,
) -> dict:
    record = dict(script)
    fallback_title = _first_non_empty(topic.get("title"), f"{brief.product_name}脚本")
    fallback_hook = _first_non_empty(topic.get("hook"), f"{brief.target_user}，这条内容先解决一个真实使用问题。")
    record["title"] = _first_non_empty(record.get("title"), fallback_title)
    record["hook"] = _first_non_empty(record.get("hook"), fallback_hook)
    if not str(record.get("spoken_script", "")).strip():
        angle = _first_non_empty(topic.get("angle"), "脚本方向")
        record["spoken_script"] = (
            f"{record['hook']}\n"
            f"这条内容的角度是“{angle}”。\n"
            f"重点讲清楚：{brief.selling_points or '核心卖点'}。\n"
            "先还原用户场景，再说明产品适配点，最后用页面已确认信息完成转化引导。"
        )
    record["storyboard"] = _usable_list(record.get("storyboard")) or _fallback_storyboard(
        brief,
        topic,
        decomposition,
    )
    record["subtitle_points"] = _usable_list(record.get("subtitle_points")) or [record["hook"], brief.selling_points]
    record["material_suggestions"] = _usable_list(record.get("material_suggestions")) or [
        "产品实拍",
        "使用场景画面",
        "可确认的证明材料",
    ]
    record["risk_notes"] = _usable_list(record.get("risk_notes")) or ["避免夸大、绝对化、医疗化表达"]
    record["needs_confirmation"] = _usable_list(record.get("needs_confirmation"))
    record.setdefault("task_id", topic.get("task_id", decomposition.get("task_id", "")))
    record.setdefault("topic_id", topic.get("id", ""))
    record.setdefault("product_id", topic.get("product_id", decomposition.get("product_id", "")))
    record.setdefault("product_name", brief.product_name)
    record.setdefault("platform", brief.platform)
    record.setdefault("business_goal", brief.business_goal)
    record.setdefault("content_type", brief.content_type)
    record.setdefault("topic", topic)
    record.setdefault("decomposition_snapshot", decomposition)
    record.setdefault("status", "待审核")
    return record


def _fallback_storyboard(
    brief: ProductBrief,
    topic: dict,
    decomposition: dict,
) -> list[dict[str, str]]:
    title = _short_text(_first_non_empty(topic.get("title"), f"{brief.product_name}脚本"), 22)
    hook = _short_text(_first_non_empty(topic.get("hook"), f"{brief.target_user}真实使用问题"), 28)
    pain = _short_text(_first_list_text(decomposition.get("pain_points"), brief.target_user, title), 28)
    scenario = _short_text(_first_list_text(decomposition.get("scenarios"), brief.usage_scenario, "真实使用场景"), 24)
    benefit = _short_text(_first_list_text(decomposition.get("benefits"), brief.selling_points, "核心卖点"), 28)
    proof = _short_text(_first_list_text(decomposition.get("proof_points"), brief.proof_material, "已确认证明材料"), 26)
    product = _short_text(brief.product_name or "产品", 18)
    selling_points = _short_text(brief.selling_points or benefit, 34)
    cta = _cta_storyboard_note(brief.business_goal)
    return [
        {
            "time": "0-3s",
            "visual": f"字幕打出“{title}”，镜头聚焦“{pain}”的表情或手部动作",
            "note": f"用 Hook “{hook}”切入，让痛点先被看见",
        },
        {
            "time": "3-10s",
            "visual": f"在“{scenario}”场景里展示{product}质地、起泡或冲洗细节",
            "note": f"把“{selling_points}”转成可观察的使用过程",
        },
        {
            "time": "10-20s",
            "visual": f"插入“{proof}”或围绕“{benefit}”的细节镜头",
            "note": "只使用已确认素材；没有素材时在待确认信息里标注",
        },
        {
            "time": "20-30s",
            "visual": f"回到{product}包装、活动页或评论区反馈，字幕收束到行动入口",
            "note": cta,
        },
    ]


def _usable_list(value: object) -> list:
    if isinstance(value, list):
        return [item for item in value if item]
    if value:
        return [value]
    return []


def _first_list_text(value: object, *fallbacks: object) -> str:
    if isinstance(value, list):
        for item in value:
            text = _first_non_empty(item)
            if text:
                return text
    return _first_non_empty(*fallbacks)


def _short_text(value: object, limit: int) -> str:
    text = _first_non_empty(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit - 1]}..."


def _cta_storyboard_note(business_goal: str) -> str:
    if business_goal == "种草":
        return "用真实体验和适合人群收尾，弱化硬广感"
    if business_goal == "直播引流":
        return "自然提示直播间承接，不虚构价格、库存或开播时间"
    if business_goal == "品牌曝光":
        return "强化品牌记忆点和关注动作，避免强转化压迫感"
    return "给出明确但不过度承诺的页面/购买行动引导"


def _save_ai_initial_script(script: dict) -> tuple[dict, dict]:
    saved = save_script(script, DATA_FILE)
    version = save_script_version(
        {
            "script_id": saved["id"],
            "source": "AI 生成",
            "content_json": saved,
            "change_summary": "AI 初稿生成",
            "editor": "AI",
            "review_status": saved.get("review_status", "待审核"),
            "saved_at": saved.get("generated_at"),
        },
        VERSIONS_FILE,
    )
    saved["version_no"] = version["version_no"]
    saved = save_script(saved, DATA_FILE)
    return saved, version


def _export_selected_ids(query: str) -> set[str]:
    selected_ids: set[str] = set()
    for value in parse_qs(query).get("ids", []):
        selected_ids.update(part.strip() for part in value.split(",") if part.strip())
    return selected_ids


def _filter_scripts_for_export(scripts: list[dict], selected_ids: set[str]) -> list[dict]:
    if not selected_ids:
        return scripts
    filtered: list[dict] = []
    seen_ids: set[str] = set()
    for script in scripts:
        script_id = str(script.get("id", ""))
        if script_id in selected_ids and script_id not in seen_ids:
            filtered.append(script)
            seen_ids.add(script_id)
    return filtered


def _sort_scripts_for_saved_view(scripts: list[dict]) -> list[dict]:
    indexed_scripts = list(enumerate(scripts))
    indexed_scripts.sort(
        key=lambda item: (_parse_script_sort_time(_script_saved_sort_value(item[1])), item[0]),
        reverse=True,
    )
    return [script for _index, script in indexed_scripts]


def _script_saved_sort_value(script: dict) -> str:
    return _first_non_empty(
        script.get("saved_at"),
        script.get("generated_at"),
        script.get("created_at"),
    )


def _parse_script_sort_time(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except ValueError:
        return 0.0


class DemoRequestHandler(BaseHTTPRequestHandler):
    server_version = "AIScriptDemo/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/health":
                self._send_json(
                    {
                        "storage_backend": "supabase" if using_supabase_storage() else "jsonl",
                        "supabase_configured": supabase_configured(),
                        "supabase_database_url": supabase_database_url_preview(),
                    }
                )
                return
            if parsed.path == "/api/tasks":
                self._send_json({"items": load_tasks(TASKS_FILE)})
                return
            if parsed.path == "/api/products":
                self._send_json({"items": load_products(PRODUCTS_FILE)})
                return
            if parsed.path == "/api/decompositions":
                self._send_json({"items": load_decompositions(DECOMPOSITIONS_FILE)})
                return
            if parsed.path == "/api/topics":
                self._send_json({"items": load_topics(TOPICS_FILE)})
                return
            if parsed.path == "/api/scripts":
                self._send_json({"items": _sort_scripts_for_saved_view(load_scripts(DATA_FILE))})
                return
            if parsed.path == "/api/versions":
                self._send_json({"items": load_versions(VERSIONS_FILE)})
                return
            if parsed.path == "/api/campaign-results":
                self._send_json({"items": load_campaign_results(CAMPAIGN_RESULTS_FILE)})
                return
            if parsed.path == "/api/performance-insights":
                self._send_json(
                    {
                        "insights": analyze_performance_feedback(
                            load_scripts(DATA_FILE),
                            load_campaign_results(CAMPAIGN_RESULTS_FILE),
                        )
                    }
                )
                return
            if parsed.path == "/api/export.csv":
                exported_at = _now_iso()
                selected_ids = _export_selected_ids(parsed.query)
                scripts_to_export = _filter_scripts_for_export(
                    _sort_scripts_for_saved_view(load_scripts(DATA_FILE)),
                    selected_ids,
                )
                scripts = mark_scripts_exported(scripts_to_export, DATA_FILE, exported_at)
                self._send_text(
                    scripts_to_csv(scripts, exported_at=exported_at),
                    content_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="ai-script-demo-export.csv"'},
                )
                return
            if parsed.path == "/api/export.xls":
                exported_at = _now_iso()
                selected_ids = _export_selected_ids(parsed.query)
                scripts_to_export = _filter_scripts_for_export(
                    _sort_scripts_for_saved_view(load_scripts(DATA_FILE)),
                    selected_ids,
                )
                scripts = mark_scripts_exported(scripts_to_export, DATA_FILE, exported_at)
                self._send_text(
                    scripts_to_excel_xml(scripts, exported_at=exported_at),
                    content_type="application/vnd.ms-excel; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="ai-script-demo-export.xls"'},
                )
                return
            self._serve_static(parsed.path)
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/tasks":
            self._handle_create_task()
            return
        if parsed.path == "/api/decompose":
            self._handle_decompose()
            return
        if parsed.path == "/api/topics":
            self._handle_topics()
            return
        if parsed.path == "/api/script":
            self._handle_script()
            return
        if parsed.path == "/api/scripts/batch":
            self._handle_script_batch()
            return
        if parsed.path == "/api/risk-scan":
            self._handle_risk_scan()
            return
        if parsed.path == "/api/quality-score":
            self._handle_quality_score()
            return
        if parsed.path == "/api/campaign-results":
            self._handle_campaign_result()
            return
        if parsed.path == "/api/review":
            self._handle_review()
            return
        if parsed.path == "/api/generate":
            self._handle_generate()
            return
        if parsed.path == "/api/save":
            self._handle_save()
            return
        self._send_json({"error": "接口不存在"}, status=404)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_common_headers()
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        print("%s - %s" % (self.address_string(), format % args))

    def _handle_generate(self) -> None:
        try:
            payload = self._read_json()
            brief = ProductBrief.from_dict(payload)
            errors = validate_product_brief(brief)
            if errors:
                self._send_json({"errors": errors}, status=400)
                return
            script = generate_script(brief)
            _stamp_generated_at(script)
            self._send_json({"script": script})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_create_task(self) -> None:
        try:
            payload = self._read_json()
            task = {
                "id": f"task-{uuid.uuid4().hex[:10]}",
                "task_name": payload.get("task_name", "").strip() or "未命名内容任务",
                "business_goal": payload.get("business_goal", "转化"),
                "platform": payload.get("platform", "抖音"),
                "target_user": payload.get("target_user", ""),
                "content_type": payload.get("content_type", "口播"),
                "script_count": payload.get("script_count", "1"),
                "reviewer": payload.get("reviewer", ""),
                "status": "产品信息待录入",
                "created_at": _now_iso(),
            }
            saved = save_task(task, TASKS_FILE)
            self._send_json({"task": saved})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_decompose(self) -> None:
        try:
            payload = self._read_json()
            brief = ProductBrief.from_dict(payload)
            errors = validate_product_brief(brief)
            if errors:
                self._send_json({"errors": errors}, status=400)
                return
            product = save_product(
                {key: value for key, value in _product_record_from_brief(payload, brief).items() if value},
                PRODUCTS_FILE,
            )
            decomposition = decompose_selling_points(brief)
            decomposition["task_id"] = product.get("task_id", "")
            decomposition["product_id"] = product["id"]
            saved_decomposition = save_decomposition(decomposition, DECOMPOSITIONS_FILE)
            self._send_json({"product": product, "decomposition": saved_decomposition})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_topics(self) -> None:
        try:
            payload = self._read_json()
            brief = ProductBrief.from_dict(payload.get("brief", payload))
            decomposition = payload.get("decomposition") or {}
            errors = validate_product_brief(brief)
            if errors:
                self._send_json({"errors": errors}, status=400)
                return
            topics = []
            for topic in generate_topics(brief, decomposition):
                topics.append(
                    save_topic(
                        _topic_record(
                            topic,
                            task_id=decomposition.get("task_id", payload.get("task_id", "")),
                            product_id=decomposition.get("product_id", payload.get("product_id", "")),
                            decomposition_id=decomposition.get("id", ""),
                        ),
                        TOPICS_FILE,
                    )
                )
            self._send_json({"topics": topics})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_script(self) -> None:
        try:
            payload = self._read_json()
            brief = ProductBrief.from_dict(payload.get("brief", payload))
            topic = payload.get("topic") or {}
            decomposition = payload.get("decomposition") or {}
            errors = validate_product_brief(brief)
            if errors:
                self._send_json({"errors": errors}, status=400)
                return
            if not topic:
                self._send_json({"error": "请先选择一个选题"}, status=400)
                return
            topic["selected"] = True
            saved_topic = save_topic(
                _topic_record(
                    topic,
                    task_id=decomposition.get("task_id", topic.get("task_id", "")),
                    product_id=decomposition.get("product_id", topic.get("product_id", "")),
                    decomposition_id=decomposition.get("id", topic.get("decomposition_id", "")),
                ),
                TOPICS_FILE,
            )
            script = generate_script_from_topic(brief, saved_topic, decomposition)
            _stamp_generated_at(script)
            script = _attach_script_context(script, brief, saved_topic, decomposition)
            saved_script, version = _save_ai_initial_script(script)
            self._send_json({"script": saved_script, "version": version})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_script_batch(self) -> None:
        try:
            payload = self._read_json()
            brief = ProductBrief.from_dict(payload.get("brief", payload))
            decomposition = payload.get("decomposition") or {}
            topics = payload.get("topics") or []
            errors = validate_product_brief(brief)
            if errors:
                self._send_json({"errors": errors}, status=400)
                return
            if not isinstance(topics, list) or not topics:
                self._send_json({"error": "批量生成需要选题列表"}, status=400)
                return
            scripts = []
            for topic in topics[: min(len(topics), 20)]:
                if not isinstance(topic, dict):
                    continue
                saved_topic = save_topic(
                    _topic_record(
                        topic,
                        task_id=decomposition.get("task_id", topic.get("task_id", "")),
                        product_id=decomposition.get("product_id", topic.get("product_id", "")),
                        decomposition_id=decomposition.get("id", topic.get("decomposition_id", "")),
                    ),
                    TOPICS_FILE,
                )
                script = generate_script_from_topic(brief, saved_topic, decomposition)
                _stamp_generated_at(script)
                script = _attach_script_context(script, brief, saved_topic, decomposition)
                saved_script, _version = _save_ai_initial_script(script)
                scripts.append(saved_script)
            self._send_json({"scripts": scripts})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_risk_scan(self) -> None:
        try:
            payload = self._read_json()
            text = payload.get("text")
            script = payload.get("script")
            if text is None and isinstance(script, dict):
                findings = scan_script_risks(script)
                if script.get("id"):
                    script["risk_findings"] = findings
                    save_script(script, DATA_FILE)
                self._send_json({"findings": findings})
                return
            if text is None:
                text = json.dumps(script or payload, ensure_ascii=False)
            self._send_json({"findings": scan_risks(str(text))})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_quality_score(self) -> None:
        try:
            payload = self._read_json()
            script = payload.get("script", payload)
            if not isinstance(script, dict):
                self._send_json({"error": "评分内容必须是脚本对象"}, status=400)
                return
            quality_score = score_script_quality(script)
            saved_script = None
            if script.get("id"):
                script["quality_score"] = quality_score
                saved_script = save_script(script, DATA_FILE)
            self._send_json({"quality_score": quality_score, "script": saved_script or script})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_campaign_result(self) -> None:
        try:
            payload = self._read_json()
            if not payload.get("script_id"):
                self._send_json({"error": "script_id 不能为空"}, status=400)
                return
            saved = save_script_feedback(payload, SCRIPT_FEEDBACK_FILE)
            for script in load_scripts(DATA_FILE):
                if script.get("id") == payload.get("script_id"):
                    script["status"] = "已复盘"
                    save_script(script, DATA_FILE)
                    break
            insights = analyze_performance_feedback(load_scripts(DATA_FILE), load_campaign_results(CAMPAIGN_RESULTS_FILE))
            self._send_json({"campaign_result": saved, "insights": insights})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_review(self) -> None:
        try:
            payload = self._read_json()
            script = payload.get("script", {})
            if not isinstance(script, dict):
                self._send_json({"error": "审核内容必须是脚本对象"}, status=400)
                return
            saved_at = _now_iso()
            script.setdefault("id", f"script-{uuid.uuid4().hex[:10]}")
            script.setdefault("generated_at", script.get("created_at") or saved_at)
            script["saved_at"] = saved_at
            script["review_status"] = payload.get("review_status", "小修后通过")
            script["status"] = _status_from_review(script["review_status"])
            script["reviewer"] = payload.get("reviewer", "编导")
            if script["status"] in {"已退回", "废弃"}:
                script["reject_reason"] = payload.get("change_summary", "")
            script["quality_score"] = score_script_quality(script)
            script["review_flow"] = build_review_flow(script["review_status"])
            version = save_script_version(
                {
                    "script_id": script["id"],
                    "source": "人工审核",
                    "content_json": script,
                    "change_summary": payload.get("change_summary", "人工编辑审核后保存"),
                    "editor": payload.get("reviewer", "编导"),
                    "review_status": script["review_status"],
                    "review_flow": script["review_flow"],
                    "saved_at": saved_at,
                },
                VERSIONS_FILE,
            )
            script["version_no"] = version["version_no"]
            saved = save_script(script, DATA_FILE)
            self._send_json({"script": saved, "version": version})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_save(self) -> None:
        try:
            payload = self._read_json()
            script = payload.get("script", payload)
            if not isinstance(script, dict):
                self._send_json({"error": "保存内容必须是脚本对象"}, status=400)
                return
            saved_at = _now_iso()
            script.setdefault("generated_at", script.get("created_at") or saved_at)
            script["saved_at"] = saved_at
            saved = save_script(script, DATA_FILE)
            self._send_json({"script": saved})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        if not raw.strip():
            return {}
        return json.loads(raw)

    def _serve_static(self, request_path: str) -> None:
        safe_path = unquote(request_path).lstrip("/")
        if not safe_path:
            safe_path = "index.html"
        target = (WEB_DIR / safe_path).resolve()
        if not str(target).startswith(str(WEB_DIR.resolve())) or not target.exists() or target.is_dir():
            self._send_json({"error": "文件不存在"}, status=404)
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self._send_common_headers(content_type=content_type)
        self.end_headers()
        self.wfile.write(target.read_bytes())

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self._send_common_headers(content_type="application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, *, content_type: str, headers: dict[str, str] | None = None) -> None:
        body = text.encode("utf-8-sig")
        self.send_response(200)
        self._send_common_headers(content_type=content_type)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_common_headers(self, *, content_type: str | None = None) -> None:
        if content_type:
            self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def main() -> None:
    load_project_env(ROOT)
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), DemoRequestHandler)
    print(f"AI 编导脚本生成工具 Demo 已启动：http://127.0.0.1:{port}")
    print("配置 DEEPSEEK_API_KEY 后会调用真实 DeepSeek API；未配置时使用本地演示模式。")
    server.serve_forever()


if __name__ == "__main__":
    main()
