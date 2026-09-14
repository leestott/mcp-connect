const state = { data: null, approvalId: null, busy: false };

const $ = (id) => document.getElementById(id);
const formatNumber = (value) => new Intl.NumberFormat("en-IN").format(value ?? 0);
const safeJson = (value) => JSON.stringify(value).replaceAll("<", "&lt;").replaceAll(">", "&gt;");

function setBusy(busy, label = "Working...") {
  state.busy = busy;
  $("analysis-button").disabled = busy;
  $("analysis-button").innerHTML = busy ? `<span class="spinner"></span>${label}` : `<i data-lucide="play"></i>Run analysis`;
  const canApprove = state.data?.last_result?.status === "approval_required";
  const canReplay = state.data?.last_result?.status === "quarantined" && state.approvalId;
  $("approval-button").disabled = busy || (!canApprove && !canReplay);
  $("approval-button").innerHTML = canReplay
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
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "Operation failed");
  return body;
}

function renderInventory(inventory) {
  const rows = [...inventory.positions].sort((a, b) =>
    a.location_type.localeCompare(b.location_type) || a.location.localeCompare(b.location)
  );
  $("inventory-body").innerHTML = rows.length ? rows.map((position) => `
    <tr>
      <td class="location-name">${position.location}</td>
      <td class="type-label">${position.location_type.replaceAll("_", " ")}</td>
      <td class="number">${formatNumber(position.units)}</td>
      <td><span class="badge ${position.status}">${position.status}</span></td>
    </tr>`).join("") : `<tr><td colspan="4" class="empty">No affected inventory found.</td></tr>`;
}

function renderWorkflow(workflow) {
  $("workflow-list").innerHTML = workflow.map((stage, index) => `
    <li class="${stage.status}">
      <span class="workflow-index">${stage.status === "complete" ? "OK" : String(index + 1).padStart(2, "0")}</span>
      <div class="workflow-name">${stage.name}</div>
      <div class="workflow-tool">${stage.tool || "synthesize decision brief"}</div>
    </li>`).join("");
}

function renderCalls(calls) {
  $("call-count").textContent = calls.length;
  $("activity-list").innerHTML = calls.length ? calls.map((call) => `
    <article class="activity-item ${call.outcome}">
      <div class="activity-top"><strong>${call.tool}</strong><span>${call.duration_ms ?? "--"} ms</span></div>
      <code>${safeJson(call.input)}</code>
      <div class="activity-meta"><span>${call.protocol}</span><span>${call.outcome.toUpperCase()}</span></div>
    </article>`).join("") : `<p class="empty">No tool calls in this run.</p>`;
}

function renderAudit(audit) {
  $("audit-list").innerHTML = audit.length ? [...audit].reverse().map((event) => `
    <article class="audit-item">
      <div class="audit-top"><strong>${event.event.replaceAll("_", " ")}</strong><span>${new Date(event.timestamp).toLocaleTimeString()}</span></div>
      <p>${event.batch_id} / ${safeJson(event.details)}</p>
    </article>`).join("") : `<p class="empty">No control events recorded.</p>`;
}

function renderBrief(result) {
  const brief = $("decision-brief");
  brief.hidden = !result;
  if (!result) return;
  if (result.facts) {
    $("brief-facts").textContent = `${formatNumber(result.facts.units)} units at ${result.facts.locations} locations; ${result.facts.risk_tier} risk; supplier ${result.facts.supplier_acknowledged ? "acknowledged" : "not acknowledged"}.`;
    $("brief-recommendation").textContent = result.recommendation;
    $("brief-uncertainty").textContent = result.uncertainty;
    $("brief-action").textContent = result.required_human_action;
  } else {
    $("brief-facts").textContent = `${formatNumber(result.units_quarantined)} units processed.`;
    $("brief-recommendation").textContent = result.idempotent_replay ? "Replay confirmed: no additional inventory changed." : `${result.positions_changed} positions moved to quarantine.`;
    $("brief-uncertainty").textContent = "No inventory mutation remains pending for this batch.";
    $("brief-action").textContent = "Review the audit evidence and continue recall communications.";
  }
}

function render(data) {
  state.data = data;
  const { notice, inventory, supplier } = data;
  $("runtime-mode").textContent = data.runtime.toUpperCase();
  $("protocol").textContent = data.protocol;
  $("model-name").textContent = data.model_deployment;
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
  $("incident-status").textContent = quarantined ? "QUARANTINED" : data.last_result ? "DECISION READY" : "ASSESSMENT";
  $("dialog-units").textContent = formatNumber(inventory.total_units);
  $("dialog-locations").textContent = inventory.locations;
  $("dialog-batch").textContent = notice.batch_id;
  $("correlation-id").textContent = data.correlation_id ? `TRACE ${data.correlation_id.slice(0, 12).toUpperCase()}` : "NO ACTIVE RUN";
  renderInventory(inventory);
  renderWorkflow(data.workflow);
  renderCalls(data.calls);
  renderAudit(data.audit);
  renderBrief(data.last_result);
  setBusy(false);
  if (window.lucide) window.lucide.createIcons();
}

async function loadState() {
  try { render(await api("/api/state")); }
  catch (error) { toast(`Disconnected: ${error.message}`, true); }
}

$("analysis-button").addEventListener("click", async () => {
  setBusy(true, "Running specialists...");
  try {
    render(await api("/api/analysis", { method: "POST", body: "{}" }));
    toast("Analysis complete. Human approval is required.");
  } catch (error) {
    setBusy(false);
    toast(error.message, true);
    await loadState();
  }
});

$("approval-button").addEventListener("click", async () => {
  if (state.approvalId && state.data?.last_result?.status === "quarantined") {
    setBusy(true, "Replaying control...");
    try {
      render(await api("/api/quarantine", { method: "POST", body: JSON.stringify({ approval_id: state.approvalId }) }));
      toast("Replay confirmed. No additional inventory changed.");
    } catch (error) { setBusy(false); toast(error.message, true); }
    return;
  }
  $("approval-dialog").showModal();
  $("approver-name").focus();
});

$("cancel-approval").addEventListener("click", () => $("approval-dialog").close());

$("approval-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const approver = $("approver-name").value.trim();
  if (!approver) return;
  $("approval-dialog").close();
  setBusy(true, "Applying control...");
  try {
    const approval = await api("/api/approval", { method: "POST", body: JSON.stringify({ approver }) });
    state.approvalId = approval.approval_id;
    render(await api("/api/quarantine", { method: "POST", body: JSON.stringify({ approval_id: state.approvalId }) }));
    toast("Named approval recorded. 2,196 units quarantined.");
  } catch (error) {
    setBusy(false);
    toast(error.message, true);
  }
});

$("reset-button").addEventListener("click", async () => {
  setBusy(true, "Resetting...");
  try {
    state.approvalId = null;
    render(await api("/api/reset", { method: "POST", body: "{}" }));
    $("approver-name").value = "";
    toast("Demo state restored.");
  } catch (error) { setBusy(false); toast(error.message, true); }
});

window.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) window.lucide.createIcons();
  loadState();
});
