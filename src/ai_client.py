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


PLATFORM_STRATEGIES = {
    "抖音": {
        "focus": "前 3 秒强 Hook、节奏快、痛点直接、转化动作明确",
        "tone": "短句、强节奏、口语化，避免长铺垫",
        "structure": "Hook -> 痛点放大 -> 产品切入 -> 证据/体验 -> 明确行动",
        "conversion": "高",
        "material": "强字幕、产品近景、使用前后状态、手势或场景快切",
    },
    "小红书": {
        "focus": "真实体验、种草感、细节可信、避免硬广",
        "tone": "像用户分享经验，弱推销、重感受和使用细节",
        "structure": "真实困扰 -> 选择理由 -> 使用体验 -> 适合人群 -> 温和建议",
        "conversion": "中",
        "material": "生活化场景、质地/使用细节、对比说明、笔记感字幕",
    },
    "视频号": {
        "focus": "信任感、稳健表达、日常适用和私域转化",
        "tone": "表达克制、可信，避免过强冲突和夸张语气",
        "structure": "场景共鸣 -> 可信解释 -> 产品价值 -> 温和引导",
        "conversion": "中",
        "material": "真人口播、产品展示、证明材料、适合熟人转发的字幕",
    },
    "快手": {
        "focus": "真实生活感、强口语化、场景直接、直播承接",
        "tone": "接地气、像熟人推荐，避免精致但悬浮的表达",
        "structure": "生活场景 -> 痛点直说 -> 解决方案 -> 直播/购买承接",
        "conversion": "高",
        "material": "真实场景、手持产品、直播间权益提示、用户反馈截图",
    },
    "B站": {
        "focus": "逻辑完整、测评解释、信息密度、弱转化",
        "tone": "解释型、理性、信息充分，避免强行带货感",
        "structure": "问题定义 -> 原理/测评 -> 对比分析 -> 结论建议",
        "conversion": "低",
        "material": "测评画面、成分/参数图、对比表、章节式字幕",
    },
}


BUSINESS_GOAL_STRATEGIES = {
    "转化": {
        "focus": "购买理由、行动路径、价格权益和明确 CTA",
        "structure": "痛点 -> 卖点利益 -> 证明/体验 -> 权益提示 -> 点击/购买行动",
        "success": "点击率、转化率、ROI",
        "generation": "转化口播要明确但不过度承诺，必须把未确认价格和活动规则放入待确认信息。",
    },
    "种草": {
        "focus": "真实体验、可信细节、适合人群和自然推荐",
        "structure": "真实困扰 -> 选择理由 -> 使用感受 -> 适合谁 -> 温和建议",
        "success": "收藏、评论、互动、后续搜索或咨询",
        "generation": "降低硬广感，强化使用细节、个人体验口吻和可信表达。",
    },
    "直播引流": {
        "focus": "直播间承接、开播理由、权益钩子和适合人群筛选",
        "structure": "直播场景 -> 人群筛选 -> 产品价值 -> 权益/时间提示 -> 进直播间行动",
        "success": "直播间点击、预约、停留和成交承接",
        "generation": "自然引出直播间，不虚构价格、库存、赠品或开播时间。",
    },
    "品牌曝光": {
        "focus": "品牌记忆点、品牌信任、情绪共鸣和可传播表达",
        "structure": "品牌场景 -> 用户共鸣 -> 品牌价值 -> 记忆点强化 -> 温和关注",
        "success": "品牌记忆、互动、分享和搜索兴趣",
        "generation": "弱化直接购买催促，强化品牌记忆点、视觉识别和可信价值。",
    },
}


CONTENT_TYPE_STRATEGIES = {
    "口播": {
        "focus": "真人表达自然、短句清楚、口播节奏稳定",
        "structure": "Hook -> 痛点 -> 卖点 -> 场景 -> 信任 -> 行动",
        "must_have": "口播可直接念，避免书面腔和长句堆叠",
        "avoid": "只写概念不写可说出口的句子",
    },
    "测评": {
        "focus": "测试维度、体验过程、对照结果和结论边界",
        "structure": "问题 -> 测评维度 -> 体验/观察 -> 结论 -> 适合人群",
        "must_have": "说明测试维度和可观察现象，不编造实验数据",
        "avoid": "把主观体验说成绝对功效",
    },
    "对比": {
        "focus": "对比对象、对照维度、差异解释和选择建议",
        "structure": "常见选择困惑 -> 对比维度 -> 差异说明 -> 适合谁",
        "must_have": "对比维度明确，避免拉踩竞品或绝对化结论",
        "avoid": "无证据贬低其他产品",
    },
    "剧情": {
        "focus": "剧情冲突、角色动机、场景转折和产品自然出现",
        "structure": "冲突开场 -> 场景推进 -> 产品解决点 -> 角色反馈 -> 记忆点",
        "must_have": "让产品服务剧情，不硬插卖点",
        "avoid": "剧情和产品卖点脱节",
    },
    "直播切片": {
        "focus": "直播片段感、主播话术、互动承接和权益提醒",
        "structure": "直播间问题 -> 主播回应 -> 产品说明 -> 权益提醒 -> 进入直播间",
        "must_have": "保留直播语气和互动感，不虚构实时价格和库存",
        "avoid": "像普通短视频口播而没有直播承接",
    },
}


STRATEGY_SPLIT_PATTERN = re.compile(r"[、,，/|；;\s]+")


def _split_strategy_names(value: str) -> list[str]:
    raw = (value or "").strip()
    if not raw:
        return []
    names: list[str] = []
    for part in STRATEGY_SPLIT_PATTERN.split(raw):
        name = part.strip()
        if name and name not in names:
            names.append(name)
    return names


