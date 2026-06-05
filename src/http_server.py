from __future__ import annotations

import json
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

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
    load_campaign_results,
    load_scripts,
    load_versions,
    save_campaign_result,
    save_script,
    save_script_version,
)


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
DATA_DIR = ROOT / "data" / "runtime"
DATA_FILE = DATA_DIR / "saved_scripts.jsonl"
TASKS_FILE = DATA_DIR / "tasks.jsonl"
VERSIONS_FILE = DATA_DIR / "script_versions.jsonl"
CAMPAIGN_RESULTS_FILE = DATA_DIR / "campaign_results.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stamp_generated_at(script: dict) -> dict:
    script.setdefault("generated_at", _now_iso())
    return script


class DemoRequestHandler(BaseHTTPRequestHandler):
    server_version = "AIScriptDemo/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/scripts":
            self._send_json({"items": load_scripts(DATA_FILE)})
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
            self._send_text(
                scripts_to_csv(load_scripts(DATA_FILE), exported_at=exported_at),
                content_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="ai-script-demo-export.csv"'},
            )
            return
        if parsed.path == "/api/export.xls":
            exported_at = _now_iso()
            self._send_text(
                scripts_to_excel_xml(load_scripts(DATA_FILE), exported_at=exported_at),
                content_type="application/vnd.ms-excel; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="ai-script-demo-export.xls"'},
            )
            return
        self._serve_static(parsed.path)

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
            TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with TASKS_FILE.open("a", encoding="utf-8") as file:
                file.write(json.dumps(task, ensure_ascii=False) + "\n")
            self._send_json({"task": task})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_decompose(self) -> None:
        try:
            brief = ProductBrief.from_dict(self._read_json())
            errors = validate_product_brief(brief)
            if errors:
                self._send_json({"errors": errors}, status=400)
                return
            self._send_json({"decomposition": decompose_selling_points(brief)})
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
            self._send_json({"topics": generate_topics(brief, decomposition)})
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
            script = generate_script_from_topic(brief, topic, decomposition)
            _stamp_generated_at(script)
            self._send_json({"script": script})
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
            scripts = [
                generate_script_from_topic(brief, topic, decomposition)
                for topic in topics[: min(len(topics), 20)]
                if isinstance(topic, dict)
            ]
            for script in scripts:
                _stamp_generated_at(script)
            self._send_json({"scripts": scripts})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_risk_scan(self) -> None:
        try:
            payload = self._read_json()
            text = payload.get("text")
            script = payload.get("script")
            if text is None and isinstance(script, dict):
                self._send_json({"findings": scan_script_risks(script)})
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
            self._send_json({"quality_score": score_script_quality(script)})
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _handle_campaign_result(self) -> None:
        try:
            payload = self._read_json()
            if not payload.get("script_id"):
                self._send_json({"error": "script_id 不能为空"}, status=400)
                return
            saved = save_campaign_result(payload, CAMPAIGN_RESULTS_FILE)
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
            script["reviewer"] = payload.get("reviewer", "编导")
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
