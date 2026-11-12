"use strict";

const $ = (selector) => document.querySelector(selector);
const view = $("#result-view");
const panel = $("#result-panel");
const question = $("#question");
const scope = $("#report-scope");
const statusLine = $("#request-status");
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
let reportsReady = false;
let busy = false;

const examples = {
  production: "In Devon's estimated 2008 production table, what percentage of total production in MMBoe comes from Canada?",
  revenue: "For CBRE, what was the signed percentage change in net revenue from 2015 to 2016?",
};
const labels = {
  success: ["Analysis complete", "Calculated", ""],
  insufficient_evidence: ["No verified answer", "Insufficient evidence", "warning"],
  unsupported_request: ["Outside the supported scope", "Unsupported request", "warning"],
  blocked: ["Analysis blocked", "Blocked", "warning"],
  failed: ["Analysis unavailable", "Technical failure", "error"],
  started: ["Analysis not finalized", "Started", "warning"],
};
const explanations = {
  ambiguous_unit: "The source unit could not be established. No numerical answer was produced.",
  ambiguous_scale: "The source scale is ambiguous. No numerical answer was produced.",
  ambiguous_period: "The evidence does not establish a clear period for this calculation.",
  question_period_mismatch: "The source period does not match the question.",
  no_numeric_candidates: "The retrieved excerpts did not contain usable table cells.",
  provider_http_429: "The model service's request limit was reached. Wait before submitting a new analysis.",
  provider_http_503: "The model service is temporarily unavailable. This attempt produced no answer.",
  provider_http_504: "The model service did not respond in time. A saved result may still be finalizing.",
  provider_timeout: "The model service did not respond in time.",
  provider_not_configured: "A model provider has not been connected to this server.",
  budget_limit: "The local request allowance has been reached. No further model work is allowed.",
  analysis_in_progress: "Another analysis is still running. Wait before submitting a new question.",
  deadline_reached: "The analysis reached its time limit. The server may still be finalizing its saved result.",
  recording_unavailable: "Saved-result storage is unavailable. A durable result cannot be guaranteed.",
  analysis_not_found: "No saved analysis was found for this execution ID.",
};

