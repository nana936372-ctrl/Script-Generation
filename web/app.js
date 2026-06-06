const taskForm = document.querySelector("#taskForm");
const briefForm = document.querySelector("#briefForm");
const fillSampleButton = document.querySelector("#fillSampleButton");
const createTaskButton = document.querySelector("#createTaskButton");
const decomposeButton = document.querySelector("#decomposeButton");
const topicsButton = document.querySelector("#topicsButton");
const scriptButton = document.querySelector("#scriptButton");
const batchScriptButton = document.querySelector("#batchScriptButton");
const regenerateScriptButton = document.querySelector("#regenerateScriptButton");
const riskButton = document.querySelector("#riskButton");
const reviewButton = document.querySelector("#reviewButton");
const reviewRegenerateButton = document.querySelector("#reviewRegenerateButton");
const scoreQualityButton = document.querySelector("#scoreQualityButton");
const refreshLibraryButton = document.querySelector("#refreshLibraryButton");
const refreshFeedbackButton = document.querySelector("#refreshFeedbackButton");
const runtimeStatus = document.querySelector("#runtimeStatus");
const workflowStrip = document.querySelector("#workflowStrip");
const resultPanel = document.querySelector(".result-panel");

const taskResult = document.querySelector("#taskResult");
const decompositionResult = document.querySelector("#decompositionResult");
const topicsResult = document.querySelector("#topicsResult");
const scriptResult = document.querySelector("#scriptResult");
const qualityResult = document.querySelector("#qualityResult");
const riskResult = document.querySelector("#riskResult");
const versionResult = document.querySelector("#versionResult");
const libraryResult = document.querySelector("#libraryResult");
const feedbackResult = document.querySelector("#feedbackResult");
const scriptEditor = document.querySelector("#scriptEditor");
const reviewStatus = document.querySelector("#reviewStatus");
const reviewFlowHint = document.querySelector("#reviewFlowHint");
const reviewChecklist = document.querySelector("#reviewChecklist");
const changeSummary = document.querySelector("#changeSummary");
const savedTableBody = document.querySelector("#savedTableBody");
const exportTimeStatus = document.querySelector("#exportTimeStatus");
const exportLinks = document.querySelectorAll("[data-export-format]");
const exportSelectAll = document.querySelector("[data-export-select-all]");
const campaignForm = document.querySelector("#campaignForm");
const campaignScriptSelect = document.querySelector("#campaignScriptSelect");

let currentTask = null;
let currentBrief = null;
let currentDecomposition = null;
let currentTopics = [];
let selectedTopic = null;
let currentScripts = [];
let currentScriptIndex = -1;
let selectedScriptIndex = -1;
let currentScript = null;
let currentQualityScore = null;
let savedScripts = [];
let selectedExportIds = new Set();
let lastExportedAt = "";

const stepPages = {
  taskCard: document.querySelector("#taskCard"),
  decompositionCard: document.querySelector("#decompositionCard"),
  topicsCard: document.querySelector("#topicsCard"),
  scriptCard: document.querySelector("#scriptCard"),
  qualityCard: document.querySelector("#qualityCard"),
  riskCard: document.querySelector("#riskCard"),
  reviewCard: document.querySelector("#reviewCard"),
  libraryCard: document.querySelector("#libraryCard"),
  feedbackCard: document.querySelector("#feedbackCard")
};

const statusPageMap = {
  0: "taskCard",
  1: "taskCard",
  2: "decompositionCard",
  3: "topicsCard",
  4: "scriptCard",
  5: "qualityCard",
  6: "riskCard",
  7: "reviewCard",
  8: "reviewCard",
  9: "libraryCard",
  10: "feedbackCard"
};

const sampleTask = {
  task_name: "618 洁面乳短视频脚本",
  platform: "抖音",
  business_goal: "转化",
  content_type: "口播",
  script_count: "3",
  reviewer: "编导负责人"
};

const sampleBrief = {
  product_name: "氨基酸洁面乳",
  selling_points: "氨基酸表活，温和清洁，洗后不紧绷，适合日常早晚洁面",
  target_user: "18-30 岁油敏肌女生",
  usage_scenario: "早晚洁面、熬夜后出油、换季清洁",
  price_offer: "618 活动价，具体价格以页面为准",
  proof_material: "温和清洁相关检测报告、用户反馈截图",
  compliance_notes: "避免治疗、根治、彻底改善等表达；不承诺医学功效"
};

const reviewFlowMap = {
  "通过": {
    title: "通过 -> T8 版本保存 -> T9 导出",
    description: "脚本无需修改或仅做格式确认，保存后进入版本记录、优秀脚本库和导出表。",
    action: "save"
  },
  "小修后通过": {
    title: "小修后通过 -> 人工编辑 -> T8 版本保存 -> T9 导出",
    description: "编导在下方口播框完成小修，保存后沉淀为新版本，继续进入导出和复盘。",
    action: "save"
  },
  "退回 AI 重写": {
    title: "退回 AI 重写 -> 退回 T5 -> AI 重新生成",
    description: "当前脚本不进入交付，可先保存退回原因，再一键回到脚本生成区重新生成。",
    action: "regenerate"
  },
  "废弃": {
    title: "废弃 -> 记录原因 -> 停止进入交付",
    description: "该脚本不再进入优秀脚本库和导出，建议重新选题或重新生成。",
    action: "discard"
  }
};

fillSampleButton.addEventListener("click", () => {
  fillForm(taskForm, sampleTask);
  fillForm(briefForm, sampleBrief);
});

reviewStatus.addEventListener("change", () => {
  updateReviewFlowHint();
  updateReviewChecklist();
});

exportLinks.forEach((link) => {
  link.addEventListener("click", () => {
    link.href = buildExportHref(link.getAttribute("href") || "");
    lastExportedAt = new Date().toISOString();
    updateExportTimeStatus(link.dataset.exportFormat || "");
    renderSavedTable(savedScripts);
  });
});

savedTableBody.addEventListener("change", (event) => {
  const checkbox = event.target.closest("[data-export-id]");
  if (!checkbox) {
    return;
  }
  const scriptId = checkbox.dataset.exportId || "";
  if (!scriptId) {
    return;
  }
  if (checkbox.checked) {
    selectedExportIds.add(scriptId);
  } else {
    selectedExportIds.delete(scriptId);
  }
  syncExportSelection();
});

exportSelectAll?.addEventListener("change", () => {
  selectedExportIds = exportSelectAll.checked
    ? new Set(savedScripts.map((item) => String(item.id || "")).filter(Boolean))
    : new Set();
  renderSavedTable(savedScripts);
});

document.querySelectorAll("[data-step-target]").forEach((button) => {
  button.addEventListener("click", () => {
    setActiveStepPage(button.dataset.stepTarget, { scroll: true });
  });
});

workflowStrip.addEventListener("click", (event) => {
  const link = event.target.closest(".workflow-step");
  if (!link) {
    return;
  }

  const targetId = (link.getAttribute("href") || "").replace("#", "");
  if (stepPages[targetId]) {
    event.preventDefault();
    setActiveStepPage(targetId, { scroll: true });
  }
});

taskForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setButtonBusy(createTaskButton, true, "创建中...");
  try {
    const payload = Object.fromEntries(new FormData(taskForm).entries());
    const data = await postJson("/api/tasks", payload);
    currentTask = data.task;
    setResultContent(taskResult, renderKeyValues([
      ["任务名称", currentTask.task_name],
      ["业务目标", currentTask.business_goal],
      ["投放平台", currentTask.platform],
      ["内容形式", currentTask.content_type],
      ["脚本数量", currentTask.script_count],
      ["审核人", currentTask.reviewer || "未指定"]
    ]));
    syncTaskFieldsToBrief();
    decomposeButton.disabled = false;
    updateStatus("产品信息待录入", 1);
  } catch (error) {
    toast(error.message);
  } finally {
    setButtonBusy(createTaskButton, false, "创建任务");
  }
});

briefForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  currentBrief = collectBrief();
  setButtonBusy(decomposeButton, true, "拆解中...");
  try {
    const data = await postJson("/api/decompose", currentBrief);
    currentDecomposition = data.decomposition;
    setResultContent(decompositionResult, renderDecomposition(currentDecomposition));
    topicsButton.disabled = false;
    setActiveStepPage("decompositionCard");
    updateStatus("卖点拆解完成", 2);
  } catch (error) {
    toast(error.message);
  } finally {
    setButtonBusy(decomposeButton, false, "AI 卖点拆解");
  }
});

decompositionResult.addEventListener("click", (event) => {
  const insightButton = event.target.closest("[data-insight-carousel-action]");
  if (!insightButton) {
    return;
  }

  updateInsightCarousel(
    insightButton.closest(".insight-carousel"),
    insightButton.dataset.insightCarouselAction
  );
});

decompositionResult.addEventListener("change", (event) => {
  const select = event.target.closest("[data-carousel-page-size]");
  if (!select) {
    return;
  }

  updateInsightCarousel(select.closest(".insight-carousel"), "resize", Number(select.value));
});

