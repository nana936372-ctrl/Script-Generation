from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from src.demo_core import (
    ProductBrief,
    decompose_demo_selling_points,
    generate_demo_script,
    generate_demo_script_from_topic,
    generate_demo_topics,
    parse_script_count,
    scan_risks,
)


DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def build_script_prompt(brief: ProductBrief) -> str:
    return f"""
你是短视频编导脚本助手。请只基于以下已提供信息生成脚本，不要编造功效、价格、认证、用户反馈或活动规则。

【产品名称】{brief.product_name}
【核心卖点】{brief.selling_points}
【目标用户】{brief.target_user}
【使用场景】{brief.usage_scenario}
【价格权益】{brief.price_offer}
【证明材料】{brief.proof_material}
【平台】{brief.platform}
【业务目标】{brief.business_goal}
【内容形式】{brief.content_type}
【合规要求】{brief.compliance_notes}

请输出严格 JSON，不要输出 Markdown。字段必须包含：
title, hook, spoken_script, storyboard, subtitle_points, material_suggestions,
conversion_cta, risk_notes, needs_confirmation。

要求：
1. storyboard 是数组，每项包含 time、visual、note。
2. subtitle_points、material_suggestions、risk_notes、needs_confirmation 都是数组。
3. 未提供的价格、证明材料、功效依据必须进入 needs_confirmation。
4. 避免绝对化、医疗化、夸大承诺和价格误导表达。
5. 口播要自然，适合真人表达，结构为 Hook -> 痛点 -> 卖点 -> 场景 -> 信任 -> 转化。
6. 不使用外貌羞辱、贬损称呼、低俗比喻或攻击性表达制造冲突。
""".strip()


def build_decomposition_prompt(brief: ProductBrief) -> str:
    return f"""
请基于产品信息做短视频脚本前置卖点拆解。只基于已提供信息，不要编造事实。

【产品名称】{brief.product_name}
【核心卖点】{brief.selling_points}
【目标用户】{brief.target_user}
【使用场景】{brief.usage_scenario}
【价格权益】{brief.price_offer}
【证明材料】{brief.proof_material}
【平台】{brief.platform}
【合规要求】{brief.compliance_notes}

输出严格 JSON，字段必须包含：
pain_points, scenarios, benefits, proof_points, safe_expressions, risky_expressions, needs_confirmation。
所有字段均为数组。
""".strip()


def build_topics_prompt(brief: ProductBrief, decomposition: dict[str, Any]) -> str:
    topic_count = parse_script_count(brief.script_count)
    return f"""
请基于任务目标、产品信息和卖点拆解，生成 {topic_count} 个短视频选题方向。

【产品名称】{brief.product_name}
【目标用户】{brief.target_user}
【平台】{brief.platform}
【业务目标】{brief.business_goal}
【内容形式】{brief.content_type}
【脚本数量】{topic_count}
【卖点拆解】{json.dumps(decomposition, ensure_ascii=False)}

输出严格 JSON，格式为：
{{
  "topics": [
    {{
      "id": "topic-1",
      "title": "",
      "hook": "",
      "angle": "",
      "platform": "",
      "reason": "",
      "risk_tip": "",
      "difficulty": "低/中/高"
    }}
  ]
}}
""".strip()


def build_topic_script_prompt(brief: ProductBrief, topic: dict[str, Any], decomposition: dict[str, Any]) -> str:
    return f"""
请基于已选选题生成短视频脚本。只基于已提供信息，不要编造产品事实。

【产品信息】{json.dumps(brief.to_dict(), ensure_ascii=False)}
【卖点拆解】{json.dumps(decomposition, ensure_ascii=False)}
【已选选题】{json.dumps(topic, ensure_ascii=False)}

请输出严格 JSON，不要输出 Markdown。字段必须包含：
title, hook, spoken_script, storyboard, subtitle_points, material_suggestions,
conversion_cta, risk_notes, needs_confirmation。

要求：
1. storyboard 是数组，每项包含 time、visual、note。
2. 不使用外貌羞辱、贬损称呼、低俗比喻或攻击性表达制造冲突。
""".strip()


def build_deepseek_payload(brief: ProductBrief, model: str | None = None) -> dict[str, Any]:
    return build_json_payload(build_script_prompt(brief), model=model)


