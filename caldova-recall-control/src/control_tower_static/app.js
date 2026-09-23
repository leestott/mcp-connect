const state = { data: null, approvalId: null, busy: false, pending: false, refreshing: false, stale: true, approvalBlocked: false, refreshTimer: null, monitoringStarted: null };

const $ = (id) => document.getElementById(id);
const themePreference = window.matchMedia("(prefers-color-scheme: dark)");

function updateThemeButton() {
  const dark = document.documentElement.dataset.theme === "dark"
    || (!document.documentElement.dataset.theme && themePreference.matches);
  const label = `Switch to ${dark ? "light" : "dark"} theme`;
  $("theme-button").setAttribute("aria-label", label);
  $("theme-button").title = label;
  $("theme-button").innerHTML = `<i data-lucide="${dark ? "sun" : "moon"}"></i>`;
  if (window.lucide) window.lucide.createIcons();
}

try {
  const savedTheme = localStorage.getItem("caldova-theme");
  if (savedTheme === "light" || savedTheme === "dark") document.documentElement.dataset.theme = savedTheme;
} catch (error) {
  console.warn("Theme preference could not be loaded; using system preference.", error);
}
updateThemeButton();
themePreference.addEventListener("change", updateThemeButton);
window.addEventListener("storage", (event) => {
  if (event.key !== "caldova-theme" && event.key !== null) return;
  if (event.newValue === "light" || event.newValue === "dark") document.documentElement.dataset.theme = event.newValue;
  else delete document.documentElement.dataset.theme;
  updateThemeButton();
});
$("theme-button").addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme === "dark"
    || (!document.documentElement.dataset.theme && themePreference.matches);
  const next = dark ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  updateThemeButton();
  try {
    localStorage.setItem("caldova-theme", next);
  } catch (error) {
    console.warn("Theme preference could not be saved for future visits.", error);
    toast("Theme changed for this visit, but the preference could not be saved.", true);
  }
});

const formatNumber = (value) => new Intl.NumberFormat("en-IN").format(value ?? 0);
const escapeHtml = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
const safeJson = (value) => escapeHtml(JSON.stringify(value));
const authorized = () => state.data?.runtime === "hosted"
  ? state.data.identity?.can_approve === true
  : Boolean(state.data) && state.data.identity?.can_approve !== false;
const canAct = () => Boolean(state.data) && !state.busy && !state.stale && !state.refreshing;
const canApprove = () => canAct() && authorized() && !state.approvalBlocked && state.data.last_result?.status === "approval_required";
const canReplay = () => canAct() && authorized() && !state.approvalBlocked && state.data.last_result?.status === "quarantined" && Boolean(state.approvalId);

function setBusy(busy, label = "Working...") {
  state.busy = busy;
  $("analysis-button").disabled = !canAct();
  $("reset-button").disabled = !canAct() || !authorized();
  $("refresh-button").disabled = state.pending || state.refreshing;
  $("analysis-button").innerHTML = busy ? `<span class="spinner"></span>${label}` : `<i data-lucide="play"></i>Run analysis`;
  $("approval-button").disabled = !canApprove() && !canReplay();
  $("confirm-approval").disabled = !canApprove();
  if (!canApprove() && $("approval-dialog").open) $("approval-dialog").close();
  $("approval-button").innerHTML = state.data?.last_result?.status === "quarantined" && state.approvalId
    ? `<i data-lucide="repeat-2"></i>Replay quarantine`
    : `<i data-lucide="shield-check"></i>Approve quarantine`;
  if (window.lucide) window.lucide.createIcons();
}