topicsButton.addEventListener("click", async () => {
  if (!currentBrief || !currentDecomposition) {
    toast("请先完成卖点拆解");
    return;
  }
  setButtonBusy(topicsButton, true, "生成中...");
  try {
    const data = await postJson("/api/topics", {
      brief: currentBrief,
      decomposition: currentDecomposition
    });
    currentTopics = data.topics || [];
    selectedTopic = null;
    currentScripts = [];
    currentScriptIndex = -1;
    currentScript = null;
    scriptButton.disabled = true;
    batchScriptButton.disabled = !currentTopics.length;
    setResultContent(topicsResult, renderTopics(currentTopics));
    setActiveStepPage("topicsCard");
    updateStatus("选题池已生成", 3);
  } catch (error) {
    toast(error.message);
  } finally {
    setButtonBusy(topicsButton, false, "生成选题池");
  }
});

topicsResult.addEventListener("click", (event) => {
  const carouselButton = event.target.closest("[data-topic-carousel-action]");
  if (carouselButton) {
    updateTopicCarousel(
      carouselButton.closest(".topic-carousel"),
      carouselButton.dataset.topicCarouselAction
    );
    return;
  }

  const button = event.target.closest("[data-topic-index]");
  if (!button) {
    return;
  }
  const index = Number(button.dataset.topicIndex);
  selectedTopic = currentTopics[index];
  topicsResult.querySelectorAll(".topic-card").forEach((card) => card.classList.remove("selected"));
  topicsResult.querySelectorAll(".topic-select-button").forEach((item) => {
    item.textContent = "选择";
  });
  button.closest(".topic-card").classList.add("selected");
  button.textContent = "已选择";
  scriptButton.disabled = false;
  batchScriptButton.disabled = !currentTopics.length;
  updateReviewFlowHint();
  setActiveStepPage("topicsCard");
  updateStatus("已选择选题", 3);
});

topicsResult.addEventListener("change", (event) => {
  const select = event.target.closest("[data-carousel-page-size]");
  if (!select) {
    return;
  }

  updateTopicCarousel(select.closest(".topic-carousel"), "resize", Number(select.value));
});

scriptResult.addEventListener("click", (event) => {
  const chooseButton = event.target.closest("[data-choose-script]");
  if (chooseButton) {
    chooseCurrentScript();
    return;
  }

  const scriptSwitchButton = event.target.closest("[data-script-index]");
  if (scriptSwitchButton) {
    selectGeneratedScript(Number(scriptSwitchButton.dataset.scriptIndex));
    return;
  }

  const moduleButton = event.target.closest("[data-script-module-action]");
  if (!moduleButton) {
    return;
  }

  updateScriptModule(
    moduleButton.closest(".script-module-browser"),
    moduleButton.dataset.scriptModuleAction
  );
});

scriptResult.addEventListener("change", (event) => {
  const select = event.target.closest("[data-script-select]");
  if (!select) {
    return;
  }
  selectGeneratedScript(Number(select.value));
});

riskResult.addEventListener("click", (event) => {
  const button = event.target.closest("[data-risk-script-index]");
  if (!button) {
    return;
  }
  selectGeneratedScript(Number(button.dataset.riskScriptIndex), { activate: false, updateStatus: false });
  setResultContent(riskResult, renderRiskFindings(currentScript.risk_findings || [], currentScript));
  setActiveStepPage("riskCard");
});

riskResult.addEventListener("change", (event) => {
  const select = event.target.closest("[data-risk-script-select]");
  if (!select) {
    return;
  }
  selectGeneratedScript(Number(select.value), { activate: false, updateStatus: false });
  setResultContent(riskResult, renderRiskFindings(currentScript.risk_findings || [], currentScript));
  setActiveStepPage("riskCard");
});

scriptButton.addEventListener("click", async () => {
  await generateScriptFromSelectedTopic(scriptButton, {
    busyLabel: "生成中...",
    doneLabel: "AI 生成脚本",
    statusText: "脚本已生成"
  });
});

batchScriptButton.addEventListener("click", async () => {
  await generateBatchScripts();
});

regenerateScriptButton.addEventListener("click", async () => {
  if (currentScripts.length > 1) {
    await generateBatchScripts({
      button: regenerateScriptButton,
      busyLabel: "批量重写中...",
      doneLabel: "AI 重新生成",
      statusText: "脚本已批量重新生成",
      topics: getBatchTopicsForRegeneration(),
      activeIndex: currentScriptIndex
    });
    return;
  }

  await generateScriptFromSelectedTopic(regenerateScriptButton, {
    busyLabel: "重写中...",
    doneLabel: "AI 重新生成",
    statusText: "脚本已重新生成"
  });
});

reviewRegenerateButton.addEventListener("click", async () => {
  if (currentScripts.length > 1) {
    await regenerateCurrentScriptInBatch(reviewRegenerateButton, {
      busyLabel: "重写中...",
      doneLabel: "AI 重新生成",
      statusText: "已重写当前脚本，批量列表已保留"
    });
    return;
  }

  await generateScriptFromSelectedTopic(reviewRegenerateButton, {
    busyLabel: "重写中...",
    doneLabel: "AI 重新生成",
    statusText: "退回后已重新生成脚本"
  });
});

scoreQualityButton.addEventListener("click", () => {
  scoreCurrentScript({ activate: true, scroll: true });
});

riskButton.addEventListener("click", async () => {
  await scanGeneratedScriptRisks({ activate: true, manual: true });
});

reviewButton.addEventListener("click", async () => {
  if (!currentScript) {
    toast("请先生成脚本");
    return;
  }
  setButtonBusy(reviewButton, true, "保存中...");
  try {
    currentScript.spoken_script = scriptEditor.value;
    if (!Array.isArray(currentScript.risk_findings)) {
      await scanGeneratedScriptRisks({ onlyCurrent: true, silent: true });
      currentScript.spoken_script = scriptEditor.value || currentScript.spoken_script || "";
    }
    const data = await postJson("/api/review", {
      script: currentScript,
      review_status: reviewStatus.value,
      reviewer: currentTask?.reviewer || "编导",
      change_summary: changeSummary.value
    });
    currentScript = data.script;
    currentQualityScore = data.script.quality_score || currentQualityScore;
    syncCurrentScriptState();
    if (currentQualityScore) {
      setResultContent(qualityResult, renderQualityScore(currentQualityScore, currentScript));
    }
    setResultContent(versionResult, renderKeyValues([
      ["脚本 ID", data.script.id],
      ["版本号", `v${data.version.version_no}`],
      ["审核状态", data.script.review_status],
      ["流转动作", data.script.review_flow?.next_action || ""],
      ["修改说明", data.version.change_summary]
    ]));
    updateReviewChecklist();
    await loadSavedScripts();
    if (reviewStatus.value === "退回 AI 重写") {
      regenerateScriptButton.disabled = false;
      reviewRegenerateButton.disabled = false;
      setActiveStepPage("scriptCard");
      updateStatus("已退回 T5，可 AI 重新生成", 4);
    } else if (reviewStatus.value === "废弃") {
      setActiveStepPage("reviewCard");
      updateStatus("脚本已废弃，建议重新选题或生成", 7);
    } else {
      setActiveStepPage("libraryCard");
      updateStatus("脚本已沉淀到优秀脚本库", 9);
    }
  } catch (error) {
    toast(error.message);
  } finally {
    setButtonBusy(reviewButton, false, "保存审核版本");
  }
});

refreshLibraryButton.addEventListener("click", () => {
  loadSavedScripts()
    .then(() => {
      setActiveStepPage("libraryCard", { scroll: true });
      updateStatus("脚本库已刷新", 9);
    })
    .catch((error) => toast(error.message));
});

refreshFeedbackButton.addEventListener("click", () => {
  loadPerformanceInsights()
    .then(() => {
      setActiveStepPage("feedbackCard", { scroll: true });
      updateStatus("数据复盘已刷新", 10);
    })
    .catch((error) => toast(error.message));
});

campaignForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!campaignScriptSelect.value) {
    toast("请先保存脚本，再回传投放数据");
    return;
  }

  const submitButton = campaignForm.querySelector("button[type='submit']");
  setButtonBusy(submitButton, true, "回传中...");
  try {
    const payload = Object.fromEntries(new FormData(campaignForm).entries());
    const data = await postJson("/api/campaign-results", payload);
    setResultContent(feedbackResult, renderPerformanceFeedback(data.insights));
    setActiveStepPage("feedbackCard");
    updateStatus("数据已反向生成优化建议", 10);
  } catch (error) {
    toast(error.message);
  } finally {
    setButtonBusy(submitButton, false, "回传投放数据");
  }
});

async function loadSavedScripts() {
  const data = await getJson("/api/scripts");
  savedScripts = data.items || [];
  const savedIds = new Set(savedScripts.map((item) => String(item.id || "")).filter(Boolean));
  selectedExportIds = new Set([...selectedExportIds].filter((id) => savedIds.has(id)));
  renderSavedTable(savedScripts);
  renderScriptLibrary(savedScripts);
  updateCampaignScriptOptions(savedScripts);
}

async function loadPerformanceInsights() {
  const data = await getJson("/api/performance-insights");
  setResultContent(feedbackResult, renderPerformanceFeedback(data.insights));
}

function collectBrief() {
  const brief = Object.fromEntries(new FormData(briefForm).entries());
  const task = Object.fromEntries(new FormData(taskForm).entries());
  brief.task_id = currentTask?.id || "";
  brief.task_name = currentTask?.task_name || task.task_name || "";
  brief.reviewer = currentTask?.reviewer || task.reviewer || "";
  brief.platform = task.platform || "抖音";
  brief.business_goal = task.business_goal || "转化";
  brief.content_type = task.content_type || "口播";
  brief.script_count = task.script_count || "1";
  return brief;
}

