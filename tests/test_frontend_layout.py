import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_workflow_cards_use_paged_workbench():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'class="step-workbench"' in html
    assert 'class="step-rail"' in html
    assert 'class="step-stage"' in html
    assert 'data-step-target="taskCard"' in html
    assert 'data-step-target="decompositionCard"' in html
    assert 'data-step-target="topicsCard"' in html
    assert 'data-step-target="scriptCard"' in html
    assert 'data-step-target="riskCard"' in html
    assert 'data-step-target="reviewCard"' in html

    assert "setActiveStepPage" in js
    assert "data-step-target" in js
    assert "setActiveStepPage(\"decompositionCard\")" in js
    assert "setActiveStepPage(\"topicsCard\")" in js
    assert "setActiveStepPage(\"scriptCard\")" in js

    assert "step-column" not in html
    expected_order = [
        'id="taskCard"',
        'id="decompositionCard"',
        'id="topicsCard"',
        'id="scriptCard"',
        'id="riskCard"',
        'id="reviewCard"',
    ]
    positions = [html.index(marker) for marker in expected_order]
    assert positions == sorted(positions)

    step_card_rule = re.search(r"\.step-card\s*\{(?P<body>.*?)\n\}", css, re.S)
    assert step_card_rule is not None
    assert "height: 100%;" in step_card_rule.group("body")
    assert "overflow: hidden;" in step_card_rule.group("body")
    assert ".step-card:not(.active)" in css
    assert "display: none;" in css
    assert ".step-stage" in css
    step_stage_body = re.search(r"\.step-stage\s*\{(?P<body>.*?)\n\}", css, re.S).group("body")
    assert "height:" in step_stage_body
    assert "height: var(--stage-height);" in step_stage_body

    step_workbench_body = re.search(r"\.step-workbench\s*\{(?P<body>.*?)\n\}", css, re.S).group("body")
    assert "--stage-height:" in step_workbench_body
    stage_height = int(re.search(r"--stage-height:\s*(\d+)px", step_workbench_body).group(1))
    assert stage_height >= 640

    step_rail_body = re.search(r"\.step-rail\s*\{(?P<body>.*?)\n\}", css, re.S).group("body")
    assert "height: var(--stage-height);" in step_rail_body

    assert ".result-content" in css
    assert "setResultContent(taskResult" in js
    assert "node.className = \"result-content\";" in js


def test_generated_sections_use_fixed_browsable_modules():
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    topic_window_rule = re.search(r"\.topic-carousel-window\s*\{(?P<body>.*?)\n\}", css, re.S)
    script_stage_rule = re.search(r"\.script-module-stage\s*\{(?P<body>.*?)\n\}", css, re.S)

    assert topic_window_rule is not None
    assert "height:" in topic_window_rule.group("body")
    assert "overflow: hidden;" in topic_window_rule.group("body")
    assert "data-topic-carousel-action" in js
    assert "updateTopicCarousel" in js
    assert "data-carousel-page-size" in js
    assert "renderCarouselSizeOptions" in js

    assert "renderInsightTiles" in js
    assert "insight-tile" in js
    assert "overflow: hidden;" in re.search(r"\.insight-carousel-window\s*\{(?P<body>.*?)\n\}", css, re.S).group("body")
    assert "#decompositionCard .result-content" in css
    assert "#topicsCard .result-content" in css
    assert "align-content: stretch;" in css
    assert 'renderListBlock("用户痛点"' not in js

    assert script_stage_rule is not None
    assert "height:" in script_stage_rule.group("body")
    assert "overflow-y: auto;" in script_stage_rule.group("body")
    script_active_rule = re.search(r"\.script-module\.active\s*\{(?P<body>.*?)\n\}", css, re.S)
    assert script_active_rule is not None
    assert "min-height: 100%;" in script_active_rule.group("body")
    assert "data-script-module-action" in js
    assert "updateScriptModule" in js
    assert "renderScriptModules" in js
    assert 'renderListBlock("字幕重点"' not in js


def test_decomposition_carousel_and_sticky_workflow_nav():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    insight_window_rule = re.search(r"\.insight-carousel-window\s*\{(?P<body>.*?)\n\}", css, re.S)
    workflow_nav_rule = re.search(r"\.workflow-nav\s*\{(?P<body>.*?)\n\}", css, re.S)

    assert insight_window_rule is not None
    assert "height:" in insight_window_rule.group("body")
    assert "overflow: hidden;" in insight_window_rule.group("body")
    assert "data-insight-carousel-action" in js
    assert "updateInsightCarousel" in js

    assert '<nav class="workflow-nav"' in html
    assert workflow_nav_rule is not None
    assert "position: sticky;" in workflow_nav_rule.group("body")
    assert 'href="#taskCard"' in html
    assert 'href="#productTitle"' in html
    assert 'href="#decompositionCard"' in html
    assert 'href="#topicsCard"' in html
    assert 'href="#scriptCard"' in html
    assert 'href="#riskCard"' in html
    assert 'href="#reviewCard"' in html
    assert 'href="#tableTitle"' in html
    assert "scroll-padding-top:" in css
    assert "workflow-step" in js


