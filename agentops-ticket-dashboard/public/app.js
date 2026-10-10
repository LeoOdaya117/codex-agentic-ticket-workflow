const state = { tickets: [], runs: [] };
let ticketId = null;
let runId = null;
let selectedTab = "ticket.md";

const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
}[character]));

async function api(path, options) {
  const response = await fetch(path, options);
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || "Request failed");
  return value;
}

function post(data) {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  };
}

function badge(status) {
  const value = String(status ?? "").trim();
  const kind = /^done$/i.test(value)
    ? "done"
    : /ready|pass|finished/i.test(value)
      ? "good"
      : /fail|block|cancel/i.test(value) ? "bad" : "";
  return `<span class="tag ${kind}">${escapeHtml(status)}</span>`;
}

async function refresh() {
  try {
    const overview = await api("/api/overview");
    state.tickets = overview.tickets;
    state.runs = overview.runs;

    const connection = byId("connection");
    connection.textContent = "● Local connection active";
    connection.className = "connection online";
    byId("repo").textContent = overview.repo;
    byId("count-total").textContent = state.tickets.length;
    byId("count-active").textContent = overview.active_tickets ?? state.tickets.filter((ticket) =>
      ["investigating", "planning", "implementing", "code review", "qa testing"]
        .includes(String(ticket.status || "").trim().toLowerCase())).length;
    byId("count-ready").textContent = state.tickets.filter((ticket) => /ready.*verif/i.test(ticket.status)).length;
    byId("count-failed").textContent = state.tickets.filter((ticket) => /failed|blocked/i.test(ticket.status)).length;
    byId("ticket-count").textContent = `${state.tickets.length} found`;
    renderTickets();
    renderRuns();

    if (runId) await refreshEvents();
    if (ticketId) await loadDetail(false);
  } catch (error) {
    byId("connection").textContent = `● Connection error: ${error.message}`;
    byId("connection").className = "connection error";
  }
}

function renderTickets() {
  const container = byId("tickets");
  if (!state.tickets.length) {
    container.className = "empty";
    container.textContent = "No tickets yet. Use Create ticket or add tickets in your repository.";
    return;
  }

  container.className = "ticket-list";
  container.innerHTML = state.tickets.map((ticket) => `
    <article class="ticket ${ticket.id === ticketId ? "sel" : ""}"
      data-ticket-id="${escapeHtml(ticket.id)}" role="button" tabindex="0"
      aria-pressed="${ticket.id === ticketId}">
      <div class="line">
        <span class="tiny muted">${escapeHtml(ticket.id)} · ${escapeHtml(ticket.type)}</span>
        ${badge(ticket.status)}
      </div>
      <div class="ticket-title">${escapeHtml(ticket.title)}</div>
      <div class="line tiny muted">
        <span>Priority: ${escapeHtml(ticket.priority)}</span>
        <span>${ticket.checked}/${ticket.total} acceptance criteria</span>
      </div>
      <div class="progress"><i style="width:${ticket.total ? ticket.checked / ticket.total * 100 : 0}%"></i></div>
    </article>`).join("");
}

async function selectTicket(id) {
  ticketId = id;
  selectedTab = "ticket.md";
  await loadDetail(true);
  await refresh();
}

async function loadDetail(force) {
  const detail = await api(`/api/tickets/${encodeURIComponent(ticketId)}`);
  const isDone = String(detail.summary.status || "").trim().toLowerCase() === "done";
  const needsVerification = String(detail.summary.status || "").trim().toLowerCase() === "ready for human verification";
  byId("detail-heading").textContent = detail.summary.id;
  byId("process-button").hidden = isDone;
  byId("complete-button").hidden = !needsVerification;

  const keys = [...Object.keys(detail.files), ...detail.reports.map((report) => `agent-reports/${report.name}`)];
  if (!keys.includes(selectedTab)) selectedTab = keys[0] || "ticket.md";
  const content = detail.files[selectedTab]
    ?? detail.reports.find((report) => `agent-reports/${report.name}` === selectedTab)?.content
    ?? "";
  const html = `
    <div class="break">
      <b>${escapeHtml(detail.summary.title)}</b>
      <div class="detail-status">${badge(detail.summary.status)} &nbsp; <span class="muted tiny">${escapeHtml(detail.summary.priority)}</span></div>
    </div>
    <div class="tabs">${keys.map((key) => `
      <button class="${key === selectedTab ? "" : "secondary"}" data-tab="${escapeHtml(key)}" type="button">${escapeHtml(key)}</button>`).join("")}
    </div>
    <div class="pre">${escapeHtml(content || "No content")}</div>`;
  const snapshot = JSON.stringify([
    detail.summary.title, detail.summary.status, detail.summary.priority, keys, selectedTab, content,
  ]);

  if (force || byId("detail").dataset.snapshot !== snapshot) {
    const previous = byId("detail").querySelector(".pre");
    const scrollTop = previous?.scrollTop ?? 0;
    byId("detail").innerHTML = html;
    byId("detail").dataset.tab = selectedTab;
    byId("detail").dataset.ticket = ticketId;
    byId("detail").dataset.snapshot = snapshot;
    const updated = byId("detail").querySelector(".pre");
    if (updated) updated.scrollTop = scrollTop;
  }
}