function syncTaskFieldsToBrief() {
  const task = Object.fromEntries(new FormData(taskForm).entries());
  const targetUser = briefForm.elements.target_user;
  if (targetUser && !targetUser.value && task.target_user) {
    targetUser.value = task.target_user;
  }
}

function renderDecomposition(decomposition) {
  return renderInsightTiles([
    { title: "用户痛点", items: decomposition.pain_points, tone: "blue" },
    { title: "使用场景", items: decomposition.scenarios, tone: "green" },
    { title: "核心利益点", items: decomposition.benefits, tone: "blue" },
    { title: "证明材料", items: decomposition.proof_points, tone: "plain" },
    { title: "可用表达", items: decomposition.safe_expressions, tone: "green" },
    { title: "风险表达", items: decomposition.risky_expressions, tone: "warn" },
    { title: "待确认信息", items: decomposition.needs_confirmation, tone: "warn" }
  ]);
}

function renderTopics(topics) {
  if (!topics.length) {
    return "<div class=\"empty-mini\">暂无选题</div>";
  }
  const defaultPageSize = Math.min(2, topics.length);
  return `
    <div class="topic-carousel" data-active-index="0" data-page-index="0" data-per-page="${defaultPageSize}" style="${getCarouselLayoutStyle(defaultPageSize)}">
      <div class="carousel-toolbar">
        <button class="ghost-button compact-button" type="button" data-topic-carousel-action="prev">上一页</button>
        <div class="carousel-toolbar-center">
          <span class="carousel-count">1 / ${Math.ceil(topics.length / defaultPageSize)}</span>
          ${renderCarouselSizeOptions(defaultPageSize, [1, 2, 3, 4], topics.length)}
        </div>
        <button class="ghost-button compact-button" type="button" data-topic-carousel-action="next">下一页</button>
      </div>
      <div class="topic-carousel-window">
        ${topics.map((topic, index) => `
          <div class="topic-slide ${index < defaultPageSize ? "active" : ""}" ${index >= defaultPageSize ? "hidden" : ""} data-topic-slide="${index}">
            <div class="topic-card">
              <div class="topic-card-header">
                <div class="badge-row">
                  <span class="badge" title="${escapeHtml(getAngleHelp(topic.angle))}" data-tooltip="${escapeHtml(getAngleHelp(topic.angle))}">${escapeHtml(topic.angle || "选题")}</span>
                  <span class="badge warn" title="${escapeHtml(getDifficultyHelp(topic.difficulty))}" data-tooltip="${escapeHtml(getDifficultyHelp(topic.difficulty))}">难度：${escapeHtml(topic.difficulty || "")}</span>
                </div>
              </div>
              <div class="topic-card-body">
                <h3>${escapeHtml(topic.title || "")}</h3>
                <p><strong>Hook：</strong>${escapeHtml(topic.hook || "")}</p>
                <p><strong>推荐理由：</strong>${escapeHtml(topic.reason || "")}</p>
                <p><strong>风险提示：</strong>${escapeHtml(topic.risk_tip || "")}</p>
              </div>
              <div class="topic-card-footer">
                <button class="topic-select-button" type="button" data-topic-index="${index}">选择此选题</button>
              </div>
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

function renderScript(script) {
  return `
    <div class="script-summary-card">
      <div class="badge-row">
        <span class="badge">${escapeHtml(script.generation_mode === "ai" ? "DeepSeek" : "Demo")}</span>
        <span class="badge">${escapeHtml(script.platform || "")}</span>
        <span class="badge warn">${escapeHtml(script.ai_status || "已生成")}</span>
      </div>
      <h3>${escapeHtml(script.title || "未命名脚本")}</h3>
      <p><strong>Hook：</strong>${escapeHtml(script.hook || "")}</p>
    </div>
    ${renderScriptModules(script)}
  `;
}

function renderScriptWorkspace(scripts, activeIndex) {
  const activeScript = scripts[activeIndex] || scripts[0];
  if (!activeScript) {
    return "<div class=\"empty-mini\">暂无脚本</div>";
  }
  return `
    <div class="script-workspace-shell">
      ${renderScriptSwitcher(scripts, activeIndex)}
      <div class="script-detail-shell">
        ${renderScript(activeScript)}
      </div>
    </div>
  `;
}

function renderScriptSwitcher(scripts, activeIndex) {
  const activeScript = scripts[activeIndex] || {};
  const isSelected = selectedScriptIndex === activeIndex;
  const useCompactSelect = scripts.length > 8;
  return `
    <div class="script-batch-strip" aria-label="批量生成脚本列表">
      <div class="script-batch-meta">
        <span class="badge">${scripts.length > 1 ? "批量生成" : "脚本选择"}</span>
        <strong>${scripts.length} 条脚本</strong>
      </div>
      <button class="secondary-button compact-button script-choose-button ${isSelected ? "selected" : ""}" type="button" data-choose-script>
        ${isSelected ? "已选择此脚本" : "选择此脚本"}
      </button>
      <div class="script-tabs-row">
        ${scripts.length > 1 ? `
          ${useCompactSelect ? `
            <label class="script-select-wrap">
              <span>当前浏览</span>
              <select data-script-select aria-label="选择脚本">
                ${scripts.map((script, index) => `
                  <option value="${index}" ${index === activeIndex ? "selected" : ""}>
                    ${index + 1}. ${escapeHtml(script.title || `脚本 ${index + 1}`)}${index === selectedScriptIndex ? "（已选择）" : ""}
                  </option>
                `).join("")}
              </select>
            </label>
          ` : `
            <div class="script-tabs">
              ${scripts.map((script, index) => `
                <button
                  class="script-tab ${index === activeIndex ? "active" : ""} ${index === selectedScriptIndex ? "selected" : ""}"
                  type="button"
                  data-script-index="${index}"
                >
                  <span>${index + 1}</span>
                  ${escapeHtml(script.title || `脚本 ${index + 1}`)}
                </button>
              `).join("")}
            </div>
          `}
        ` : `
          <div class="script-active-title">${escapeHtml(activeScript.title || "当前脚本")}</div>
        `}
      </div>
    </div>
  `;
}

function setGeneratedScripts(scripts, activeIndex = 0) {
  currentScripts = scripts.filter(Boolean).map((script, index) => normalizeGeneratedScript(script, index));
  currentScriptIndex = currentScripts.length ? Math.max(0, Math.min(activeIndex, currentScripts.length - 1)) : -1;
  if (selectedScriptIndex >= currentScripts.length) {
    selectedScriptIndex = -1;
  }
  currentScript = currentScriptIndex >= 0 ? currentScripts[currentScriptIndex] : null;
  if (!currentScript) {
    return;
  }
  selectedTopic = currentScript.topic || selectedTopic;
  setResultContent(scriptResult, renderScriptWorkspace(currentScripts, currentScriptIndex));
  scriptEditor.value = currentScript.spoken_script || "";
  riskButton.disabled = false;
  reviewButton.disabled = false;
  scoreQualityButton.disabled = false;
  regenerateScriptButton.disabled = false;
  updateQualityPanelForCurrentScript();
  updateReviewFlowHint();
  updateReviewChecklist();
}

function normalizeGeneratedScript(script, index) {
  const topic = script.topic || currentTopics[index] || selectedTopic || {};
  const title = firstText(script.title, topic.title, `脚本 ${index + 1}`);
  const hook = firstText(script.hook, topic.hook, "先从用户真实痛点切入。");
  const spokenScript = firstText(
    script.spoken_script,
    `${hook}\n围绕“${firstText(topic.angle, "脚本方向")}”展开，讲清楚产品卖点和使用场景，再用已确认信息完成转化。`
  );
  return {
    ...script,
    title,
    hook,
    spoken_script: spokenScript,
    topic,
    storyboard: listOrFallback(script.storyboard, buildContextualStoryboardFallback(script, topic)),
    subtitle_points: listOrFallback(script.subtitle_points, [hook, title]),
    material_suggestions: listOrFallback(script.material_suggestions, ["产品实拍", "使用场景画面"]),
    risk_notes: listOrFallback(script.risk_notes, ["避免夸大、绝对化、医疗化表达"]),
    needs_confirmation: Array.isArray(script.needs_confirmation) ? script.needs_confirmation : []
  };
}

function firstText(...values) {
  for (const value of values) {
    const text = String(value || "").trim();
    if (text) {
      return text;
    }
  }
  return "";
}

function listOrFallback(value, fallback) {
  if (Array.isArray(value) && value.some(Boolean)) {
    return value.filter(Boolean);
  }
  if (value) {
    return [value];
  }
  return fallback;
}

function buildContextualStoryboardFallback(script = {}, topic = {}) {
  const context = contextPhrasesFromScript(script, topic);
  return [
    {
      time: "0-3s",
      visual: `字幕打出“${context.title}”，镜头切到“${context.pain}”的真实状态`,
      note: `用 Hook “${context.hook}”切入，先让目标用户看到自己的问题`
    },
    {
      time: "3-10s",
      visual: `${context.scenario}场景下展示${context.product}质地、起泡或冲洗细节`,
      note: `把“${context.sellingPoint}”转成可观察的使用过程`
    },
    {
      time: "10-20s",
      visual: `围绕“${context.benefit}”补充特写、字幕或已确认素材`,
      note: `证明材料使用“${context.proof}”，没有素材就保留待确认`
    },
    {
      time: "20-30s",
      visual: `回到${context.product}包装、页面信息或评论区反馈，字幕收束行动入口`,
      note: context.cta
    }
  ];
}

function contextPhrasesFromScript(script = {}, topic = {}) {
  const brief = currentBrief || {};
  const decomposition = script.decomposition_snapshot || currentDecomposition || {};
  return {
    title: compactPhrase(firstText(script.title, topic.title, `${brief.product_name || "产品"}脚本`), 22),
    hook: compactPhrase(firstText(script.hook, topic.hook, "先讲一个真实使用问题"), 28),
    pain: compactPhrase(firstListText(decomposition.pain_points, brief.target_user, topic.title, "目标用户痛点"), 28),
    scenario: compactPhrase(firstListText(decomposition.scenarios, brief.usage_scenario, "真实使用"), 20),
    benefit: compactPhrase(firstListText(decomposition.benefits, brief.selling_points, "核心卖点"), 28),
    proof: compactPhrase(firstListText(decomposition.proof_points, brief.proof_material, "已确认证明材料"), 24),
    product: compactPhrase(firstText(script.product_name, brief.product_name, "产品"), 16),
    sellingPoint: compactPhrase(firstText(brief.selling_points, script.selling_points, "核心卖点"), 32),
    cta: ctaNoteForGoal(brief.business_goal || script.business_goal || "转化")
  };
}

function firstListText(value, ...fallbacks) {
  if (Array.isArray(value)) {
    const found = value.map((item) => String(item || "").trim()).find(Boolean);
    if (found) {
      return found;
    }
  }
  return firstText(...fallbacks);
}

function compactPhrase(value, maxLength) {
  const text = firstText(value);
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, Math.max(1, maxLength - 1))}...`;
}

function ctaNoteForGoal(goal = "") {
  if (goal === "种草") {
    return "用真实体验和适合人群收尾，保留自然推荐语气";
  }
  if (goal === "直播引流") {
    return "自然提示直播间承接，不虚构价格、库存或开播时间";
  }
  if (goal === "品牌曝光") {
    return "强化品牌记忆点和关注动作，不做强硬购买催促";
  }
  return "给出明确但不过度承诺的页面或购买行动引导";
}

function mergeScoredScriptIntoSavedList({ script } = {}) {
  if (!script?.id) {
    return;
  }
  const scriptId = String(script.id);
  const existingIndex = savedScripts.findIndex((item) => String(item.id || "") === scriptId);
  if (existingIndex >= 0) {
    savedScripts = savedScripts.map((item, index) => (index === existingIndex ? { ...item, ...script } : item));
  } else {
    savedScripts = [...savedScripts, script];
  }
  renderSavedTable(savedScripts);
  renderScriptLibrary(savedScripts);
  updateCampaignScriptOptions(savedScripts);
}

async function refreshSavedScriptsAfterScoring() {
  try {
    await loadSavedScripts();
  } catch (error) {
    toast(`质量评分已保存，但脚本库刷新失败：${error.message}`);
  }
}

function selectGeneratedScript(index, options = {}) {
  if (!currentScripts[index]) {
    return;
  }
  persistEditorToCurrentScript();
  setGeneratedScripts(currentScripts, index);
  if (options.activate !== false) {
    setActiveStepPage("scriptCard");
  }
  if (options.updateStatus !== false) {
    updateStatus(`已切换到脚本 ${index + 1}`, 4);
  }
}

function syncCurrentScriptState() {
  if (currentScriptIndex >= 0 && currentScripts[currentScriptIndex]) {
    currentScripts[currentScriptIndex] = currentScript;
    setResultContent(scriptResult, renderScriptWorkspace(currentScripts, currentScriptIndex));
    updateReviewChecklist();
  }
}

function persistEditorToCurrentScript() {
  if (currentScript && currentScriptIndex >= 0 && currentScripts[currentScriptIndex]) {
    currentScript.spoken_script = scriptEditor.value || currentScript.spoken_script || "";
    currentScripts[currentScriptIndex] = currentScript;
  }
}

async function chooseCurrentScript() {
  if (!currentScript) {
    toast("请先生成脚本");
    return;
  }
  persistEditorToCurrentScript();
  selectedScriptIndex = currentScriptIndex;
  syncCurrentScriptState();
  await scoreCurrentScript({ activate: true, scroll: true });
}

function updateQualityPanelForCurrentScript() {
  currentQualityScore = currentScript?.quality_score || null;
  if (currentQualityScore) {
    setResultContent(qualityResult, renderQualityScore(currentQualityScore, currentScript));
    return;
  }
  setResultContent(qualityResult, `
    <div class="empty-mini">当前浏览：${escapeHtml(currentScript?.title || "未选择脚本")}。点击“选择此脚本”后生成该脚本评分。</div>
  `);
}

async function generateScriptFromSelectedTopic(button, labels = {}) {
  if (!selectedTopic) {
    toast("请先选择一个选题");
    return;
  }

  const busyLabel = labels.busyLabel || "生成中...";
  const doneLabel = labels.doneLabel || "AI 生成脚本";
  setButtonBusy(button, true, busyLabel);
  try {
    const data = await postJson("/api/script", {
      brief: currentBrief,
      decomposition: currentDecomposition,
      topic: selectedTopic
    });
    currentScript = data.script;
    currentQualityScore = null;
    selectedScriptIndex = -1;
    setGeneratedScripts([currentScript]);
    setActiveStepPage("scriptCard");
    updateStatus(labels.statusText || (currentScript.generation_mode === "ai" ? "DeepSeek 脚本已生成" : "演示脚本已生成"), 4);
    await scanGeneratedScriptRisks({ activate: false, silent: true });
  } catch (error) {
    toast(error.message);
  } finally {
    setButtonBusy(button, false, doneLabel);
  }
}

async function generateBatchScripts(options = {}) {
  const topics = options.topics || currentTopics;
  if (!topics.length) {
    toast("请先生成选题池");
    return;
  }

  const button = options.button || batchScriptButton;
  const busyLabel = options.busyLabel || "批量生成中...";
  const doneLabel = options.doneLabel || "批量生成脚本";
  setButtonBusy(button, true, busyLabel);
  try {
    const data = await postJson("/api/scripts/batch", {
      brief: currentBrief,
      decomposition: currentDecomposition,
      topics
    });
    selectedScriptIndex = -1;
    setGeneratedScripts(data.scripts || [], options.activeIndex ?? getDefaultBatchActiveIndex(topics));
    if (!currentScript) {
      toast("批量生成未返回脚本");
      return;
    }
    setActiveStepPage("scriptCard");
    await scanGeneratedScriptRisks({ activate: false, silent: true });
    updateStatus(options.statusText || `已批量生成 ${currentScripts.length} 条脚本并完成风险初筛`, 6);
    setActiveStepPage("scriptCard");
  } catch (error) {
    toast(error.message);
  } finally {
    setButtonBusy(button, false, doneLabel);
  }
}

function getDefaultBatchActiveIndex(topics) {
  if (!selectedTopic || !Array.isArray(topics)) {
    return 0;
  }
  const selectedId = String(selectedTopic.id || selectedTopic.source_topic_id || "");
  const selectedTitle = String(selectedTopic.title || "");
  const matchedIndex = topics.findIndex((topic) => {
    if (!topic) {
      return false;
    }
    const topicId = String(topic.id || topic.source_topic_id || "");
    return (selectedId && topicId === selectedId) || (selectedTitle && topic.title === selectedTitle);
  });
  return matchedIndex >= 0 ? matchedIndex : 0;
}

async function regenerateCurrentScriptInBatch(button, labels = {}) {
  if (!currentScript) {
    toast("请先生成脚本");
    return;
  }

  persistEditorToCurrentScript();
  const topic = currentScript.topic || selectedTopic;
  if (!topic) {
    toast("当前脚本缺少选题信息，无法重写");
    return;
  }

  const busyLabel = labels.busyLabel || "重写中...";
  const doneLabel = labels.doneLabel || "AI 重新生成";
  setButtonBusy(button, true, busyLabel);
  try {
    const data = await postJson("/api/script", {
      brief: currentBrief,
      decomposition: currentDecomposition,
      topic
    });
    currentScript = data.script;
    currentQualityScore = null;
    if (selectedScriptIndex === currentScriptIndex) {
      selectedScriptIndex = -1;
    }
    currentScripts[currentScriptIndex] = currentScript;
    setGeneratedScripts(currentScripts, currentScriptIndex);
    await scanGeneratedScriptRisks({ activate: false, silent: true, onlyCurrent: true });
    setActiveStepPage("scriptCard");
    updateStatus(labels.statusText || "当前脚本已重新生成", 4);
  } catch (error) {
    toast(error.message);
  } finally {
    setButtonBusy(button, false, doneLabel);
  }
}

function getBatchTopicsForRegeneration() {
  const scriptTopics = currentScripts
    .map((script) => script.topic)
    .filter((topic) => topic && typeof topic === "object");
  return scriptTopics.length === currentScripts.length ? scriptTopics : currentTopics;
}

async function scanGeneratedScriptRisks(options = {}) {
  if (!currentScript) {
    if (!options.silent) {
      toast("请先生成脚本");
    }
    return;
  }

  persistEditorToCurrentScript();
  const originalIndex = currentScriptIndex;
  const indexes = options.onlyCurrent
    ? [currentScriptIndex]
    : currentScripts.map((_, index) => index);

  if (options.manual) {
    setButtonBusy(riskButton, true, indexes.length > 1 ? "批量初筛中..." : "初筛中...");
  }

  try {
    for (const index of indexes) {
      const script = currentScripts[index];
      if (!script) {
        continue;
      }
      const data = await postJson("/api/risk-scan", { script });
      currentScripts[index] = { ...script, risk_findings: data.findings || [] };
    }
    currentScriptIndex = originalIndex;
    currentScript = currentScripts[currentScriptIndex];
    setGeneratedScripts(currentScripts, currentScriptIndex);
    setResultContent(riskResult, renderRiskFindings(currentScript.risk_findings || [], currentScript));
    updateReviewChecklist();
    if (options.activate) {
      setActiveStepPage("riskCard");
      updateStatus(indexes.length > 1 ? "批量风险词初筛完成" : "风险词初筛完成", 6);
    }
  } catch (error) {
    if (!options.silent) {
      toast(error.message);
    }
  } finally {
    if (options.manual) {
      setButtonBusy(riskButton, false, "风险词初筛");
    }
  }
}

function updateReviewFlowHint() {
  const flow = reviewFlowMap[reviewStatus.value] || reviewFlowMap["小修后通过"];
  const tone = flow.action === "regenerate" ? "warn" : flow.action === "discard" ? "danger" : "success";
  reviewFlowHint.className = `review-flow-hint ${tone}`;
  reviewFlowHint.innerHTML = `
    <strong>${escapeHtml(flow.title)}</strong>
    <span>${escapeHtml(flow.description)}</span>
  `;
  reviewRegenerateButton.disabled = flow.action !== "regenerate" || !selectedTopic;
}

function updateReviewChecklist() {
  if (!reviewChecklist) {
    return;
  }

  if (!currentScript) {
    reviewChecklist.innerHTML = "<div class=\"empty-mini\">生成脚本后显示交付前检查。</div>";
    return;
  }

  const flow = reviewFlowMap[reviewStatus.value] || reviewFlowMap["小修后通过"];
  const riskScanned = Array.isArray(currentScript.risk_findings);
  const riskFindings = riskScanned ? currentScript.risk_findings : [];
  const quality = currentScript.quality_score || currentQualityScore;
  const qualityScore = Number(quality?.total_score || 0);
  const selectedExplicitly = selectedScriptIndex === currentScriptIndex;
  const selectionLabel = selectedExplicitly ? "已选择" : currentScripts.length > 1 ? "当前浏览未确认" : "单条脚本";
  const selectionTone = selectedExplicitly || currentScripts.length <= 1 ? "ready" : "warn";
  const riskTone = !riskScanned ? "warn" : riskFindings.length ? "danger" : "ready";
  const qualityTone = qualityScore ? (quality.go_live_ready ? "ready" : "warn") : "warn";
  const flowTone = flow.action === "discard" ? "danger" : flow.action === "regenerate" ? "warn" : "ready";
  const notes = [];

  if (!selectedExplicitly && currentScripts.length > 1) {
    notes.push("批量脚本建议先在 T5 点击“选择此脚本”，再进入审核保存。");
  }
  if (!riskScanned) {
    notes.push("保存前会自动补跑当前脚本风险初筛。");
  } else if (riskFindings.length) {
    notes.push(`风险初筛命中 ${riskFindings.length} 处，保存前建议确认替换表达。`);
  }
  if (!qualityScore) {
    notes.push("点击“选择此脚本”会生成质量评分，便于判断是否进入版本保存。");
  }
  if (!notes.length) {
    notes.push("当前脚本已具备保存前的核心检查记录。");
  }

  reviewChecklist.innerHTML = `
    <section class="review-check-card">
      <div class="review-check-head">
        <span class="badge">交付前检查</span>
        <h4 title="${escapeHtml(currentScript.title || "当前脚本")}">${escapeHtml(currentScript.title || "当前脚本")}</h4>
      </div>
      <div class="review-check-grid">
        ${renderReviewCheckItem("脚本选择", selectionLabel, selectionTone, "批量生成时用于确认最终进入评分、审核和保存的脚本。")}
        ${renderReviewCheckItem("风险初筛", riskScanned ? `${riskFindings.length} 个命中` : "待初筛", riskTone, "基于风险词库扫描标题、Hook、口播、字幕重点和转化口播。")}
        ${renderReviewCheckItem("质量评分", qualityScore ? `${qualityScore} 分 / ${quality.grade || "-"} 级` : "待评分", qualityTone, "评分来自结构完整度、卖点转化、场景适配、风险控制和执行可落地性。")}
        ${renderReviewCheckItem("审核动作", reviewStatus.value, flowTone, flow.description)}
      </div>
      <ul class="review-check-notes">
        ${notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}
      </ul>
    </section>
  `;
}

function renderReviewCheckItem(label, value, tone, description) {
  return `
    <div class="review-check-item ${tone}" title="${escapeHtml(description)}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