// All report/question/response text enters the page as text, never as HTML.
function element(tag, className = "", text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function setBusy(value, message = "") {
  busy = value;
  question.disabled = value || !reportsReady;
  scope.disabled = value || !reportsReady;
  $("#analyze-button").disabled = value || !reportsReady;
  $("#lookup-button").disabled = value;
  $("#run-id").disabled = value;
  document.querySelectorAll(".example").forEach((button) => { button.disabled = value || !reportsReady; });
  $("#analyze-label").textContent = value ? "Please wait…" : "Analyze question";
  panel.setAttribute("aria-busy", String(value));
  statusLine.textContent = message;
}

function rememberRun(id) {
  const url = new URL(window.location.href);
  url.hash = "";
  if (id && uuid.test(id)) {
    url.searchParams.set("run", id);
    $("#run-id").value = id;
  } else {
    url.searchParams.delete("run");
  }
  window.history.replaceState(null, "", url);
}

function showLoading(saved) {
  const box = element("div", "loading-state");
  box.append(element("span", "spinner"), element("h2", "", saved ? "Opening saved analysis" : "Following the evidence"));
  box.append(element("p", "", saved ? "Reading the stored result. No model request is made." : "Searching the reports, selecting source values and checking the calculation."));
  view.replaceChildren(box);
}

function addNotice(parent, title, message, variant = "warning", runId = null) {
  const notice = element("div", `notice ${variant}`);
  notice.append(element("h3", "", title), element("p", "", message));
  if (runId && uuid.test(runId)) {
    notice.append(element("p", "cell-note", `Execution ID: ${runId}`));
    const button = element("button", "button secondary", "Check saved result");
    button.type = "button";
    button.addEventListener("click", () => { if (!busy) openSaved(runId); });
    notice.append(button);
  }
  parent.append(notice);
}

function unitLabel(context) {
  if (context.unit === "$" && context.scale === 1000000) return "$ · millions";
  if (context.unit === "$" && context.scale === 1000) return "$ · thousands";
  if (context.unit === "square feet" && context.scale === 1000000) return "million square feet";
  return context.unit;
}

function renderCalculation(parent, calculation, evidence) {
  const answer = element("div", "answer-block");
  answer.append(element("p", "answer-label", "Calculated result"), element("p", "answer-value", calculation.display), element("div", "formula", calculation.formula));
  parent.append(answer);
  const heading = element("div", "subheading");
  heading.append(element("h3", "", "Values behind the result"), element("span", "", "Original source values"));
  parent.append(heading);
  const scroll = element("div", "table-scroll");
  scroll.tabIndex = 0;
  scroll.setAttribute("role", "region");
  scroll.setAttribute("aria-label", "Source values. Scroll horizontally to see all columns.");
  const table = element("table");
  table.setAttribute("aria-label", "Source values used in the calculation");
  const head = element("thead");
  const headerRow = element("tr");
  ["Measure / period", "Value", "Unit", "Source cell"].forEach((label) => {
    const cell = element("th", "", label); cell.scope = "col"; headerRow.append(cell);
  });
  head.append(headerRow);
  const body = element("tbody");
  calculation.operands.forEach((operand) => {
    const row = element("tr");
    const measure = element("td", "measure", operand.row_label);
    const context = operand.context;
    const nature = { estimate: "estimate", reported: "reported", as_of: "as of" }[context.nature] || context.nature;
    // A nearby context date can describe reserves rather than the estimate period.
    const period = context.date?.startsWith(`${context.year}-`) ? context.date : context.year;
    measure.append(element("span", "cell-note", `${period} · ${nature}`), element("span", "cell-note", `Column: ${operand.column_header}`));
    const source = element("td");
    const index = evidence.findIndex((hit) => hit.cell_ids.includes(operand.cell_id));
    const reference = element(index >= 0 ? "a" : "span", "source-reference", operand.cell_id);
    if (index >= 0) {
      reference.href = `#evidence-${index + 1}`;
      reference.addEventListener("click", () => { document.getElementById(`evidence-${index + 1}`).open = true; });
    }
    source.append(reference);
    row.append(measure, element("td", "source-value", operand.source_value), element("td", "", unitLabel(context)), source);
    body.append(row);
  });
  table.append(head, body); scroll.append(table); parent.append(scroll);
}

function renderEvidence(parent, evidence, calculation) {
  const heading = element("div", "subheading");
  heading.append(element("h3", "", "Report evidence"), element("span", "", `${evidence.length} retrieved excerpt${evidence.length === 1 ? "" : "s"}`));
  parent.append(heading);
  if (!evidence.length) parent.append(element("p", "muted", "No report excerpts were recorded for this attempt."));
  const usedCells = new Set((calculation?.operands || []).map((operand) => operand.cell_id));
  evidence.forEach((hit, index) => {
    const used = hit.cell_ids.some((id) => usedCells.has(id));
    const details = element("details", "excerpt");
    details.id = `evidence-${index + 1}`;
    details.open = used || index === 0;
    const summary = element("summary", "", `${index + 1}. ${hit.source_id}`);
    if (used) summary.append(element("span", "used", "Used in calculation"));
    const score = typeof hit.score === "number" ? hit.score.toFixed(4) : "unknown";
    details.append(summary, element("p", "excerpt-meta", `${hit.kind} excerpt · search score ${score}`), element("pre", "", hit.text));
    parent.append(details);
  });
}

function renderTechnical(parent, data) {
  const details = element("details", "technical");
  details.append(element("summary", "", "Execution details"));
  const list = element("dl", "execution-meta");
  const duration = typeof data.duration_seconds === "number" ? `${data.duration_seconds.toFixed(2)} seconds` : "Not available";
  for (const [label, value] of [["Execution ID", data.run_id], ["Recorded", data.created_at_utc], ["Retrieval", data.retrieval_method], ["Duration", duration], ["Scope", data.report_ids?.join(", ") || "All reports"], ["Error code", data.error_code || "None"]]) {
    list.append(element("dt", "", label), element("dd", "", value));
  }
  details.append(list, element("p", "cell-note", "Search scores rank excerpts; they are not answer-confidence scores. Unknown usage and charges remain null in the response."), element("pre", "json", JSON.stringify(data, null, 2)));
  parent.append(details);
}

function renderRecord(data, saved) {
  const [title, badge, variant] = labels[data.status] || labels.failed;
  const fragment = document.createDocumentFragment();
  const heading = element("div", "result-heading");
  const text = element("div");
  text.append(element("p", "eyebrow", saved ? "SAVED ANALYSIS" : "YOUR ANALYSIS"), element("h2", "", title));
  heading.append(text, element("span", `status-badge ${variant}`, badge));
  fragment.append(heading, element("p", "question-display", data.question));
  const calculation = data.status === "success" ? data.calculation : null;
  if (calculation) renderCalculation(fragment, calculation, data.evidence);
  else {
    const fallback = data.status === "started" ? "This execution is not finalized. Check the saved result again in a moment." : data.status === "unsupported_request" ? "This question requires an operation or source context outside the supported scope." : "The available evidence did not produce a verified numerical answer.";
    addNotice(fragment, title, explanations[data.error_code] || fallback, variant, data.status === "started" || data.error_code === "deadline_reached" ? data.run_id : null);
  }
  renderEvidence(fragment, data.evidence, calculation);
  renderTechnical(fragment, data);
  view.replaceChildren(fragment);
  rememberRun(data.run_id);
}

// A UI/network timeout cannot recall an already submitted server/model request.
async function requestAnalysis(path, options, saved) {
  if (busy) return;
  setBusy(true, saved ? "Opening saved analysis…" : "Analysis in progress…");
  showLoading(saved);
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 75000);
  let announcement;
  try {
    const response = await fetch(path, { ...options, signal: controller.signal, cache: "no-store", headers: { Accept: "application/json", ...options.headers } });
    const data = await response.json();
    if (Array.isArray(data.evidence) && typeof data.question === "string" && uuid.test(data.run_id)) {
      renderRecord(data, saved);
      announcement = saved ? "Saved analysis opened. No model request was made." : data.status === "success" ? "Calculation complete. The result and sources are displayed." : "The recorded outcome and available evidence are displayed.";
    } else {
      view.replaceChildren();
      const id = uuid.test(data.run_id || "") ? data.run_id : null;
      if (id) rememberRun(id);
      addNotice(view, saved ? "Could not open this analysis" : "No answer was produced", explanations[data.error_code] || data.message || "The service could not complete this request.", "error", id);
      if (data.error_code) view.append(element("p", "cell-note", `Error code: ${data.error_code}`));
      announcement = "The request could not complete. Review the message in the result panel.";
    }
  } catch {
    view.replaceChildren();
    addNotice(view, "The result could not be received", "Check the local server connection. A submitted analysis may still be running; opening its saved execution does not create another model request.", "error");
    announcement = "The result could not be received.";
  } finally {
    window.clearTimeout(timeout);
    setBusy(false, announcement);
    if (window.matchMedia("(max-width: 840px)").matches) panel.scrollIntoView({ block: "start" });
  }
}