function toast(message, error = false) {
  const element = $("toast");
  element.textContent = message;
  element.className = error ? "toast error" : "toast";
  element.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { element.hidden = true; }, 4200);
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.method === "POST" ? 120000 : 10000);
  try {
    const response = await fetch(path, {
      ...options,
      signal: controller.signal,
      credentials: "same-origin",
      redirect: "error",
      cache: "no-store",
      headers: { "Content-Type": "application/json", "X-Caldova-Request": "1", ...(options.headers || {}) },
    });
    if (response.status === 401 || response.redirected) {
      throw new Error("Session expired. Reload to sign in again.");
    }
    const body = await response.json();
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Operation failed");
    return body;
  } catch (error) {
    if (controller.signal.aborted) throw new Error("Request timed out. The server may still be processing it.");
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function renderInventory(inventory) {
  const rows = [...inventory.positions].sort((a, b) =>
    a.location_type.localeCompare(b.location_type) || a.location.localeCompare(b.location)
  );
  $("inventory-body").innerHTML = rows.length ? rows.map((position) => `
    <tr>
      <td class="location-name">${escapeHtml(position.location)}</td>
      <td class="type-label">${escapeHtml(position.location_type.replaceAll("_", " "))}</td>
      <td class="number">${formatNumber(position.units)}</td>
      <td><span class="badge ${escapeHtml(position.status)}">${escapeHtml(position.status)}</span></td>
    </tr>`).join("") : `<tr><td colspan="4" class="empty">No affected inventory found.</td></tr>`;
}

function renderWorkflow(workflow) {
  $("workflow-list").hidden = workflow.length === 0;
  $("workflow-list").innerHTML = workflow.map((stage, index) => `
    <li class="${escapeHtml(stage.status)}">
      <span class="workflow-index">${stage.status === "complete" ? "OK" : String(index + 1).padStart(2, "0")}</span>
      <div class="workflow-name">${escapeHtml(stage.name)}</div>
      <div class="workflow-tool">${escapeHtml(stage.tool || "synthesize decision brief")}</div>
    </li>`).join("");
}

function renderCalls(calls) {
  $("call-count").textContent = calls.length;
  $("activity-list").innerHTML = calls.length ? calls.map((call) => `
    <article class="activity-item ${escapeHtml(call.outcome)}">
      <div class="activity-top"><strong>${escapeHtml(call.tool)}</strong><span>${escapeHtml(call.duration_ms ?? "--")} ms</span></div>
      <code>${safeJson(call.input)}</code>
      <div class="activity-meta"><span>${escapeHtml(call.protocol)}</span><span>${escapeHtml(call.outcome.toUpperCase())}</span></div>
    </article>`).join("") : `<p class="empty">${state.data?.runtime === "hosted" ? "Hosted tool trace unavailable." : "No tool calls in this run."}</p>`;
}

function renderAudit(audit) {
  $("audit-list").innerHTML = audit.length ? [...audit].reverse().map((event) => `
    <article class="audit-item">
      <div class="audit-top"><strong>${escapeHtml(event.event.replaceAll("_", " "))}</strong><span>${new Date(event.timestamp).toLocaleTimeString()}</span></div>
      <p>${escapeHtml(event.batch_id)} / ${safeJson(event.details)}</p>
    </article>`).join("") : `<p class="empty">No control events recorded.</p>`;
}

function renderQuarantineEvidence(data) {
  const resetIndex = data.audit.findLastIndex((event) => event.event === "demo_reset");
  const outcomes = data.audit.slice(resetIndex + 1)
    .filter((event) => event.event === "batch_quarantined" && event.batch_id === data.notice.batch_id)
    .map((event) => event.details);
  const first = outcomes.find((result) => result.idempotent_replay === false);
  const replay = outcomes.findLast((result) => result.idempotent_replay === true);
  const describe = (result) => result
    ? `${formatNumber(result.positions_changed)} positions changed; ${formatNumber(result.units_quarantined)} units processed.`
    : "Not recorded";
  $("quarantine-evidence").hidden = outcomes.length === 0;
  $("first-quarantine-result").textContent = describe(first);
  $("replay-quarantine-result").textContent = describe(replay);
}

function renderBrief(result) {
  const brief = $("decision-brief");
  const assessment = state.data.runtime === "hosted"
    ? state.data.assessment || (result?.agent_text ? result : null) : null;
  brief.hidden = !result && !assessment;
  const hostedAnswer = Boolean(assessment);
  $("hosted-answer").hidden = !hostedAnswer;
  $("brief-grid").hidden = !result || (hostedAnswer && result.status !== "quarantined");
  $("hosted-text").textContent = "";
  $("hosted-response-id").textContent = "";
  if (hostedAnswer) {
    $("hosted-text").textContent = typeof assessment.agent_text === "string" && assessment.agent_text ? assessment.agent_text : "No model response available.";
    $("hosted-response-id").textContent = [assessment.response_id && `Response ${assessment.response_id}`, assessment.request_id && `Request ${assessment.request_id}`].filter(Boolean).join(" | ");
  }
  if (!result) return;
  if (result.facts) {
    $("brief-facts").textContent = `${formatNumber(result.facts.units)} units at ${result.facts.locations} locations; ${result.facts.risk_tier} risk; supplier ${result.facts.supplier_acknowledged ? "acknowledged" : "not acknowledged"}.`;
    $("brief-recommendation").textContent = result.recommendation;
    $("brief-uncertainty").textContent = result.uncertainty;
    $("brief-action").textContent = result.required_human_action;
  } else if (result.status === "quarantined") {
    $("brief-facts").textContent = `${formatNumber(result.units_quarantined)} units processed.`;
    $("brief-recommendation").textContent = result.idempotent_replay ? "Replay confirmed: no additional inventory changed." : `${result.positions_changed} positions moved to quarantine.`;
    $("brief-uncertainty").textContent = "No inventory mutation remains pending for this batch.";
    $("brief-action").textContent = "Review the audit evidence and continue recall communications.";
  } else {
    $("brief-grid").hidden = true;
  }
}

function render(data) {
  state.data = data;
  state.stale = false;
  if (data.runtime === "hosted") {
    state.approvalId = data.last_result?.status === "quarantined" && typeof data.replay_approval_id === "string" && data.replay_approval_id
      ? data.replay_approval_id : null;
  } else if (data.last_result?.status !== "quarantined") {
    state.approvalId = null;
  }
  const { notice, inventory, supplier } = data;
  $("runtime-mode").textContent = data.runtime === "local" ? "LOCAL / NO MODEL" : data.runtime.toUpperCase();
  $("protocol").textContent = data.protocol;
  $("execution-label").textContent = data.runtime === "local" ? "DETERMINISTIC LOCAL DEMO" : "FOUNDRY HOSTED AGENT";
  $("model-name").textContent = data.runtime === "local" ? "No model calls" : data.model_deployment;
  $("approver-label").textContent = data.runtime === "local" ? "Demo approver name (not authenticated)" : "Authenticated approver";
  if (data.identity) {
    $("approver-name").value = data.identity.name;
    $("approver-name").readOnly = true;
    $("approver-name").removeAttribute("maxlength");
    $("approver-name").removeAttribute("minlength");
  }
  $("incident-title").textContent = notice.product;
  $("incident-reason").textContent = notice.reason;
  $("batch-id").textContent = notice.batch_id;
  $("supplier-name").textContent = notice.supplier;
  $("risk-tier").textContent = notice.risk_tier;
  $("total-units").textContent = formatNumber(inventory.total_units);
  $("location-count").textContent = inventory.locations;
  $("supplier-state").textContent = supplier.supplier_acknowledged ? "ACKNOWLEDGED" : "PENDING";
  $("replacement-eta").textContent = `${supplier.replacement_eta_hours}h replacement ETA`;
  const quarantined = inventory.positions.every((position) => position.status === "quarantined");
  $("incident-status").textContent = data.analysis_running ? "ANALYZING" : quarantined ? "QUARANTINED" : data.last_result?.status === "approval_required" ? "DECISION READY" : "ASSESSMENT";
  $("dialog-units").textContent = formatNumber(inventory.total_units);
  $("dialog-locations").textContent = inventory.locations;
  $("dialog-batch").textContent = notice.batch_id;
  $("correlation-id").textContent = data.correlation_id ? `REQUEST ${data.correlation_id.slice(0, 12).toUpperCase()}` : "NO ACTIVE RUN";
  renderInventory(inventory);
  renderWorkflow(data.runtime === "hosted" ? [] : data.workflow);
  $("workflow-empty").hidden = data.runtime !== "hosted";
  renderCalls(data.runtime === "hosted" ? [] : data.calls);
  renderAudit(data.audit);
  renderQuarantineEvidence(data);
  renderBrief(data.last_result);
  monitorAnalysis();
  setBusy(state.pending || Boolean(data.analysis_running));
  if (window.lucide) window.lucide.createIcons();
}

function monitorAnalysis() {
  clearTimeout(state.refreshTimer);
  if (!state.data.analysis_running) {
    state.monitoringStarted = null;
    $("state-status").textContent = state.approvalBlocked ? "Control failed. Approval is locked pending a new analysis." : "";
    return;
  }
  state.monitoringStarted ??= Date.now();
  if (Date.now() - state.monitoringStarted >= 120000) {
    state.stale = true;
    $("state-status").textContent = "Analysis still pending. Automatic refresh paused; completion is unconfirmed.";
    return;
  }
  $("state-status").textContent = "Analysis in progress. Checking server state...";
  state.refreshTimer = setTimeout(loadState, 2000);
}

async function loadState() {
  if (state.pending || state.refreshing) return;
  state.refreshing = true;
  setBusy(state.busy);
  try { render(await api("/api/state")); }
  catch (error) {
    clearTimeout(state.refreshTimer);
    state.stale = true;
    state.approvalId = null;
    $("runtime-mode").textContent = "OFFLINE";
    $("state-status").textContent = `State unavailable: ${error.message}`;
    toast(`Disconnected: ${error.message}`, true);
  } finally {
    state.refreshing = false;
    setBusy(!state.stale && Boolean(state.data?.analysis_running));
  }
}

async function recover(error) {
  state.pending = false;
  state.stale = true;
  state.approvalBlocked = true;
  state.approvalId = null;
  setBusy(false);
  toast(error.message, true);
  await loadState();
}

function beginOperation(label) {
  clearTimeout(state.refreshTimer);
  state.pending = true;
  setBusy(true, label);
}

$("refresh-button").addEventListener("click", () => {
  if (state.pending || state.refreshing) return;
  clearTimeout(state.refreshTimer);
  state.monitoringStarted = null;
  loadState();
});

$("analysis-button").addEventListener("click", async () => {
  if (!canAct()) return;
  state.approvalId = null;
  beginOperation(state.data?.runtime === "hosted" ? "Contacting live agent..." : "Reading evidence...");
  try {
    const data = await api("/api/analysis", { method: "POST", body: "{}" });
    state.pending = false;
    state.approvalBlocked = false;
    render(data);
    toast(data.analysis_running ? "Analysis in progress." : data.last_result?.status === "approval_required" ? "Analysis complete. Human approval is required." : "Analysis state updated.");
  } catch (error) {
    await recover(error);
  }
});

$("approval-button").addEventListener("click", async () => {
  if (canReplay()) {
    beginOperation("Replaying control...");
    try {
      const data = await api("/api/quarantine", { method: "POST", body: JSON.stringify({ approval_id: state.approvalId }) });
      state.pending = false;
      render(data);
      toast(data.last_result?.status === "quarantined" && data.last_result.idempotent_replay ? "Replay confirmed. No additional inventory changed." : "Control state updated.");
    } catch (error) { await recover(error); }
    return;
  }
  if (!canApprove()) return;
  $("approval-dialog").showModal();
  $("approver-name").focus();
});

$("cancel-approval").addEventListener("click", () => $("approval-dialog").close());

$("approval-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!canApprove()) return;
  const approver = $("approver-name").value.trim();
  if (!approver) return;
  $("approval-dialog").close();
  beginOperation("Applying control...");
  try {
    const approval = await api("/api/approval", { method: "POST", body: JSON.stringify({ approver: state.data?.identity ? "Authenticated approver" : approver }) });
    state.approvalId = approval.approval_id;
    const data = await api("/api/quarantine", { method: "POST", body: JSON.stringify({ approval_id: state.approvalId }) });
    state.pending = false;
    render(data);
    toast(data.last_result?.status === "quarantined" ? "Named approval recorded. Inventory quarantined." : "Control state updated.");
  } catch (error) {
    await recover(error);
  }
});

$("reset-button").addEventListener("click", async () => {
  if (!canAct() || !authorized()) return;
  beginOperation("Resetting...");
  try {
    state.approvalId = null;
    const data = await api("/api/reset", { method: "POST", body: "{}" });
    state.pending = false;
    state.approvalBlocked = false;
    render(data);
    if (!state.data?.identity) $("approver-name").value = "";
    toast("Demo state restored.");
  } catch (error) { await recover(error); }
});

window.addEventListener("DOMContentLoaded", () => {
  setBusy(false);
  if (window.lucide) window.lucide.createIcons();
  loadState();
});