async function scoreCurrentScript(options = {}) {
  if (!currentScript) {
    toast("请先生成脚本");
    return;
  }

  setButtonBusy(scoreQualityButton, true, "评分中...");
  try {
    currentScript.spoken_script = scriptEditor.value || currentScript.spoken_script || "";
    const data = await postJson("/api/quality-score", { script: currentScript });
    currentQualityScore = data.quality_score;
    const savedScript = data.script;
    currentScript = {
      ...currentScript,
      ...(savedScript || {}),
      quality_score: currentQualityScore
    };
    syncCurrentScriptState();
    setResultContent(qualityResult, renderQualityScore(currentQualityScore, currentScript));
    mergeScoredScriptIntoSavedList({ script: savedScript || currentScript });
    await refreshSavedScriptsAfterScoring();
    if (options.updateProgress !== false) {
      updateStatus("质量评分完成", 5);
    }
    if (options.activate !== false) {
      setActiveStepPage("qualityCard", { scroll: Boolean(options.scroll) });
    }
  } catch (error) {
    if (!options.silent) {
      toast(error.message);
    }
  } finally {
    setButtonBusy(scoreQualityButton, false, "重新评分");
  }
}

function renderQualityScore(score, script = currentScript) {
  if (!score) {
    return "<div class=\"empty-mini\">暂无评分结果</div>";
  }

  const total = Number(score.total_score || 0);
  const dimensions = score.dimensions || [];
  const riskFindings = score.risk_findings || [];
  const suggestions = score.suggestions || [];
  const readyText = score.go_live_ready ? "可进入审核与小规模投放" : "建议优化后再投放";

  return `
    <div class="quality-shell">
      <section class="quality-context">
        <span class="badge">当前脚本</span>
        <h3>${escapeHtml(script?.title || "未命名脚本")}</h3>
        <p><strong>Hook：</strong>${escapeHtml(script?.hook || "暂无 Hook")}</p>
      </section>
      <section class="score-total ${score.go_live_ready ? "ready" : "hold"}">
        <span>总分</span>
        <strong>${escapeHtml(total)}</strong>
        <em>${escapeHtml(score.grade || "-")} 级</em>
        <p>${escapeHtml(readyText)}</p>
      </section>
      <div class="score-grid">
        ${dimensions.map((item) => {
          const percent = Math.max(0, Math.min(100, Math.round((Number(item.score || 0) / Number(item.max_score || 20)) * 100)));
          return `
            <article class="score-card">
              <div>
                <h4>${escapeHtml(item.label)}</h4>
                <span>${escapeHtml(item.score)} / ${escapeHtml(item.max_score || 20)}</span>
              </div>
              <div class="score-bar" aria-hidden="true"><span style="width: ${percent}%"></span></div>
              <p>${escapeHtml(item.rationale || "")}</p>
            </article>
          `;
        }).join("")}
      </div>
      <section class="quality-notes">
        <div>
          <h4>优化建议</h4>
          ${renderCompactList(suggestions)}
        </div>
        <div>
          <h4>风险命中</h4>
          ${riskFindings.length ? renderCompactList(riskFindings.map((item) => `${item.word}：${item.category}，建议替换为“${item.replacement}”`)) : "<p class=\"muted\">未命中明显风险表达</p>"}
        </div>
      </section>
    </div>
  `;
}

