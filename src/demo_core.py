from __future__ import annotations

import csv
import html
import io
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ProductBrief:
    product_name: str = ""
    selling_points: str = ""
    target_user: str = ""
    usage_scenario: str = ""
    price_offer: str = ""
    proof_material: str = ""
    platform: str = "抖音"
    business_goal: str = "转化"
    content_type: str = "口播"
    script_count: str = "1"
    compliance_notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProductBrief":
        known = {field: data.get(field, "") for field in cls.__dataclass_fields__}
        return cls(**known)

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


REQUIRED_FIELDS = {
    "product_name": "产品名称不能为空",
    "selling_points": "核心卖点不能为空",
    "target_user": "目标用户不能为空",
}


RISK_RULES = [
    ("最好", "绝对化表达", "更适合日常使用"),
    ("第一", "绝对化表达", "表现较突出"),
    ("永久", "夸大承诺", "长期使用更有帮助"),
    ("彻底", "夸大承诺", "帮助改善使用体验"),
    ("立刻见效", "夸大承诺", "使用后更容易感受到变化"),
    ("马上变白", "夸大承诺", "帮助提亮观感"),
    ("根治", "医疗化表达", "不建议使用该表达"),
    ("治疗", "医疗化表达", "护理或改善体验"),
    ("消炎", "医疗化表达", "舒缓不适感"),
    ("全网最低", "价格误导", "当前活动价"),
    ("错过不再有", "价格误导", "活动以页面信息为准"),
    ("猪刚鬣", "贬损表达", "脸部出油明显"),
]

REVIEW_FLOW_STEPS = {
    "通过": {
        "steps": ["T7 人工审核", "T8 版本保存", "T9 CSV / Excel 导出"],
        "next_action": "保存版本并导出",
    },
    "小修后通过": {
        "steps": ["T7 人工小修", "T8 版本保存", "T9 CSV / Excel 导出"],
        "next_action": "保存小修版本并导出",
    },
    "退回 AI 重写": {
        "steps": ["T7 人工审核", "退回 T5 脚本生成", "AI 重新生成"],
        "next_action": "回到 T5 重新生成脚本",
    },
    "废弃": {
        "steps": ["T7 人工审核", "记录废弃原因", "停止进入交付"],
        "next_action": "重新选题或重新生成",
    },
}


CSV_HEADERS = [
    ("id", "脚本ID"),
    ("generated_at", "脚本生成时间"),
    ("saved_at", "版本保存时间"),
    ("exported_at", "文件导出时间"),
    ("product_name", "产品名称"),
    ("platform", "平台"),
    ("title", "选题标题"),
    ("hook", "Hook"),
    ("spoken_script", "口播脚本"),
    ("conversion_cta", "转化口播"),
    ("generation_mode", "生成模式"),
    ("review_status", "审核状态"),
    ("reviewer", "审核人"),
    ("version_no", "版本号"),
    ("review_flow.next_action", "下一流程"),
    ("quality_score.total_score", "质量总分"),
    ("quality_score.grade", "质量等级"),
]


def validate_product_brief(brief: ProductBrief) -> list[str]:
    errors: list[str] = []
    for field_name, message in REQUIRED_FIELDS.items():
        if not getattr(brief, field_name, "").strip():
            errors.append(message)
    return errors