def test_quality_library_and_feedback_modules_are_exposed():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'id="qualityCard"' in html
    assert 'id="libraryCard"' in html
    assert 'id="feedbackCard"' in html
    assert 'data-step-target="qualityCard"' in html
    assert 'data-step-target="libraryCard"' in html
    assert 'data-step-target="feedbackCard"' in html
    assert 'href="#qualityCard"' in html
    assert 'href="#libraryCard"' in html
    assert 'href="#feedbackCard"' in html

    assert "scoreQualityButton" in js
    assert "renderQualityScore" in js
    assert "renderScriptLibrary" in js
    assert "renderPerformanceFeedback" in js
    assert 'postJson("/api/quality-score"' in js
    assert 'postJson("/api/campaign-results"' in js
    assert 'getJson("/api/performance-insights"' in js

    assert ".score-grid" in css
    assert ".library-list" in css
    assert ".metric-form" in css


def test_workflow_phase_labels_and_task_card_without_readiness_panel():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'id="readinessResult"' not in html
    assert 'class="readiness-panel"' not in html
    assert "P0 就绪度" not in html
    assert "renderReadinessChecklist" not in js
    assert "updateP0Check" not in js
    assert "质量分" in html
    assert "质量分" in js
    assert "质量总分" in js
    assert ".readiness-grid" not in css
    assert ".readiness-meter" not in css

    assert '<span class="phase-tag">P0</span>' not in html
    assert '<span class="phase-tag">P1</span>' not in html
    for step in range(1, 10):
        assert f'<span class="phase-tag">T{step}</span>' in html

    assert len(re.findall(r'class="workflow-step[^"]*"\s+data-phase="p0"', html)) == 9
    assert len(re.findall(r'class="workflow-step[^"]*"\s+data-phase="p1"', html)) >= 3
    assert "phase-tag" in html
    assert '.workflow-step[data-phase="p0"]' in css
    assert '.workflow-step[data-phase="p1"]' in css
    assert 'class="workflow-group p0-chain"' in html
    assert 'class="workflow-group p1-tools"' in html
    assert "P0 核心链路" in html
    assert "P1 增强能力" in html
    assert html.index("P0 核心链路") < html.index("P1 增强能力")
    assert html.index('<span class="phase-tag">T9</span>') < html.index("P1 增强能力")
    assert "data-flow-index" in html
    assert "markWorkflowProgress" in js


def test_workbench_cards_use_dense_horizontal_browsing():
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "grid-template-columns: repeat(var(--page-columns" in css
    assert "grid-template-rows: repeat(var(--page-rows" in css
    assert ".topic-slide[hidden]" in css
    assert ".insight-slide[hidden]" in css
    assert "updatePagedCarousel" in js
    assert ".step-rail-item[data-phase=\"p0\"]" in css
    assert ".step-rail-item[data-phase=\"p1\"]" in css
    assert ".badge[data-tooltip]" in css
    assert "box-shadow" not in re.search(r"\.badge\[data-tooltip\]:hover::after,\s*\n\.badge\[data-tooltip\]:focus-visible::after\s*\{(?P<body>.*?)\n\}", css, re.S).group("body")
    assert 'data-tooltip="${escapeHtml(getAngleHelp(topic.angle))}"' in js
    assert 'data-tooltip="${escapeHtml(getDifficultyHelp(topic.difficulty))}"' in js


def test_topic_cards_keep_selection_button_visible():
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "topic-card-header" in js
    assert "topic-card-body" in js
    assert "topic-card-footer" in js
    assert "topic-select-button" in js
    assert ".topic-card-header" in css
    assert ".topic-card-body" in css
    assert ".topic-card-footer" in css
    assert ".topic-select-button" in css
    topic_card_rule = re.search(r"\.topic-card\s*\{(?P<body>.*?)\n\}", css, re.S)
    assert topic_card_rule is not None
    assert "grid-template-rows: auto minmax(0, 1fr) auto;" in topic_card_rule.group("body")
    assert "overflow-y: auto;" in re.search(r"\.topic-card-body\s*\{(?P<body>.*?)\n\}", css, re.S).group("body")


def test_review_status_flow_and_regenerate_action_are_exposed():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'id="regenerateScriptButton"' in html
    assert 'id="reviewRegenerateButton"' in html
    assert 'id="reviewFlowHint"' in html
    assert 'id="reviewChecklist"' in html
    assert "AI 重新生成" in html
    assert "reviewFlowMap" in js
    assert "updateReviewFlowHint" in js
    assert "updateReviewChecklist" in js
    assert "renderReviewCheckItem" in js
    assert "交付前检查" in js
    assert "当前浏览未确认" in js
    assert "待初筛" in js
    assert "保存前会自动补跑当前脚本风险初筛" in js
    assert "generateScriptFromSelectedTopic" in js
    assert "退回 T5" in js
    assert "退回 AI 重写" in js
    assert ".review-flow-hint" in css
    assert ".review-check-card" in css
    assert ".review-check-item" in css
    assert ".review-actions" in css