function renderInsightTiles(sections) {
  const slides = sections
    .filter((section) => (section.items || []).length)
    .map((section, index) => `
      <section class="insight-slide ${index === 0 ? "active" : ""}" data-insight-slide="${index}">
        <div class="insight-tile ${section.tone || ""}">
          <div class="module-kicker">
            <span class="badge" data-tooltip="${escapeHtml(getInsightHelp(section.title))}">${escapeHtml(section.title)}</span>
            <span class="muted">${(section.items || []).length} 条</span>
          </div>
          <h3>${escapeHtml(section.title)}</h3>
          <div class="insight-items">
            ${(section.items || []).map((item, itemIndex) => `
              <div class="insight-item">
                <span>${itemIndex + 1}</span>
                <p>${escapeHtml(String(item))}</p>
              </div>
            `).join("")}
          </div>
        </div>
      </section>
    `);

  if (!slides.length) {
    return "<div class=\"empty-mini\">暂无拆解内容</div>";
  }

  const defaultPageSize = Math.min(4, slides.length);
  return `
    <div class="insight-carousel" data-active-index="0" data-page-index="0" data-per-page="${defaultPageSize}" style="${getCarouselLayoutStyle(defaultPageSize)}">
      <div class="carousel-toolbar">
        <button class="ghost-button compact-button" type="button" data-insight-carousel-action="prev">上一页</button>
        <div class="carousel-toolbar-center">
          <span class="carousel-count">1 / ${Math.ceil(slides.length / defaultPageSize)}</span>
          ${renderCarouselSizeOptions(defaultPageSize, [1, 2, 4, 6], slides.length)}
        </div>
        <button class="ghost-button compact-button" type="button" data-insight-carousel-action="next">下一页</button>
      </div>
      <div class="insight-carousel-window">
        ${slides.map((slide, index) => (index < defaultPageSize ? slide : slide.replace("<section ", "<section hidden "))).join("")}
      </div>
    </div>
  `;
}