def scan_risks(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for word, category, replacement in RISK_RULES:
        position = text.find(word)
        if position >= 0 and word not in seen:
            findings.append(
                {
                    "word": word,
                    "category": category,
                    "replacement": replacement,
                    "severity": "high" if category in {"医疗化表达", "价格误导", "贬损表达"} else "medium",
                    "position": position,
                    "snippet": _risk_snippet(text, position, len(word)),
                }
            )
            seen.add(word)
    return findings


def scan_script_risks(script: dict[str, Any]) -> list[dict[str, Any]]:
    return scan_risks(_public_script_text(script))


def build_review_flow(review_status: str) -> dict[str, Any]:
    normalized = review_status if review_status in REVIEW_FLOW_STEPS else "小修后通过"
    flow = REVIEW_FLOW_STEPS[normalized]
    return {
        "status": normalized,
        "steps": list(flow["steps"]),
        "next_action": flow["next_action"],
    }


def score_script_quality(script: dict[str, Any]) -> dict[str, Any]:
    risks = scan_script_risks(script)
    storyboard = script.get("storyboard") if isinstance(script.get("storyboard"), list) else []
    material_suggestions = (
        script.get("material_suggestions") if isinstance(script.get("material_suggestions"), list) else []
    )

    structure_score = _score_presence(
        [
            script.get("hook"),
            script.get("spoken_script"),
            storyboard,
            script.get("conversion_cta"),
            script.get("risk_notes"),
        ],
        20,
    )
    attraction_score = _score_hook(script.get("hook", ""))
    selling_score = _score_presence(
        [
            script.get("product_name") or script.get("title"),
            script.get("topic") or script.get("decomposition_snapshot"),
            script.get("subtitle_points"),
            script.get("conversion_cta"),
        ],
        20,
    )
    compliance_score = max(0, 20 - (len(risks) * 5))
    shootability_score = _score_presence([storyboard, material_suggestions], 20)

    dimensions = [
        _dimension("structure", "结构完整度", structure_score, "Hook、口播、分镜、转化和合规提醒是否齐全"),
        _dimension("attraction", "开头吸引力", attraction_score, "Hook 是否具体、短促、有痛点或场景"),
        _dimension("selling_point", "卖点准确度", selling_score, "是否围绕产品、选题和卖点稳定表达"),
        _dimension("compliance", "合规安全", compliance_score, "风险词越少，安全分越高"),
        _dimension("shootability", "可拍摄性", shootability_score, "分镜和素材建议是否可执行"),
    ]
    total_score = round(sum(item["score"] for item in dimensions))
    suggestions = _quality_suggestions(dimensions, risks)

    return {
        "total_score": total_score,
        "grade": _quality_grade(total_score),
        "go_live_ready": total_score >= 75 and compliance_score >= 14,
        "dimensions": dimensions,
        "risk_findings": risks,
        "suggestions": suggestions,
    }


def analyze_performance_feedback(
    scripts: list[dict[str, Any]],
    campaign_results: list[dict[str, Any]],
) -> dict[str, Any]:
    script_by_id = {script.get("id"): script for script in scripts if script.get("id")}
    joined: list[dict[str, Any]] = []
    for result in campaign_results:
        script = script_by_id.get(result.get("script_id"), {})
        if not script:
            continue
        joined.append(
            {
                "script_id": result.get("script_id"),
                "title": script.get("title", ""),
                "angle": (script.get("topic") or {}).get("angle", "未标注"),
                "hook": script.get("hook", ""),
                "quality_score": (script.get("quality_score") or {}).get("total_score", 0),
                "impressions": _number(result.get("impressions")),
                "three_sec_rate": _number(result.get("three_sec_rate")),
                "completion_rate": _number(result.get("completion_rate")),
                "click_rate": _number(result.get("click_rate")),
                "conversion_rate": _number(result.get("conversion_rate")),
                "roi": _number(result.get("roi")),
            }
        )

    if not joined:
        return {
            "sample_size": 0,
            "best_script": None,
            "top_patterns": [],
            "weak_patterns": [],
            "recommendations": ["先导入脚本投放数据，至少包含播放、点击或转化指标。"],
            "metric_summary": {},
        }

    best = max(joined, key=lambda item: (item["roi"], item["conversion_rate"], item["click_rate"]))
    worst = min(joined, key=lambda item: (item["roi"], item["conversion_rate"], item["click_rate"]))
    averages = _metric_averages(joined)

    return {
        "sample_size": len(joined),
        "best_script": best,
        "top_patterns": [
            f"表现最好脚本来自“{best['angle']}”角度，ROI {best['roi']:.2f}，可优先沉淀为模板。",
            f"高表现 Hook：{best['hook'] or '暂无 Hook'}",
        ],
        "weak_patterns": [
            f"低表现脚本来自“{worst['angle']}”角度，ROI {worst['roi']:.2f}，建议复查 Hook 和转化口播。"
        ],
        "recommendations": [
            "将高 ROI 脚本的 Hook、卖点表达和分镜结构加入优秀脚本库。",
            "低于平均点击率的脚本优先重写开头 3 秒和利益点表达。",
            "转化率低但完播率高的脚本，优先优化 CTA 和价格权益呈现。",
        ],
        "metric_summary": averages,
    }


def decompose_demo_selling_points(brief: ProductBrief) -> dict[str, Any]:
    product = brief.product_name.strip() or "产品"
    audience = brief.target_user.strip() or "目标用户"
    points = _split_phrases(brief.selling_points) or ["核心卖点"]
    scenarios = _split_phrases(brief.usage_scenario) or ["日常使用"]

    return {
        "pain_points": [
            f"{audience}在{scenario}时需要更明确的解决方案" for scenario in scenarios[:3]
        ],
        "scenarios": scenarios,
        "benefits": [f"{product}可围绕“{point}”展开表达" for point in points[:4]],
        "proof_points": _split_phrases(brief.proof_material) or ["证明材料需人工补充"],
        "safe_expressions": [
            f"适合{audience}在{scenarios[0]}场景下了解",
            f"围绕{points[0]}做真实体验表达",
            "价格、活动和功效以已确认信息为准",
        ],
        "risky_expressions": [
            "避免治疗、根治、彻底改善等医疗化或绝对化表达",
            "避免虚构认证、用户反馈或活动力度",
        ],
        "needs_confirmation": _confirmation_items(brief),
    }


def generate_demo_topics(brief: ProductBrief, decomposition: dict[str, Any] | None = None) -> list[dict[str, str]]:
    product = brief.product_name.strip() or "产品"
    platform = brief.platform.strip() or "抖音"
    audience = brief.target_user.strip() or "目标用户"
    pain = _first(decomposition or {}, "pain_points", f"{audience}的使用痛点")
    benefit = _first(decomposition or {}, "benefits", brief.selling_points or "核心卖点")
    scenario = _first(decomposition or {}, "scenarios", brief.usage_scenario or "日常使用")

    base_topics = [
        {
            "id": "topic-pain",
            "title": f"{audience}为什么总觉得{product}不好选？",
            "hook": f"{pain}，这条先帮你把选择逻辑讲清楚。",
            "angle": "痛点型",
            "platform": platform,
            "reason": "适合转化目标，先放大真实需求再切入卖点。",
            "risk_tip": "避免夸大功效，使用场景化表达。",
            "difficulty": "低",
        },
        {
            "id": "topic-test",
            "title": f"{product}真实使用感怎么讲更自然？",
            "hook": f"只看卖点不够，关键要看它在{scenario}里表现如何。",
            "angle": "测评型",
            "platform": platform,
            "reason": f"围绕{benefit}做体验表达，适合种草和转化。",
            "risk_tip": "证明材料必须来自已确认输入。",
            "difficulty": "中",
        },
        {
            "id": "topic-scene",
            "title": f"{scenario}场景下，{product}怎么出镜？",
            "hook": f"如果你也经常遇到{scenario}，这类产品可以这样看。",
            "angle": "场景型",
            "platform": platform,
            "reason": "便于剪辑用现有素材执行，降低拍摄难度。",
            "risk_tip": "避免把场景体验说成功效承诺。",
            "difficulty": "低",
        },
        {
            "id": "topic-live",
            "title": f"直播间讲{product}，先讲适合谁",
            "hook": f"今晚这类{product}不是所有人都要抢，先看你是不是{audience}。",
            "angle": "直播引流型",
            "platform": platform,
            "reason": "适合直播引流或活动转化，能自然引出权益。",
            "risk_tip": "活动价格以页面和运营确认信息为准。",
            "difficulty": "低",
        },
    ]
    target_count = parse_script_count(brief.script_count)
    if target_count <= len(base_topics):
        return base_topics[:target_count]

    topics = list(base_topics)
    for index in range(len(base_topics), target_count):
        number = index + 1
        topics.append(
            {
                "id": f"topic-extra-{number}",
                "title": f"{product}补充选题 {number}：换一个角度讲清楚核心卖点",
                "hook": f"{audience}看{product}，不要只看一个卖点，这条换个角度讲。",
                "angle": "补充型",
                "platform": platform,
                "reason": "用于满足本次任务脚本数量要求，提供额外可选方向。",
                "risk_tip": "仍需基于已确认卖点和证明材料表达。",
                "difficulty": "中",
            }
        )
    return topics


def generate_demo_script_from_topic(
    brief: ProductBrief,
    topic: dict[str, Any],
    decomposition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    script = generate_demo_script(brief)
    script["title"] = topic.get("title") or script["title"]
    script["hook"] = topic.get("hook") or script["hook"]
    script["topic"] = topic
    script["decomposition_snapshot"] = decomposition or {}
    script["spoken_script"] = (
        f"{script['hook']}\n"
        f"这条内容的角度是“{topic.get('angle', '脚本方向')}”。\n"
        f"我们先讲用户真实场景，再讲产品卖点：{brief.selling_points or '核心卖点'}。\n"
        f"中间用可确认的证明材料补充可信度，不能编造认证或用户反馈。\n"
        f"最后用一句明确但不过度承诺的转化口播收尾。"
    )
    script["risk_findings"] = scan_script_risks(script)
    return script


def generate_demo_script(brief: ProductBrief) -> dict[str, Any]:
    product = brief.product_name.strip() or "产品"
    audience = brief.target_user.strip() or "目标用户"
    points = brief.selling_points.strip() or "核心卖点"
    scenario = brief.usage_scenario.strip() or "日常使用场景"
    platform = brief.platform.strip() or "抖音"
    goal = brief.business_goal.strip() or "转化"

    hook = f"{audience}，是不是也遇到过这种情况：{scenario}时，总想找一款更省心的{product}？"
    spoken_script = (
        f"{hook}\n"
        f"这条内容我们重点讲清楚一个点：{points}。\n"
        f"如果你平时在{scenario}里有类似需求，可以先看它是否匹配你的使用习惯。\n"
        f"它的表达重点不是夸大效果，而是把真实场景、核心卖点和使用感受讲明白。\n"
        f"最后引导用户根据页面信息了解活动，不做未经确认的功效承诺。"
    )
    conversion_cta = "想看具体活动和适合人群，可以点击页面了解，以实际活动信息为准。"

    script = {
        "generation_mode": "demo",
        "title": f"{product}短视频脚本：{audience}的{goal}口播方向",
        "hook": hook,
        "spoken_script": spoken_script,
        "storyboard": [
            {"time": "0-3s", "visual": "人物口播开场，字幕突出用户痛点", "note": "Hook 要短，先抓场景"},
            {"time": "3-10s", "visual": "展示产品特写或使用场景", "note": "切入核心卖点"},
            {"time": "10-20s", "visual": "补充证明材料或用户反馈截图", "note": "如无素材，标记待补充"},
            {"time": "20-30s", "visual": "回到人物口播并展示页面信息", "note": "完成转化引导"},
        ],
        "subtitle_points": [
            "场景痛点先出现",
            f"核心卖点：{points}",
            "活动和功效以已确认信息为准",
        ],
        "material_suggestions": [
            "产品包装或产品质地图",
            "真实使用场景画面",
            "可确认的检测报告、活动页或用户反馈截图",
        ],
        "conversion_cta": conversion_cta,
        "risk_notes": [
            "避免使用治疗、根治、彻底改善等医疗化或绝对化表达",
            "价格、优惠、赠品和活动时间需要运营最终确认",
        ],
        "needs_confirmation": _confirmation_items(brief),
        "platform": platform,
        "product_name": product,
    }
    script["risk_findings"] = scan_script_risks(script)
    return script


def scripts_to_csv(records: list[dict[str, Any]], exported_at: str = "") -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=[header for _, header in CSV_HEADERS])
    writer.writeheader()
    for record in records:
        writer.writerow({label: _export_value(record, key, exported_at) for key, label in CSV_HEADERS})
    return buffer.getvalue()


def scripts_to_excel_xml(records: list[dict[str, Any]], exported_at: str = "") -> str:
    rows = []
    header_cells = "".join(
        f"<Cell><Data ss:Type=\"String\">{html.escape(label)}</Data></Cell>" for _, label in CSV_HEADERS
    )
    rows.append(f"<Row>{header_cells}</Row>")
    for record in records:
        cells = []
        for key, _label in CSV_HEADERS:
            value = html.escape(str(_export_value(record, key, exported_at)))
            cells.append(f"<Cell><Data ss:Type=\"String\">{value}</Data></Cell>")
        rows.append(f"<Row>{''.join(cells)}</Row>")
    return (
        "<?xml version=\"1.0\"?>\n"
        "<?mso-application progid=\"Excel.Sheet\"?>\n"
        "<Workbook xmlns=\"urn:schemas-microsoft-com:office:spreadsheet\" "
        "xmlns:ss=\"urn:schemas-microsoft-com:office:spreadsheet\">\n"
        "<Worksheet ss:Name=\"脚本库\"><Table>\n"
        f"{''.join(rows)}\n"
        "</Table></Worksheet>\n"
        "</Workbook>\n"
    )


def parse_script_count(value: Any) -> int:
    try:
        count = int(str(value).strip())
    except (TypeError, ValueError):
        return 1
    return max(1, min(count, 20))


def _risk_snippet(text: str, position: int, word_length: int) -> str:
    start = max(0, position - 18)
    end = min(len(text), position + word_length + 18)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def _confirmation_items(brief: ProductBrief) -> list[str]:
    items: list[str] = []
    if not brief.price_offer.strip():
        items.append("价格权益需运营确认")
    if not brief.proof_material.strip():
        items.append("证明材料需人工确认")
    if brief.compliance_notes.strip():
        items.append("合规要求需审核确认")
    return items


def _split_phrases(text: str) -> list[str]:
    parts = [
        part.strip()
        for part in text.replace("，", ",").replace("、", ",").replace("；", ",").replace(";", ",").split(",")
    ]
    return [part for part in parts if part]


def _first(mapping: dict[str, Any], key: str, fallback: str) -> str:
    value = mapping.get(key)
    if isinstance(value, list) and value:
        return str(value[0])
    if isinstance(value, str) and value:
        return value
    return fallback


def _flatten_script_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        texts: list[str] = []
        for child in value.values():
            texts.extend(_flatten_script_text(child))
        return texts
    if isinstance(value, list):
        texts = []
        for child in value:
            texts.extend(_flatten_script_text(child))
        return texts
    return []


def _public_script_text(script: dict[str, Any]) -> str:
    public_fields = [
        script.get("title"),
        script.get("hook"),
        script.get("spoken_script"),
        script.get("subtitle_points"),
        script.get("conversion_cta"),
    ]
    texts: list[str] = []
    for value in public_fields:
        texts.extend(_flatten_script_text(value))
    return " ".join(texts)


def _score_presence(values: list[Any], max_score: int) -> int:
    if not values:
        return 0
    hits = 0
    for value in values:
        if isinstance(value, list) and value:
            hits += 1
        elif isinstance(value, dict) and value:
            hits += 1
        elif isinstance(value, str) and value.strip():
            hits += 1
    return round(max_score * hits / len(values))


def _score_hook(hook: str) -> int:
    text = hook.strip()
    if not text:
        return 0
    score = 8
    if 8 <= len(text) <= 80:
        score += 4
    if any(mark in text for mark in ["？", "?", "！", "!"]):
        score += 3
    if any(word in text for word in ["你", "是不是", "为什么", "怎么", "别", "先"]):
        score += 3
    if any(word in text for word in ["痛", "紧绷", "出油", "场景", "早晚", "换季"]):
        score += 2
    return min(score, 20)


def _dimension(key: str, label: str, score: int, rationale: str) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "score": score,
        "max_score": 20,
        "rationale": rationale,
    }