def build_json_payload(user_prompt: str, model: str | None = None) -> dict[str, Any]:
    return {
        "model": model or os.environ.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是短视频编导脚本助手。必须输出合法 JSON 对象，不能输出 Markdown。"
                    "不要编造未提供的产品事实、价格、资质、用户反馈或活动规则。"
                    "避免外貌羞辱、贬损称呼、低俗比喻和攻击性表达。"
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
        "max_tokens": 4000,
    }


def extract_response_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()

    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]

    parts: list[str] = []
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts).strip()


def parse_script_json(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError as nested_error:
                raise ValueError(f"AI 返回内容不是合法 JSON：{nested_error}") from nested_error
        raise ValueError("AI 返回内容不是合法 JSON：未找到 JSON 对象")


def generate_script(brief: ProductBrief) -> dict[str, Any]:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        script = generate_demo_script(brief)
        script["ai_status"] = "未配置 DEEPSEEK_API_KEY，当前为本地演示模式"
        return script

    payload = _post_deepseek_chat(api_key=api_key, request_payload=build_deepseek_payload(brief))
    raw_text = extract_response_text(payload)
    parsed = parse_script_json(raw_text)
    parsed["generation_mode"] = "ai"
    parsed["ai_status"] = "已调用 DeepSeek Chat Completions API"
    parsed["product_name"] = brief.product_name
    parsed["platform"] = brief.platform
    parsed["risk_findings"] = scan_risks(" ".join(_flatten(parsed)))
    return _normalize_script(parsed)


def decompose_selling_points(brief: ProductBrief) -> dict[str, Any]:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        result = decompose_demo_selling_points(brief)
        result["generation_mode"] = "demo"
        return result
    payload = _post_deepseek_chat(api_key, build_json_payload(build_decomposition_prompt(brief)))
    result = parse_script_json(extract_response_text(payload))
    result["generation_mode"] = "ai"
    return result


def generate_topics(brief: ProductBrief, decomposition: dict[str, Any]) -> list[dict[str, Any]]:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return generate_demo_topics(brief, decomposition)
    payload = _post_deepseek_chat(api_key, build_json_payload(build_topics_prompt(brief, decomposition)))
    result = parse_script_json(extract_response_text(payload))
    topics = result.get("topics", [])
    if not isinstance(topics, list):
        raise ValueError("AI 返回的 topics 必须是数组")
    return topics[: parse_script_count(brief.script_count)]


def generate_script_from_topic(
    brief: ProductBrief,
    topic: dict[str, Any],
    decomposition: dict[str, Any],
) -> dict[str, Any]:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        script = generate_demo_script_from_topic(brief, topic, decomposition)
        script["ai_status"] = "未配置 DEEPSEEK_API_KEY，当前为本地演示模式"
        return script
    payload = _post_deepseek_chat(api_key, build_json_payload(build_topic_script_prompt(brief, topic, decomposition)))
    parsed = parse_script_json(extract_response_text(payload))
    parsed["generation_mode"] = "ai"
    parsed["ai_status"] = "已调用 DeepSeek Chat Completions API"
    parsed["product_name"] = brief.product_name
    parsed["platform"] = brief.platform
    parsed["topic"] = topic
    parsed["decomposition_snapshot"] = decomposition
    parsed["risk_findings"] = scan_risks(" ".join(_flatten(parsed)))
    return _normalize_script(parsed)


def _post_deepseek_chat(api_key: str, request_payload: dict[str, Any]) -> dict[str, Any]:
    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL).rstrip("/")
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek API 调用失败：HTTP {error.code} {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"DeepSeek API 网络连接失败：{error.reason}") from error


def _normalize_script(script: dict[str, Any]) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "title": "",
        "hook": "",
        "spoken_script": "",
        "storyboard": [],
        "subtitle_points": [],
        "material_suggestions": [],
        "conversion_cta": "",
        "risk_notes": [],
        "needs_confirmation": [],
        "risk_findings": [],
    }
    for key, value in defaults.items():
        script.setdefault(key, value)
    for key in ("storyboard", "subtitle_points", "material_suggestions", "risk_notes", "needs_confirmation", "risk_findings"):
        if not isinstance(script[key], list):
            script[key] = [script[key]]
    return script


def _flatten(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        texts: list[str] = []
        for child in value:
            texts.extend(_flatten(child))
        return texts
    if isinstance(value, dict):
        texts = []
        for child in value.values():
            texts.extend(_flatten(child))
        return texts
    return []