function updateInsightCarousel(carousel, action, pageSize) {
  updatePagedCarousel(carousel, action, pageSize, {
    slideSelector: "[data-insight-slide]",
    windowSelector: ".insight-carousel-window"
  });
}

function updateTopicCarousel(carousel, action, pageSize) {
  updatePagedCarousel(carousel, action, pageSize, {
    slideSelector: "[data-topic-slide]",
    windowSelector: ".topic-carousel-window"
  });
}

function renderScriptModules(script) {
  const modules = [
    {
      title: "口播脚本",
      body: `<div class="script-copy">${escapeHtml(script.spoken_script || "暂无口播脚本").replaceAll("\n", "<br>")}</div>`
    },
    {
      title: "分镜建议",
      body: renderStoryboardCards(script.storyboard)
    },
    {
      title: "字幕重点",
      body: renderModuleItems(script.subtitle_points)
    },
    {
      title: "素材建议",
      body: renderModuleItems(script.material_suggestions)
    },
    {
      title: "转化口播",
      body: `<div class="script-callout">${escapeHtml(script.conversion_cta || "暂无转化口播")}</div>`
    },
    {
      title: "合规提醒",
      body: renderModuleItems(script.risk_notes, "warn")
    },
    {
      title: "待确认信息",
      body: renderModuleItems(script.needs_confirmation, "warn")
    }
  ];

  return `
    <div class="script-module-browser" data-active-index="0">
      <div class="script-module-nav">
        <button class="ghost-button compact-button" type="button" data-script-module-action="prev">上一个模块</button>
        <div class="script-module-current">
          <span class="carousel-count">1 / ${modules.length}</span>
          <strong>${escapeHtml(modules[0].title)}</strong>
        </div>
        <button class="ghost-button compact-button" type="button" data-script-module-action="next">下一个模块</button>
      </div>
      <div class="script-module-stage">
        ${modules.map((module, index) => `
          <section class="script-module ${index === 0 ? "active" : ""}" data-script-module="${index}" data-module-title="${escapeHtml(module.title)}">
            <h3>${escapeHtml(module.title)}</h3>
            ${module.body}
          </section>
        `).join("")}
      </div>
    </div>
  `;
}

function updateScriptModule(browser, action) {
  if (!browser) {
    return;
  }
  const modules = Array.from(browser.querySelectorAll("[data-script-module]"));
  if (!modules.length) {
    return;
  }

  const currentIndex = Number(browser.dataset.activeIndex || 0);
  const nextIndex = action === "prev"
    ? (currentIndex - 1 + modules.length) % modules.length
    : (currentIndex + 1) % modules.length;

  browser.dataset.activeIndex = String(nextIndex);
  modules.forEach((module, index) => {
    module.classList.toggle("active", index === nextIndex);
  });

  const count = browser.querySelector(".carousel-count");
  const title = browser.querySelector(".script-module-current strong");
  if (count) {
    count.textContent = `${nextIndex + 1} / ${modules.length}`;
  }
  if (title) {
    title.textContent = modules[nextIndex].dataset.moduleTitle || "";
  }
}

function updatePagedCarousel(carousel, action, pageSize, config) {
  if (!carousel) {
    return;
  }
  const slides = Array.from(carousel.querySelectorAll(config.slideSelector));
  if (!slides.length) {
    return;
  }

  const nextPageSize = Math.max(1, Math.min(slides.length, Number(pageSize || carousel.dataset.perPage || 1)));
  const pageCount = Math.max(1, Math.ceil(slides.length / nextPageSize));
  let pageIndex = Number(carousel.dataset.pageIndex || 0);

  if (action === "resize") {
    pageIndex = 0;
  } else if (action === "prev") {
    pageIndex = (pageIndex - 1 + pageCount) % pageCount;
  } else {
    pageIndex = (pageIndex + 1) % pageCount;
  }

  carousel.dataset.perPage = String(nextPageSize);
  carousel.dataset.pageIndex = String(pageIndex);
  carousel.dataset.activeIndex = String(pageIndex);
  carousel.setAttribute("style", getCarouselLayoutStyle(nextPageSize));
  applyPagedCarousel(carousel, slides, config.windowSelector);
}

function applyPagedCarousel(carousel, slides, windowSelector) {
  const perPage = Math.max(1, Number(carousel.dataset.perPage || 1));
  const pageIndex = Math.max(0, Number(carousel.dataset.pageIndex || 0));
  const pageCount = Math.max(1, Math.ceil(slides.length / perPage));
  const startIndex = pageIndex * perPage;
  const endIndex = startIndex + perPage;

  slides.forEach((slide, index) => {
    const visible = index >= startIndex && index < endIndex;
    slide.hidden = !visible;
    slide.classList.toggle("active", visible);
  });

  const count = carousel.querySelector(".carousel-count");
  if (count) {
    count.textContent = `${pageIndex + 1} / ${pageCount}`;
  }

  const windowNode = carousel.querySelector(windowSelector);
  if (windowNode) {
    windowNode.scrollTo({ left: 0, top: 0, behavior: "smooth" });
  }
}

function renderCarouselSizeOptions(current, options, total) {
  const availableOptions = options.filter((value) => value <= total);
  const optionList = availableOptions.includes(current)
    ? availableOptions
    : [current, ...availableOptions].sort((a, b) => a - b);
  return `
    <label class="carousel-page-size">
      <span>每页</span>
      <select data-carousel-page-size>
        ${optionList.map((value) => `<option value="${value}" ${value === current ? "selected" : ""}>${value}</option>`).join("")}
      </select>
    </label>
  `;
}

function getCarouselLayoutStyle(pageSize) {
  const size = Math.max(1, Number(pageSize || 1));
  const rows = size <= 3 ? 1 : 2;
  const columns = size <= 3 ? size : Math.ceil(size / 2);
  return `--page-columns: ${columns}; --page-rows: ${rows};`;
}

function getAngleHelp(angle = "") {
  const normalized = String(angle || "").trim();
  const descriptions = {
    "痛点型": "蓝色标签：选题切入角度。痛点型先抓用户困扰，再转入产品解决方案。",
    "测评型": "蓝色标签：选题切入角度。测评型用体验、对比或实测增强可信度。",
    "场景型": "蓝色标签：选题切入角度。场景型围绕具体使用时机组织脚本。",
    "直播引流型": "蓝色标签：选题切入角度。直播引流型强调适合人群、活动信息和转化入口。",
    "补充型": "蓝色标签：选题切入角度。补充型用于扩展同一任务下的备选表达。"
  };
  return descriptions[normalized] || "蓝色标签：表示选题角度或内容模块类型，用于说明这张卡片从哪里切入。";
}

function getDifficultyHelp(difficulty = "") {
  const normalized = String(difficulty || "").trim();
  const descriptions = {
    "低": "低：常规素材即可完成，脚本结构直接，风险低。",
    "中": "中：需要补充证明材料、对比素材或更明确的场景设计。",
    "高": "高：需要更强素材、复杂拍摄或严格合规确认。"
  };
  return descriptions[normalized] || "黄色标签：表示执行难度，依据素材要求、拍摄复杂度、合规风险和信息确认成本综合判断。";
}

function getInsightHelp(title = "") {
  const descriptions = {
    "用户痛点": "蓝色标签：用户尚未被满足的问题，适合用来设计 Hook。",
    "使用场景": "蓝色标签：用户可能触发需求的时间、地点或状态。",
    "核心利益点": "蓝色标签：产品能给用户带来的主要价值。",
    "证明材料": "蓝色标签：支撑卖点可信度的报告、截图、背书或实证素材。",
    "可用表达": "蓝色标签：相对安全、可直接进入脚本的表达方向。",
    "风险表达": "黄色标签：可能涉及夸大、医疗化、绝对化或价格误导的表达。",
    "待确认信息": "黄色标签：生成前后都需要人工确认的价格、证明、合规或活动信息。"
  };
  return descriptions[String(title || "").trim()] || "标签说明：用于解释当前模块的内容类型和使用方式。";
}

function renderStoryboardCards(items = []) {
  if (!items.length) {
    return "<p class=\"muted\">暂无分镜建议</p>";
  }
  return `
    <div class="storyboard-grid">
      ${items.map((item) => `
        <article class="storyboard-card">
          <span class="badge">${escapeHtml(item.time || "")}</span>
          <h4>${escapeHtml(item.visual || String(item))}</h4>
          <p>${escapeHtml(item.note || "")}</p>
        </article>
      `).join("")}
    </div>
  `;
}

