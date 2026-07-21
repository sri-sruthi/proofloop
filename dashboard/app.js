(() => {
  "use strict";

  const KEY_STORAGE = "proofloop.dashboard.apiKey";
  const dashboard = document.querySelector("#dashboard");
  const form = document.querySelector("#connection-form");
  const connectButton = document.querySelector("#connect-button");
  const messageRegion = document.querySelector("#message-region");
  const apiKeyInput = document.querySelector("#api-key");
  const apiBaseInput = document.querySelector("#api-base");
  const runtimeConfig = window.PROOFLOOP_RUNTIME_CONFIG || {};
  const elements = {
    status: document.querySelector("[data-status]"), freshness: document.querySelector("#freshness-chip"),
    summary: document.querySelector("#status-summary"), updated: document.querySelector("#last-updated"),
    agent: document.querySelector("#identity-agent"), tenant: document.querySelector("#identity-tenant"),
    environment: document.querySelector("#identity-environment"), boundary: document.querySelector("#identity-boundary"),
    controls: document.querySelector("#control-list"), reasons: document.querySelector("#reason-list"),
    evidence: document.querySelector("#evidence-list"), action: document.querySelector("#next-safe-action"),
    evaluated: document.querySelector("#evaluated-at"), violation: document.querySelector("#last-violation"),
    timeline: document.querySelector("#timeline-list"), incidents: document.querySelector("#incident-list")
  };

  // An operator-entered key (session storage) always wins; otherwise fall back to
  // the optional read-only demo key baked into the deployment so evaluators can
  // load a record in one click. "Clear saved key" still empties the field.
  apiKeyInput.value = sessionStorage.getItem(KEY_STORAGE) || runtimeConfig.demoApiKey || "";
  if (typeof runtimeConfig.apiBaseUrl === "string" && runtimeConfig.apiBaseUrl) {
    apiBaseInput.value = runtimeConfig.apiBaseUrl;
    if (runtimeConfig.apiBaseUrl.startsWith("https://")) {
      document.querySelector("#environment").value = "DEVELOPMENT";
      document.querySelector("#boundary-id").value = "proofloop-demo-dev-invoices";
    }
  }

  function text(value, fallback = "—") {
    return value === null || value === undefined || value === "" ? fallback : String(value);
  }

  function date(value, fallback = "Not reported") {
    if (!value) return fallback;
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  }

  function state(value) {
    const normalized = String(value || "AMBER").toUpperCase();
    return ["GREEN", "AMBER", "RED"].includes(normalized) ? normalized : "AMBER";
  }

  function setMessage(message = "", type = "") {
    messageRegion.replaceChildren();
    if (!message) return;
    const box = document.createElement("p");
    box.className = `message ${type}`;
    box.textContent = message;
    messageRegion.append(box);
  }

  function makeListItem(value) {
    const item = document.createElement("li");
    item.textContent = text(value, "No reference supplied");
    return item;
  }

  function empty(target, message) {
    const item = document.createElement("p");
    item.className = "empty-state";
    item.textContent = message;
    target.replaceChildren(item);
  }

  function controlLabel(id) {
    return String(id || "Required control").replace(/[_-]/g, " ").replace(/\b\w/g, letter => letter.toUpperCase());
  }

  function renderControls(compliance) {
    const fallbackControls = [
      { control_id: "guardrails", display_name: controlLabel("guardrails_active"), active: compliance.guardrails_active },
      { control_id: "pii-redaction", display_name: controlLabel("pii_redaction_enabled"), active: compliance.pii_redaction_enabled },
      { control_id: "audit-logging", display_name: controlLabel("audit_logging_enabled"), active: compliance.audit_logging_enabled },
      { control_id: "hitl", display_name: controlLabel("hitl_configured"), active: compliance.hitl_configured }
    ];
    const apiControls = Array.isArray(compliance.controls) ? compliance.controls : [];
    const controls = apiControls.length ? apiControls : fallbackControls;
    elements.controls.replaceChildren();
    controls.forEach(control => {
      const active = control.active;
      const reportedState = String(control.status || "").toUpperCase();
      const controlState = ["GREEN", "AMBER", "RED"].includes(reportedState)
        ? reportedState
        : active === true ? "GREEN" : active === false ? "RED" : "AMBER";
      const row = document.createElement("li");
      row.className = "control-item";
      const dot = document.createElement("span");
      dot.className = `control-dot control-dot-${controlState.toLowerCase()}`;
      const body = document.createElement("div");
      const name = document.createElement("p");
      name.className = "control-name";
      name.textContent = control.display_name || controlLabel(control.control_id);
      const detail = document.createElement("p");
      detail.className = "control-detail";
      detail.textContent = `${controlState} · evidence ${date(control.last_evidence_at, "not reported")}`;
      body.append(name, detail); row.append(dot, body); elements.controls.append(row);
    });
  }

  function renderReferences(compliance) {
    const reasons = Array.isArray(compliance.reason_codes) ? compliance.reason_codes : [];
    const evidence = Array.isArray(compliance.supporting_evidence_ids) ? compliance.supporting_evidence_ids : [];
    reasons.length ? elements.reasons.replaceChildren(...reasons.map(makeListItem)) : empty(elements.reasons, "No reason codes were provided.");
    evidence.length ? elements.evidence.replaceChildren(...evidence.map(makeListItem)) : empty(elements.evidence, "No supporting evidence references were provided.");
  }

  function eventTitle(item) {
    if (item.current_status) return `${item.previous_status || "UNSET"} → ${item.current_status}`;
    return item.transition || item.status || item.event_type || item.title || item.reason_code || "Assurance event";
  }

  function eventDetail(item) {
    const reasons = item.reason_codes || item.reasons || item.reason_code;
    const evidence = item.supporting_evidence_ids || item.evidence_ids || item.evidence_id;
    return [reasons && `Reason: ${Array.isArray(reasons) ? reasons.join(", ") : reasons}`, evidence && `Evidence: ${Array.isArray(evidence) ? evidence.join(", ") : evidence}`].filter(Boolean).join(" · ") || "No additional event detail.";
  }

  function renderTimeline(items) {
    const sorted = [...items].sort((a, b) => new Date(b.occurred_at || b.timestamp || b.created_at || b.evaluated_at || 0) - new Date(a.occurred_at || a.timestamp || a.created_at || a.evaluated_at || 0));
    if (!sorted.length) return empty(elements.timeline, "No assurance transitions were recorded in the selected seven-day window.");
    elements.timeline.replaceChildren(...sorted.map(item => {
      const row = document.createElement("li"); row.className = "timeline-item";
      const timestamp = item.occurred_at || item.timestamp || item.created_at || item.evaluated_at;
      const time = document.createElement("time"); time.className = "timeline-time"; time.textContent = date(timestamp, "Unknown time");
      const point = document.createElement("span"); point.className = "timeline-point";
      const body = document.createElement("div");
      const title = document.createElement("p"); title.className = "timeline-title"; title.textContent = eventTitle(item);
      const detail = document.createElement("p"); detail.className = "timeline-detail"; detail.textContent = eventDetail(item);
      body.append(title, detail); row.append(time, point, body); return row;
    }));
  }

  function renderIncidents(items) {
    if (!items.length) return empty(elements.incidents, "No open or historical incidents were returned for this boundary.");
    elements.incidents.replaceChildren(...items.map(item => {
      const incident = document.createElement("article"); incident.className = "incident";
      const title = document.createElement("h3");
      title.textContent = text(item.title || item.incident_id || item.id || item.status, "Incident");
      const detail = document.createElement("p");
      const bits = [item.status && `Status: ${item.status}`, item.opened_at && `Opened: ${date(item.opened_at)}`, item.reason_codes && `Reasons: ${Array.isArray(item.reason_codes) ? item.reason_codes.join(", ") : item.reason_codes}`, item.next_safe_action || item.remediation_steps];
      detail.textContent = bits.filter(Boolean).join(" · ") || "No incident detail was provided.";
      incident.append(title, detail); return incident;
    }));
  }

  function render(compliance, timeline, incidents) {
    const status = state(compliance.overall_compliance_status);
    dashboard.className = `dashboard ${status}`;
    dashboard.hidden = false;
    elements.status.textContent = status;
    elements.freshness.textContent = status === "GREEN" ? "Fresh evidence verified" : "Evidence needs attention";
    elements.summary.textContent = status === "GREEN" ? "Every required control has fresh, consistent PASS evidence." : "Review the recorded reasons and complete the next safe action before relying on this boundary.";
    elements.agent.textContent = text(compliance.agent_id); elements.tenant.textContent = text(compliance.tenant_id);
    elements.environment.textContent = text(compliance.environment); elements.boundary.textContent = text(compliance.assurance_boundary_id);
    elements.action.textContent = text(compliance.next_safe_action, "Inspect evidence and follow the recorded recovery guidance.");
    elements.evaluated.textContent = date(compliance.evaluated_at); elements.violation.textContent = date(compliance.last_violation_timestamp, "None reported");
    elements.updated.textContent = `Refreshed ${date(new Date().toISOString())}`;
    renderControls(compliance); renderReferences(compliance); renderTimeline(timeline); renderIncidents(incidents);
  }

  async function request(url, apiKey) {
    const response = await fetch(url, { headers: { "X-API-Key": apiKey, "Accept": "application/json" } });
    if (!response.ok) {
      let detail = "";
      try {
        const body = await response.json();
        detail = body.message || body.detail || body.error?.message || "";
      } catch (_) { /* Response body is not JSON. */ }
      throw new Error(`${response.status} ${response.statusText}${detail ? ` — ${detail}` : ""}`);
    }
    return response.json();
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const formData = new FormData(form);
    const apiKey = String(formData.get("apiKey") || "").trim();
    if (!apiKey) { apiKeyInput.focus(); setMessage("Enter an API key to load a protected assurance record.", "error"); return; }
    sessionStorage.setItem(KEY_STORAGE, apiKey);
    const base = String(formData.get("apiBase")).replace(/\/$/, "");
    const agentId = encodeURIComponent(String(formData.get("agentId")));
    const query = new URLSearchParams({ tenant_id: formData.get("tenantId"), environment: formData.get("environment"), assurance_boundary_id: formData.get("boundaryId") });
    connectButton.disabled = true; connectButton.textContent = "Loading assurance data…"; setMessage("Retrieving the compliance record, transition log, and incidents…", "loading");
    try {
      const [compliance, timelineResponse, incidentsResponse] = await Promise.all([
        request(`${base}/v1/agents/${agentId}/compliance?${query}`, apiKey),
        request(`${base}/v1/agents/${agentId}/timeline?${query}`, apiKey),
        request(`${base}/v1/agents/${agentId}/incidents?${query}`, apiKey)
      ]);
      render(compliance, Array.isArray(timelineResponse.items) ? timelineResponse.items : [], Array.isArray(incidentsResponse.items) ? incidentsResponse.items : []);
      setMessage("");
    } catch (error) {
      setMessage(`Unable to load assurance data. Check the API URL, selected identity, and key. ${error.message}`, "error");
    } finally {
      connectButton.disabled = false; connectButton.textContent = "Load assurance record";
    }
  });

  document.querySelector("#clear-key-button").addEventListener("click", () => {
    sessionStorage.removeItem(KEY_STORAGE); apiKeyInput.value = ""; apiKeyInput.focus(); setMessage("Saved API key cleared from this browser session.");
  });
})();