function selectTab(tab) {
  selectedTab = tab;
  loadDetail(true);
}

function renderRuns() {
  const runs = [...state.runs].reverse();
  byId("runs").innerHTML = runs.slice(0, 15).map((run) => `
    <div class="ticket run-ticket ${run.id === runId ? "sel" : ""}" data-run-id="${escapeHtml(run.id)}" role="button" tabindex="0" aria-pressed="${run.id === runId}">
      <div class="line"><span class="tiny">${escapeHtml(run.mode)} · ${escapeHtml(run.ticket_id || "new ticket")}</span>${badge(run.status)}</div>
      <div class="tiny muted">${escapeHtml(run.id)} · ${escapeHtml(run.started)}</div>
    </div>`).join("") || '<div class="empty">No dashboard-started runs yet.</div>';

  const activeRun = runs.some((run) => run.id === runId && ["running", "launching"].includes(run.status));
  byId("stop-button").hidden = !runId || !activeRun;
}

function selectRun(id) {
  runId = id;
  renderRuns();
  refreshEvents();
}

async function refreshEvents() {
  try {
    const run = await api(`/api/runs/${encodeURIComponent(runId)}`);
    byId("events").classList.remove("empty");
    byId("events").innerHTML = (run.events || []).map((event) => `
      <div class="event"><span>${escapeHtml(event.time)}</span><br>${escapeHtml(event.message || JSON.stringify(event.payload) || event.kind)}</div>`)
      .join("") || '<div class="empty">Waiting for Codex events…</div>';
  } catch (error) {
    byId("events").textContent = error.message;
  }
}

function setTheme(theme, persist = true) {
  document.documentElement.dataset.theme = theme;
  byId("theme-light").setAttribute("aria-pressed", String(theme === "light"));
  byId("theme-dark").setAttribute("aria-pressed", String(theme === "dark"));
  if (persist) {
    try { localStorage.setItem("agentops-theme", theme); } catch { /* Storage may be unavailable. */ }
  }
}

function showCreate() {
  byId("new-dialog").showModal();
}

async function createTicket() {
  try {
    const result = await api("/api/run", post({
      mode: "create",
      description: byId("description").value,
      attachments: byId("attachments").value.split("\n").map((path) => path.trim()).filter(Boolean),
    }));
    byId("new-dialog").close();
    byId("description").value = "";
    runId = result.run_id;
    await refresh();
  } catch (error) {
    alert(error.message);
  }
}

async function runTicket() {
  try {
    const result = await api("/api/run", post({ mode: "process", ticket_id: ticketId }));
    runId = result.run_id;
    await refresh();
  } catch (error) {
    alert(error.message);
  }
}

async function completeTicket() {
  if (!ticketId || !confirm(`Mark ${ticketId} as Done? This records your explicit human approval.`)) return;
  const button = byId("complete-button");
  const message = byId("action-message");
  button.disabled = true;
  button.textContent = "Saving approval…";
  message.className = "action-message";
  message.textContent = "Recording your approval…";
  try {
    const result = await api(`/api/tickets/${encodeURIComponent(ticketId)}/complete`, post({}));
    await refresh();
    message.textContent = result.message || `${ticketId} marked Done.`;
  } catch (error) {
    message.className = "action-message error";
    message.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "✓ Mark Done";
  }
}

async function stopRun() {
  if (!confirm("Request termination of this Codex run?")) return;
  try {
    await api(`/api/stop/${encodeURIComponent(runId)}`, post({}));
    await refresh();
  } catch (error) {
    alert(error.message);
  }
}

byId("theme-light").addEventListener("click", () => setTheme("light"));
byId("theme-dark").addEventListener("click", () => setTheme("dark"));
byId("create-open-button").addEventListener("click", showCreate);
byId("create-ticket-button").addEventListener("click", createTicket);
byId("process-button").addEventListener("click", runTicket);
byId("complete-button").addEventListener("click", completeTicket);
byId("stop-button").addEventListener("click", stopRun);

byId("tickets").addEventListener("click", (event) => {
  const card = event.target.closest("[data-ticket-id]");
  if (card) selectTicket(card.dataset.ticketId);
});
byId("tickets").addEventListener("keydown", (event) => {
  const card = event.target.closest("[data-ticket-id]");
  if (card && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    selectTicket(card.dataset.ticketId);
  }
});
byId("runs").addEventListener("click", (event) => {
  const card = event.target.closest("[data-run-id]");
  if (card) selectRun(card.dataset.runId);
});
byId("runs").addEventListener("keydown", (event) => {
  const card = event.target.closest("[data-run-id]");
  if (card && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    selectRun(card.dataset.runId);
  }
});
byId("detail").addEventListener("click", (event) => {
  const tab = event.target.closest("[data-tab]");
  if (tab) selectTab(tab.dataset.tab);
});

setTheme(document.documentElement.dataset.theme || "dark", false);
refresh();
window.setInterval(refresh, 2000);