function renderModuleItems(items = [], tone = "") {
  const cards = (items || []).map((item, index) => `
    <div class="module-note ${tone}">
      <span>${index + 1}</span>
      <p>${escapeHtml(String(item))}</p>
    </div>
  `).join("");

  return `<div class="module-note-grid">${cards || "<p class=\"muted\">暂无</p>"}</div>`;
}

function renderRiskFindings(items = [], script = {}) {
  const findings = items || [];
  const scriptLabel = currentScriptIndex >= 0 ? `脚本 ${currentScriptIndex + 1}` : "当前脚本";
  return `
    <div class="risk-shell">
      ${renderRiskRulePanel()}
      ${currentScripts.length > 1 ? renderRiskBatchOverview(currentScripts, currentScriptIndex) : ""}
      <section class="risk-detail-card ${findings.length ? "has-risk" : "clear"}">
        <div class="risk-detail-head">
          <div>
            <span class="badge ${findings.length ? "risk" : ""}">${findings.length ? "命中风险词" : "未命中明显风险词"}</span>
            <h3>${escapeHtml(script.title || scriptLabel)}</h3>
          </div>
          <strong>${findings.length} 条</strong>
        </div>
        ${renderRiskFindingRows(findings)}
        <section class="risk-copy-panel ${findings.length ? "danger" : "clear"}">
          <div class="risk-copy-toolbar">
            <h4>脚本定位</h4>
            <span>扫描标题、Hook、口播、字幕重点、转化口播</span>
          </div>
          <div class="risk-marked-copy">${findings.length ? highlightRiskWords(script.spoken_script || "", findings) : escapeHtml(script.spoken_script || "暂无口播脚本")}</div>
        </section>
      </section>
    </div>
  `;
}

function renderRiskRulePanel() {
  const rules = [
    {
      category: "绝对化表达",
      examples: "如“最好”“第一”",
      note: "避免绝对排名、唯一性或不可验证的领先表述。"
    },
    {
      category: "夸大承诺",
      examples: "如“永久”“彻底”“立刻见效”",
      note: "避免承诺结果或暗示短时间必然产生效果。"
    },
    {
      category: "医疗化表达",
      examples: "如“根治”“治疗”“消炎”",
      note: "非药品或非医疗服务不应暗示医学功效。"
    },
    {
      category: "价格误导",
      examples: "如“全网最低”“错过不再有”",
      note: "活动和价格表达需要以页面规则或真实证明为准。"
    },
    {
      category: "贬损表达",
      examples: "贬损外貌或状态的攻击性描述",
      note: "避免通过羞辱用户制造焦虑，优先使用中性场景。"
    }
  ];

  return `
    <section class="risk-rule-panel">
      <div class="risk-rule-head">
        <span class="badge">筛选依据</span>
        <p>风险词初筛基于内置合规词库做精确命中，扫描标题、Hook、口播、字幕重点、转化口播；命中后展示分类、建议替换、位置和片段。未命中不等于完全合规，仍需人工复核。</p>
      </div>
      <div class="risk-rule-grid">
        ${rules.map((rule) => `
          <article class="risk-rule-item" title="${escapeHtml(rule.note)}" data-tooltip="${escapeHtml(rule.note)}">
            <strong>${escapeHtml(rule.category)}</strong>
            <span>${escapeHtml(rule.examples)}</span>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderRiskBatchOverview(scripts = [], activeIndex = 0) {
  const totalFindings = scripts.reduce((sum, script) => sum + getScriptRiskCount(script), 0);
  return `
    <section class="risk-batch-overview">
      <div class="risk-batch-head">
        <div>
          <span class="badge">批量概览</span>
          <strong>${scripts.length} 条脚本 · ${totalFindings} 个命中</strong>
        </div>
        <label class="risk-script-selector">
          <span>查看脚本</span>
          <select data-risk-script-select aria-label="选择风险初筛脚本">
            ${scripts.map((script, index) => `
              <option value="${index}" ${index === activeIndex ? "selected" : ""}>
                ${index + 1}. ${escapeHtml(script.title || `脚本 ${index + 1}`)} · ${getScriptRiskCount(script)} 个命中
              </option>
            `).join("")}
          </select>
        </label>
      </div>
      <div class="risk-script-list">
        ${scripts.map((script, index) => {
          const count = getScriptRiskCount(script);
          return `
            <button class="risk-script-row ${index === activeIndex ? "active" : ""}" type="button" data-risk-script-index="${index}">
              <span>${index + 1}</span>
              <strong title="${escapeHtml(script.title || `脚本 ${index + 1}`)}">${escapeHtml(script.title || `脚本 ${index + 1}`)}</strong>
              <em class="risk-count-pill ${count ? "" : "clear"}">${count ? `${count} 个` : "0"}</em>
            </button>
          `;
        }).join("")}
      </div>
    </section>
  `;
}

function renderRiskFindingRows(items = []) {
  if (!items.length) {
    return `
      <div class="risk-empty-check">
        当前脚本在内置词库中没有命中明显风险词。上线前仍建议按品牌、平台和活动规则做人工确认。
      </div>
    `;
  }
  return `
    <div class="risk-finding-list">
      ${items.map((item) => `
        <article class="risk-finding-row ${item.severity === "high" ? "high" : "medium"}">
          <div>
            <strong>${escapeHtml(item.word || "")}</strong>
            <span>${escapeHtml(item.category || "风险表达")}</span>
          </div>
          <em>${item.position !== undefined ? `位置 ${escapeHtml(Number(item.position) + 1)}` : "位置待确认"}</em>
          <p>建议改为：${escapeHtml(item.replacement || "更中性、可验证的表达")}</p>
          ${item.snippet ? `<small>${escapeHtml(item.snippet)}</small>` : ""}
        </article>
      `).join("")}
    </div>
  `;
}

function getScriptRiskCount(script = {}) {
  return Array.isArray(script.risk_findings) ? script.risk_findings.length : 0;
}

function highlightRiskWords(text, findings = []) {
  const escaped = escapeHtml(text || "暂无口播脚本");
  const words = [...new Set(findings.map((item) => item.word).filter(Boolean))]
    .sort((a, b) => b.length - a.length);
  if (!words.length) {
    return escaped;
  }
  const pattern = new RegExp(words.map(escapeRegExp).join("|"), "g");
  return escaped.replace(pattern, (match) => `<mark>${match}</mark>`);
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function renderSavedTable(items) {
  if (!items.length) {
    savedTableBody.innerHTML = "<tr><td colspan=\"11\" class=\"muted\">暂无保存脚本</td></tr>";
    syncExportSelection();
    return;
  }
  savedTableBody.innerHTML = items.slice().reverse().map((item) => {
    const scriptId = String(item.id || "");
    return `
      <tr>
        <td class="export-check">
          <input
            type="checkbox"
            data-export-id="${escapeHtml(scriptId)}"
            aria-label="选择导出 ${escapeHtml(item.title || scriptId || "脚本")}"
            ${scriptId ? "" : "disabled"}
            ${scriptId && selectedExportIds.has(scriptId) ? "checked" : ""}
          />
        </td>
        <td>${escapeHtml(item.product_name || "")}</td>
        <td>${escapeHtml(item.platform || "")}</td>
        <td>${escapeHtml(item.title || "")}</td>
        <td>${escapeHtml(item.hook || "")}</td>
        <td class="time-cell">${escapeHtml(formatDateTime(item.generated_at || item.created_at))}</td>
        <td class="time-cell">${escapeHtml(formatDateTime(item.saved_at || item.created_at))}</td>
        <td>${renderQualityCell(item)}</td>
        <td>${escapeHtml(item.review_status || "")}</td>
        <td>${item.version_no ? `v${escapeHtml(item.version_no)}` : escapeHtml(item.id || "")}</td>
        <td class="time-cell">${escapeHtml(lastExportedAt ? formatDateTime(lastExportedAt) : "暂无")}</td>
      </tr>
    `;
  }).join("");
  syncExportSelection();
}

function syncExportSelection() {
  const availableIds = savedScripts.map((item) => String(item.id || "")).filter(Boolean);
  const selectedCount = availableIds.filter((id) => selectedExportIds.has(id)).length;
  if (exportSelectAll) {
    exportSelectAll.checked = availableIds.length > 0 && selectedCount === availableIds.length;
    exportSelectAll.indeterminate = selectedCount > 0 && selectedCount < availableIds.length;
  }
}

function buildExportHref(baseHref) {
  const cleanHref = baseHref.split("?")[0];
  const ids = [...new Set(
    savedScripts
      .map((item) => String(item.id || ""))
      .filter((id) => id && selectedExportIds.has(id))
  )];
  if (!ids.length) {
    return cleanHref;
  }
  const params = new URLSearchParams({ ids: ids.join(",") });
  return `${cleanHref}?${params.toString()}`;
}

function updateExportTimeStatus(format = "") {
  if (!exportTimeStatus) {
    return;
  }
  if (!lastExportedAt) {
    exportTimeStatus.textContent = "最近导出时间：暂无";
    return;
  }
  const prefix = format ? `${format} 导出时间` : "最近导出时间";
  exportTimeStatus.textContent = `${prefix}：${formatDateTime(lastExportedAt)}`;
}

function formatDateTime(value) {
  if (!value) {
    return "暂无";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  }).format(date);
}

function renderQualityCell(item) {
  const score = (item.quality_score || {}).total_score;
  const grade = (item.quality_score || {}).grade;
  const scoreLabel = "质量分";
  const label = score ? `质量总分：${score}${grade ? ` / ${grade}` : ""}` : "质量总分待评分";
  return `<span class="table-score" aria-label="${escapeHtml(scoreLabel)}" title="${escapeHtml(label)}">${score ? escapeHtml(score) : "待评"}</span>`;
}

function renderScriptLibrary(items = []) {
  const qualified = items
    .filter((item) => item.review_status !== "废弃")
    .slice()
    .sort((a, b) => Number((b.quality_score || {}).total_score || 0) - Number((a.quality_score || {}).total_score || 0));

  if (!qualified.length) {
    setResultContent(libraryResult, `
      <div class="library-empty">
        <h3>还没有可复用脚本</h3>
        <p>保存审核版本后，系统会带着评分、Hook、选题角度和转化口播一起入库。</p>
      </div>
    `);
    return;
  }

  setResultContent(libraryResult, `
    <div class="library-list">
      ${qualified.map((item) => {
        const score = (item.quality_score || {}).total_score;
        return `
          <article class="library-item">
            <div class="module-kicker">
              <span class="badge">${escapeHtml(item.platform || "平台")}</span>
              <span class="score-pill">${score ? `${escapeHtml(score)} 分` : "待评分"}</span>
            </div>
            <h3>${escapeHtml(item.title || "未命名脚本")}</h3>
            <p><strong>Hook：</strong>${escapeHtml(item.hook || "暂无 Hook")}</p>
            <p><strong>可复用结构：</strong>${escapeHtml(buildReusablePattern(item))}</p>
          </article>
        `;
      }).join("")}
      <article class="library-item library-guide">
        <div class="module-kicker">
          <span class="badge">入库标准</span>
          <span class="score-pill">75+ 分</span>
        </div>
        <h3>沉淀为可复用模板</h3>
        <p><strong>保留：</strong>高分 Hook、选题角度、分镜结构和转化口播。</p>
        <p><strong>复用：</strong>下一轮生成时优先参考高 ROI 脚本，低表现结构进入改写清单。</p>
      </article>
    </div>
  `);
}

function updateCampaignScriptOptions(items = []) {
  const button = campaignForm.querySelector("button[type='submit']");
  if (!items.length) {
    campaignScriptSelect.innerHTML = "<option value=\"\">暂无可回传脚本</option>";
    button.disabled = true;
    return;
  }

  const selectedId = currentScript?.id || items[items.length - 1]?.id || "";
  campaignScriptSelect.innerHTML = items.slice().reverse().map((item) => `
    <option value="${escapeHtml(item.id || "")}" ${item.id === selectedId ? "selected" : ""}>
      ${escapeHtml(item.title || item.id || "未命名脚本")}
    </option>
  `).join("");
  button.disabled = false;
}

function renderPerformanceFeedback(insights) {
  if (!insights || !insights.sample_size) {
    return `
      <div class="feedback-grid">
        <section class="feedback-card">
          <h3>数据样本不足</h3>
          <p>先保存审核脚本，再回传曝光、完播、点击、转化和 ROI，系统会反向总结高表现结构。</p>
        </section>
        <section class="feedback-card">
          <h3>复盘会输出什么</h3>
          ${renderCompactList(["高表现 Hook 和选题角度", "低表现脚本的改写方向", "下一版脚本的 CTA 与分镜优化建议"])}
        </section>
      </div>
    `;
  }

  const summary = insights.metric_summary || {};
  const best = insights.best_script || {};
  return `
    <div class="feedback-grid">
      <section class="feedback-card highlight">
        <span class="badge">样本 ${escapeHtml(insights.sample_size)} 条</span>
        <h3>${escapeHtml(best.title || "最佳脚本")}</h3>
        <p><strong>高表现 Hook：</strong>${escapeHtml(best.hook || "暂无 Hook")}</p>
        <div class="metric-summary">
          ${renderMetric("3 秒播放", summary.three_sec_rate, "rate")}
          ${renderMetric("完播", summary.completion_rate, "rate")}
          ${renderMetric("点击", summary.click_rate, "rate")}
          ${renderMetric("转化", summary.conversion_rate, "rate")}
          ${renderMetric("ROI", summary.roi, "number")}
        </div>
      </section>
      <section class="feedback-card">
        <h3>可沉淀模式</h3>
        ${renderCompactList(insights.top_patterns || [])}
      </section>
      <section class="feedback-card">
        <h3>薄弱模式</h3>
        ${renderCompactList(insights.weak_patterns || [])}
      </section>
      <section class="feedback-card">
        <h3>下一版优化</h3>
        ${renderCompactList(insights.recommendations || [])}
      </section>
    </div>
  `;
}

function renderMetric(label, value, type) {
  const numeric = Number(value || 0);
  const text = type === "rate" ? `${(numeric * 100).toFixed(1)}%` : numeric.toFixed(2);
  return `
    <div>
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(text)}</strong>
    </div>
  `;
}

function renderCompactList(items = []) {
  const rows = (items || []).map((item) => `<li>${escapeHtml(String(item))}</li>`).join("");
  return `<ul class="compact-list">${rows || "<li class=\"muted\">暂无</li>"}</ul>`;
}

function buildReusablePattern(item) {
  const topic = item.topic || {};
  const angle = topic.angle || "选题角度";
  const storyboard = (item.storyboard || []).map((row) => row.note || row.visual).filter(Boolean).slice(0, 2).join(" / ");
  return `${angle}切入，先 Hook 再卖点证明，最后 CTA${storyboard ? `；分镜重点：${storyboard}` : ""}`;
}

function renderListBlock(title, items = []) {
  const rows = (items || []).map((item) => `<li>${escapeHtml(String(item))}</li>`).join("");
  return `
    <div class="result-block">
      <h3>${title}</h3>
      <ul>${rows || "<li class=\"muted\">暂无</li>"}</ul>
    </div>
  `;
}

function renderBadgeList(title, items = [], tone = "") {
  return `
    <div class="result-block">
      <h3>${title}</h3>
      <div class="badge-row">
        ${(items || []).map((item) => `<span class="badge ${tone}">${escapeHtml(String(item))}</span>`).join("") || "<span class=\"muted\">暂无</span>"}
      </div>
    </div>
  `;
}

function renderKeyValues(rows) {
  return `<dl class="kv-list">${rows.map(([key, value]) => `
    <div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value || "")}</dd></div>
  `).join("")}</dl>`;
}