def build_platform_strategy_section(platform: str) -> str:
    normalized = (platform or "").strip()
    selected_names = [name for name in _split_strategy_names(normalized) if name in PLATFORM_STRATEGIES]

    matrix_lines = [
        f"- {name}：{strategy['focus']}；语气：{strategy['tone']}；结构：{strategy['structure']}；转化强度：{strategy['conversion']}；素材重点：{strategy['material']}。"
        for name, strategy in PLATFORM_STRATEGIES.items()
    ]
    if selected_names:
        selected_lines = "\n".join(
            f"- {name}：关注点：{PLATFORM_STRATEGIES[name]['focus']}；语气：{PLATFORM_STRATEGIES[name]['tone']}；结构：{PLATFORM_STRATEGIES[name]['structure']}；转化强度：{PLATFORM_STRATEGIES[name]['conversion']}；素材重点：{PLATFORM_STRATEGIES[name]['material']}。"
            for name in selected_names
        )
        current_platform = "、".join(selected_names)
    else:
        selected_lines = (
            "- 未命中平台矩阵：按最接近的平台内容习惯处理，优先保证用户真实感、表达可信和业务目标一致；"
            "语气自然口语化，结构为 Hook -> 痛点 -> 卖点 -> 场景 -> 信任 -> 行动。"
        )
        current_platform = normalized or "未指定"
    return f"""
【平台策略矩阵】
{chr(10).join(matrix_lines)}

【当前平台执行要求】
当前平台：{current_platform}
{selected_lines}
请按当前平台执行要求调整选题角度、Hook 强度、口播语气、转化口播、分镜建议、字幕重点和素材建议。
""".strip()


def build_business_goal_strategy_section(business_goal: str) -> str:
    normalized = (business_goal or "").strip()
    selected = BUSINESS_GOAL_STRATEGIES.get(normalized)
    if not selected:
        selected = {
            "focus": "围绕当前任务目标建立可衡量的内容结果",
            "structure": "用户问题 -> 产品价值 -> 可信表达 -> 行动建议",
            "success": "按任务目标人工确认",
            "generation": "优先保证真实可信、目标一致和合规安全。",
        }
    matrix_lines = [
        f"- {name}：关注点：{strategy['focus']}；结构：{strategy['structure']}；核心指标：{strategy['success']}。"
        for name, strategy in BUSINESS_GOAL_STRATEGIES.items()
    ]
    return f"""
【业务目标策略矩阵】
{chr(10).join(matrix_lines)}

【当前业务目标执行要求】
当前业务目标：{normalized or "未指定"}
关注点：{selected["focus"]}
结构：{selected["structure"]}
核心指标：{selected["success"]}
生成要求：{selected["generation"]}
请按当前业务目标调整选题类型、脚本重心、CTA 强度、证明材料使用和质量判断标准。
""".strip()


def build_content_type_strategy_section(content_type: str) -> str:
    normalized = (content_type or "").strip()
    selected = CONTENT_TYPE_STRATEGIES.get(normalized)
    if not selected:
        selected = {
            "focus": "按最接近的短视频内容形式组织脚本",
            "structure": "Hook -> 内容主体 -> 证明/体验 -> 行动",
            "must_have": "结构清楚、可拍、可审核",
            "avoid": "形式和内容目标脱节",
        }
    matrix_lines = [
        f"- {name}：关注点：{strategy['focus']}；结构：{strategy['structure']}；必须包含：{strategy['must_have']}；避免：{strategy['avoid']}。"
        for name, strategy in CONTENT_TYPE_STRATEGIES.items()
    ]
    return f"""
【内容形式策略矩阵】
{chr(10).join(matrix_lines)}

【当前内容形式执行要求】
当前内容形式：{normalized or "未指定"}
关注点：{selected["focus"]}
结构：{selected["structure"]}
必须包含：{selected["must_have"]}
避免：{selected["avoid"]}
请按当前内容形式调整口播写法、分镜颗粒度、字幕重点和素材建议。
""".strip()


def build_generation_strategy_context(brief: ProductBrief) -> str:
    return "\n\n".join(
        [
            build_platform_strategy_section(brief.platform),
            build_business_goal_strategy_section(brief.business_goal),
            build_content_type_strategy_section(brief.content_type),
        ]
    )


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

{build_generation_strategy_context(brief)}

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
7. 分镜不得使用通用占位描述，例如“人物口播开场”“展示产品和使用场景”；每条 storyboard 必须结合已选选题、用户痛点、产品卖点、使用场景或已确认素材。
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
【业务目标】{brief.business_goal}
【内容形式】{brief.content_type}
【合规要求】{brief.compliance_notes}

{build_generation_strategy_context(brief)}

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

{build_generation_strategy_context(brief)}

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

{build_generation_strategy_context(brief)}

请输出严格 JSON，不要输出 Markdown。字段必须包含：
title, hook, spoken_script, storyboard, subtitle_points, material_suggestions,
conversion_cta, risk_notes, needs_confirmation。

要求：
1. storyboard 是数组，每项包含 time、visual、note。
2. 不使用外貌羞辱、贬损称呼、低俗比喻或攻击性表达制造冲突。
3. 分镜不得使用通用占位描述，例如“人物口播开场”“展示产品和使用场景”。
4. 每条 storyboard 必须结合已选选题、用户痛点、产品卖点、使用场景或已确认素材，写出具体镜头、字幕或动作。
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
    parsed["business_goal"] = brief.business_goal
    parsed["content_type"] = brief.content_type
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
    parsed["business_goal"] = brief.business_goal
    parsed["content_type"] = brief.content_type
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