def _quality_suggestions(dimensions: list[dict[str, Any]], risks: list[dict[str, Any]]) -> list[str]:
    suggestions = []
    for item in dimensions:
        if item["score"] < 14:
            suggestions.append(f"优化{item['label']}：{item['rationale']}。")
    if risks:
        words = "、".join(item["word"] for item in risks[:3])
        suggestions.append(f"替换风险表达：{words}。")
    if not suggestions:
        suggestions.append("质量结构完整，可进入人工审核和投放数据回流。")
    return suggestions


def _quality_grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _metric_averages(rows: list[dict[str, Any]]) -> dict[str, float]:
    keys = ["three_sec_rate", "completion_rate", "click_rate", "conversion_rate", "roi"]
    return {
        key: round(sum(row[key] for row in rows) / len(rows), 4)
        for key in keys
    }


def _export_value(record: dict[str, Any], key: str, exported_at: str = "") -> Any:
    if key == "exported_at":
        return exported_at
    if key == "generated_at":
        return record.get("generated_at") or record.get("created_at") or record.get("saved_at", "")
    if key == "saved_at":
        return record.get("saved_at") or record.get("created_at", "")

    value: Any = record
    for part in key.split("."):
        if isinstance(value, dict):
            value = value.get(part, "")
        else:
            return ""
    return value