function openSaved(id) {
  if (!uuid.test(id)) { statusLine.textContent = "Enter a valid execution ID in the form shown by a saved result."; return; }
  requestAnalysis(`/analyses/${encodeURIComponent(id)}`, { method: "GET" }, true);
}

$("#analysis-form").addEventListener("submit", (event) => {
  event.preventDefault();
  if (busy || !reportsReady) return;
  if (!question.value.trim()) { question.focus(); statusLine.textContent = "Enter a question before submitting."; return; }
  rememberRun(null);
  requestAnalysis("/analyses", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: question.value, report_ids: scope.value ? [scope.value] : null, mode: "fixed" }) }, false);
});
$("#lookup-form").addEventListener("submit", (event) => { event.preventDefault(); openSaved($("#run-id").value.trim()); });
question.addEventListener("input", () => { $("#character-count").textContent = `${question.value.length.toLocaleString("en-US")} / 2,000`; });
document.querySelectorAll(".example").forEach((button) => button.addEventListener("click", () => {
  question.value = examples[button.dataset.example]; question.dispatchEvent(new Event("input")); question.focus();
}));

async function initialize() {
  try {
    const response = await fetch("/reports", { cache: "no-store" });
    if (!response.ok) throw new Error("Reports unavailable");
    const data = await response.json();
    data.reports.forEach((report) => { const option = element("option", "", report.report_id); option.value = report.report_id; scope.append(option); });
    reportsReady = data.reports.length > 0;
    $("#availability").textContent = `${data.reports.length} reports available`;
    $("#availability").className = "availability ready";
  } catch {
    $("#availability").textContent = "Reports unavailable";
    $("#availability").className = "availability unavailable";
    statusLine.textContent = "Reports are not available yet. You can still open a saved analysis.";
  }
  setBusy(busy, statusLine.textContent);
  const id = new URL(window.location.href).searchParams.get("run");
  if (id) { $("#run-id").value = id; openSaved(id); }
}
initialize();