def test_p0_batch_generation_and_risk_highlight_are_exposed():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'id="batchScriptButton"' in html
    assert "批量生成脚本" in html
    assert "/api/scripts/batch" in js
    assert "generateBatchScripts" in js
    assert "getBatchTopicsForRegeneration" in js
    assert "regenerateCurrentScriptInBatch" in js
    assert "currentScripts" in js
    assert "selectedScriptIndex" in js
    assert "data-script-index" in js
    assert "data-script-select" in js
    assert "data-choose-script" in js
    assert "选择此脚本" in js
    assert "scoreCurrentScript({ activate: true, scroll: true })" in js
    assert "scanGeneratedScriptRisks" in js
    assert "批量风险词初筛完成" in js
    assert "script-batch-strip" in js
    assert "script-select-wrap" in js
    assert "renderRiskRulePanel" in js
    assert "renderRiskBatchOverview" in js
    assert "data-risk-script-select" in js
    assert "data-risk-script-index" in js
    assert "扫描标题、Hook、口播、字幕重点、转化口播" in js
    assert ".script-batch-strip" in css
    assert ".script-select-wrap" in css
    assert ".script-tab.active" in css
    assert ".script-choose-button" in css
    assert ".quality-context" in css
    assert ".risk-rule-panel" in css
    assert ".risk-batch-overview" in css
    assert ".risk-script-row" in css
    assert ".risk-finding-row" in css
    assert "risk-marked-copy" in js
    assert "highlightRiskWords" in js
    assert ".risk-marked-copy mark" in css


def test_export_table_keeps_readable_columns_on_small_screens():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'id="exportTimeStatus"' in html
    assert 'data-export-format="CSV"' in html
    assert 'data-export-format="Excel"' in html
    assert 'data-export-select-all' in html
    assert "<span>导出</span>" in html
    assert "<th>生成时间</th>" in html
    assert "<th>保存时间</th>" in html
    assert "<th>最近导出</th>" in html
    assert "exportLinks" in js
    assert "selectedExportIds" in js
    assert "data-export-id" in js
    assert "buildExportHref" in js
    assert "syncExportSelection" in js
    assert "lastExportedAt" in js
    assert "formatDateTime" in js
    assert "updateExportTimeStatus" in js
    assert "item.generated_at || item.created_at" in js
    assert "item.saved_at || item.created_at" in js
    assert "colspan=\"11\"" in html
    assert "colspan=\\\"11\\\"" in js

    assert ".table-panel {" in css
    table_panel_rule = re.search(r"\.table-panel\s*\{(?P<body>.*?)\n\}", css, re.S)
    assert table_panel_rule is not None
    assert "min-width: 0;" in table_panel_rule.group("body")

    wrap_rule = re.search(r"\.table-wrap\s*\{(?P<body>.*?)\n\}", css, re.S)
    assert wrap_rule is not None
    assert "min-width: 0;" in wrap_rule.group("body")
    assert "max-width: 100%;" in wrap_rule.group("body")

    assert ".table-wrap table" in css
    table_rule = re.search(r"\.table-wrap table\s*\{(?P<body>.*?)\n\}", css, re.S)
    assert table_rule is not None
    assert "min-width: 1240px;" in table_rule.group("body")
    assert ".export-check" in css
    assert ".export-time-status" in css
    assert ".time-cell" in css


def test_batch_generation_preserves_selected_topic_and_stable_switcher_layout():
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "getDefaultBatchActiveIndex" in js
    assert "options.activeIndex ?? getDefaultBatchActiveIndex(topics)" in js
    assert "normalizeGeneratedScript" in js
    assert "选择此脚本" in js
    assert "script-tabs-row" in js

    batch_rule = re.search(r"\.script-batch-strip\s*\{(?P<body>.*?)\n\}", css, re.S)
    assert batch_rule is not None
    assert "grid-template-columns: minmax(0, 1fr) auto;" in batch_rule.group("body")
    assert "grid-template-rows: auto auto;" in batch_rule.group("body")
    assert ".script-tabs-row" in css
    assert ".script-tabs-row {" in css


def test_task_card_summary_includes_content_type():
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert '["内容形式", currentTask.content_type]' in js


def test_topic_badges_have_hover_explanations():
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "getAngleHelp" in js
    assert "getDifficultyHelp" in js
    assert 'title="${escapeHtml(getAngleHelp(topic.angle))}"' in js
    assert 'title="${escapeHtml(getDifficultyHelp(topic.difficulty))}"' in js
    assert "低：常规素材即可完成" in js
    assert "中：需要补充证明材料" in js
    assert "高：需要更强素材" in js