function setResultContent(node, html) {
  node.className = "result-content";
  node.innerHTML = html;
}

function fillForm(form, values) {
  Object.entries(values).forEach(([key, value]) => {
    const field = form.elements[key];
    if (field) {
      field.value = value;
    }
  });
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error((data.errors || [data.error || "请求失败"]).join("；"));
  }
  return data;
}

async function getJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

function setButtonBusy(button, isBusy, label) {
  button.disabled = isBusy;
  button.textContent = label;
}

function updateStatus(text, activeIndex) {
  runtimeStatus.textContent = text;
  markWorkflowProgress(activeIndex);
  setActiveStepPage(statusPageMap[activeIndex] || "taskCard");
}

function markWorkflowProgress(activeIndex) {
  const p0LimitByStatus = {
    0: 1,
    1: 2,
    2: 3,
    3: 4,
    4: 5,
    5: 5,
    6: 6,
    7: 7,
    8: 8,
    9: 9,
    10: 9
  };
  const p0Limit = p0LimitByStatus[activeIndex] || 1;

  workflowStrip.querySelectorAll(".workflow-step").forEach((item) => {
    const flowIndex = Number(item.dataset.flowIndex || 0);
    if (flowIndex) {
      item.classList.toggle("active", flowIndex <= p0Limit);
      return;
    }

    const targetId = (item.getAttribute("href") || "").replace("#", "");
    const p1IsActive =
      (targetId === "qualityCard" && activeIndex >= 5) ||
      (targetId === "libraryCard" && activeIndex >= 9) ||
      (targetId === "feedbackCard" && activeIndex >= 10);
    item.classList.toggle("active", p1IsActive);
  });
}

function setActiveStepPage(targetId, options = {}) {
  if (!stepPages[targetId]) {
    return;
  }

  Object.entries(stepPages).forEach(([id, page]) => {
    page.classList.toggle("active", id === targetId);
  });

  document.querySelectorAll("[data-step-target]").forEach((button) => {
    button.classList.toggle("active", button.dataset.stepTarget === targetId);
  });

  workflowStrip.querySelectorAll(".workflow-step").forEach((link) => {
    link.classList.toggle("current", link.getAttribute("href") === `#${targetId}`);
  });

  if (options.scroll && resultPanel) {
    resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function toast(message) {
  const node = document.createElement("div");
  node.className = "toast";
  node.textContent = message;
  document.body.appendChild(node);
  window.setTimeout(() => node.remove(), 3200);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#039;");
}

function renderScriptLibraryLoadFailure(error) {
  const message = escapeHtml(error?.message || "请求失败");
  savedTableBody.innerHTML = `<tr><td colspan="11" class="muted">脚本库加载失败：${message}</td></tr>`;
}

updateReviewFlowHint();
updateReviewChecklist();

loadSavedScripts().catch(renderScriptLibraryLoadFailure);
loadPerformanceInsights().catch(() => {
  feedbackResult.innerHTML = "数据复盘加载失败";
});
