const state = { tickets: [], runs: [], detail: null, repositories: [] };
const STATUS_ORDER = [
  "Open",
  "Investigating",
  "Planning",
  "Implementing",
  "Code Review",
  "QA Testing",
  "Ready for Human Verification",
  "Done",
  "Blocked",
];
let repoId = null;
let ticketId = null;
let selectedTab = "ticket.md";
let createFiles = [];

const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
}[character]));

async function api(path, options) {
  if (repoId && !["/api/repos", "/api/browse"].includes(path.split("?")[0])) {
    const separator = path.includes("?") ? "&" : "?";
    path = `${path}${separator}repo=${encodeURIComponent(repoId)}`;
  }
  const response = await fetch(path, options);
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || "Request failed");
  return value;
}

async function loadRepositories() {
  const response = await api("/api/repos");
  state.repositories = response.repos || [];
  repoId = state.repositories.some((repo) => repo.id === repoId) ? repoId : response.selected || state.repositories[0]?.id || null;
  try { if (repoId) localStorage.setItem("agentops-repo", repoId); } catch { /* Storage may be unavailable. */ }
  renderRepositories();
}

function renderRepositories() {
  const selected = state.repositories.find((repo) => repo.id === repoId);
  const trigger = byId("repo-picker-button");
  byId("repo-picker-name").textContent = selected?.name || "Choose a folder";
  trigger.disabled = !state.repositories.length;
  trigger.setAttribute("aria-label", selected
    ? `${selected.name}, connected folder. Show folders`
    : "Choose a connected folder");
  byId("repo-dropdown").innerHTML = state.repositories.map((repo) => `
    <button class="repo-option" id="repo-option-${escapeHtml(repo.id)}" type="button" role="option"
      data-repo-id="${escapeHtml(repo.id)}" aria-selected="${repo.id === repoId}" tabindex="-1">
      <span class="repo-option-name">${escapeHtml(repo.name)}</span>
      <span class="repo-option-path">${escapeHtml(repo.path)}</span>
      <svg class="repo-option-check" viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m4 10 4 4 8-8" /></svg>
    </button>`).join("") || '<div class="repo-dropdown-empty">No folders connected yet.</div>';
}

function repositoryOptions() {
  return [...byId("repo-dropdown").querySelectorAll('[role="option"]')];
}

function setRepositoryMenu(open, focusOption = false) {
  const trigger = byId("repo-picker-button");
  trigger.setAttribute("aria-expanded", String(open));
  trigger.classList.toggle("is-open", open);
  byId("repo-dropdown").hidden = !open;
  if (open && focusOption) {
    const options = repositoryOptions();
    (options.find((option) => option.getAttribute("aria-selected") === "true") || options[0])?.focus();
  }
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
    byId("repo").title = overview.repo;
    byId("count-total").textContent = state.tickets.length;
    byId("count-active").textContent = overview.active_tickets ?? state.tickets.filter((ticket) =>
      ["investigating", "planning", "implementing", "code review", "qa testing"]
        .includes(String(ticket.status || "").trim().toLowerCase())).length;
    byId("count-ready").textContent = state.tickets.filter((ticket) => /ready.*verif/i.test(ticket.status)).length;
    byId("count-failed").textContent = state.tickets.filter((ticket) => /failed|blocked/i.test(ticket.status)).length;
    renderTickets();

    if (ticketId) await loadDetail(false);
  } catch (error) {
    byId("connection").textContent = `● Connection error: ${error.message}`;
    byId("connection").className = "connection error";
  }
}

async function selectRepository(id) {
  if (!id || id === repoId) return;
  repoId = id;
  try { localStorage.setItem("agentops-repo", repoId); } catch { /* Storage may be unavailable. */ }
  renderRepositories();
  ticketId = null;
  selectedTab = "ticket.md";
  state.detail = null;
  byId("detail-heading").textContent = "Ticket details";
  byId("process-button").hidden = true;
  byId("request-changes-button").hidden = true;
  byId("complete-button").hidden = true;
  byId("action-message").textContent = "";
  byId("detail").className = "empty";
  byId("detail").textContent = "Select a ticket to see its reports and QA evidence.";
  byId("ticket-detail-dialog").close();
  await refresh();
}

function showAddRepository() {
  byId("repo-path").value = "";
  byId("repo-add-message").textContent = "";
  byId("repo-picker-status").textContent = "";
  byId("repo-dialog").showModal();
}

async function browseRepository() {
  const status = byId("repo-picker-status");
  status.textContent = "Choose a folder in the system dialog…";
  try {
    const result = await api("/api/browse");
    if (result.path) byId("repo-path").value = result.path;
    status.textContent = result.path ? "Folder selected" : "No folder selected";
  } catch (error) {
    status.textContent = error.message;
  }
}

async function connectRepository() {
  const button = byId("connect-repo-button");
  const message = byId("repo-add-message");
  button.disabled = true;
  message.className = "action-message";
  message.textContent = "Connecting folder…";
  try {
    const repo = await api("/api/repos", post({ path: byId("repo-path").value.trim() }));
    repoId = repo.id;
    await loadRepositories();
    byId("repo-dialog").close();
    ticketId = null;
    byId("ticket-detail-dialog").close();
    await refresh();
  } catch (error) {
    message.className = "action-message error";
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

function renderTickets() {
  const container = byId("status-board");
  const horizontalScroll = container.scrollLeft;
  const columnScroll = new Map([...container.querySelectorAll(".status-column")].map((column) => [
    column.querySelector("h2")?.textContent,
    column.querySelector(".status-cards")?.scrollTop || 0,
  ]));
  const extraStatuses = [...new Set(
    state.tickets
    .map((ticket) => String(ticket.status || "Open").trim())
    .filter((status) => !STATUS_ORDER.some((known) => known.toLowerCase() === status.toLowerCase())),
  )].sort((a, b) => a.localeCompare(b));
  const statuses = [...STATUS_ORDER, ...extraStatuses];
  container.className = "status-board";
  container.innerHTML = statuses.map((status, index) => {
    const tickets = state.tickets.filter((ticket) =>
      String(ticket.status || "Open").trim().toLowerCase() === status.toLowerCase());
    const cards = tickets.map((ticket) => {
      const focusQa = /qa testing|ready for human verification|done/i.test(String(ticket.status || ""));
      const priority = String(ticket.priority || "Unassigned").trim();
      const priorityLabel = priority.replace(/\s*\(proposed;\s*triage required\)/i, " · proposed");
      return `
        <article class="ticket kanban-ticket ${ticket.id === ticketId ? "sel" : ""}"
          data-ticket-id="${escapeHtml(ticket.id)}" data-focus-qa="${focusQa}"
          role="button" tabindex="0" aria-pressed="${ticket.id === ticketId}"
          aria-label="${escapeHtml(ticket.id)} ${escapeHtml(ticket.title)}, priority ${escapeHtml(ticket.priority)}">
          <div class="line ticket-meta">
            <span class="tiny muted">${escapeHtml(ticket.id)} · ${escapeHtml(ticket.type)}</span>
            <span class="tag priority-tag" title="${escapeHtml(priority)}">${escapeHtml(priorityLabel)}</span>
          </div>
          <div class="ticket-title">${escapeHtml(ticket.title)}</div>
          <div class="ticket-progress-label tiny muted">${ticket.checked}/${ticket.total} acceptance criteria</div>
          <div class="progress"><i style="width:${ticket.total ? ticket.checked / ticket.total * 100 : 0}%"></i></div>
        </article>`;
    }).join("");
    return `
      <section class="status-column" data-status="${escapeHtml(status.toLowerCase().replaceAll(" ", "-"))}" aria-labelledby="status-heading-${index}">
        <header class="status-column-heading">
          <h2 id="status-heading-${index}">${escapeHtml(status)}</h2>
          <span class="lane-count">${tickets.length}</span>
        </header>
        <div class="status-cards">${cards || '<div class="column-empty">No tickets</div>'}</div>
      </section>`;
  }).join("");
  container.scrollLeft = horizontalScroll;
  for (const column of container.querySelectorAll(".status-column")) {
    column.querySelector(".status-cards").scrollTop = columnScroll.get(column.querySelector("h2").textContent) || 0;
  }
}

async function selectTicket(id, focusQa = false) {
  ticketId = id;
  selectedTab = "ticket.md";
  await loadDetail(true, focusQa);
  byId("ticket-detail-dialog").showModal();
  await refresh();
}

async function loadDetail(force, focusQa = false) {
  const detail = await api(`/api/tickets/${encodeURIComponent(ticketId)}`);
  state.detail = detail;
  const isDone = String(detail.summary.status || "").trim().toLowerCase() === "done";
  const needsVerification = String(detail.summary.status || "").trim().toLowerCase() === "ready for human verification";
  const hasActiveProcess = state.runs.some((run) => run.ticket_id === ticketId
    && run.mode === "process" && ["launching", "running", "cancelling"].includes(run.status));
  byId("detail-ticket-id").textContent = detail.summary.id;
  byId("process-button").hidden = isDone || hasActiveProcess;
  byId("request-changes-button").hidden = !needsVerification;
  byId("complete-button").hidden = !needsVerification;

  const keys = [...Object.keys(detail.files), ...detail.reports.map((report) => `agent-reports/${report.name}`)];
  if (focusQa) {
    selectedTab = ["qa-report.md", "verification.md"].find((name) => keys.includes(name))
      || keys.find((name) => name.startsWith("agent-reports/"))
      || keys[0]
      || "ticket.md";
  }
  if (!keys.includes(selectedTab)) selectedTab = keys[0] || "ticket.md";
  const content = detail.files[selectedTab]
    ?? detail.reports.find((report) => `agent-reports/${report.name}` === selectedTab)?.content
    ?? "";
  const pullRequest = /^https:\/\//i.test(String(detail.summary.pull_request || ""))
    ? `<p class="detail-pr"><a href="${escapeHtml(detail.summary.pull_request)}" target="_blank" rel="noopener noreferrer">Open pull request for human testing ↗</a></p>`
    : "";
  const html = `
    <div class="break">
      <b>${escapeHtml(detail.summary.title)}</b>
      <div class="detail-status">${badge(detail.summary.status)} &nbsp; <span class="muted tiny">${escapeHtml(detail.summary.priority)}</span></div>
    </div>
    ${pullRequest}
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

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function renderCreateFiles() {
  const list = byId("create-attachment-list");
  list.replaceChildren();
  if (!createFiles.length) {
    const empty = document.createElement("li");
    empty.textContent = "No files selected.";
    list.append(empty);
    byId("create-dropzone-help").textContent = "Up to 10 files and 20 MB total";
    return;
  }
  createFiles.forEach((file, index) => {
    const item = document.createElement("li");
    const name = document.createElement("span");
    name.className = "attachment-file-name";
    name.textContent = file.name;
    const size = document.createElement("span");
    size.className = "attachment-file-size muted";
    size.textContent = formatFileSize(file.size);
    const remove = document.createElement("button");
    remove.className = "secondary attachment-remove";
    remove.type = "button";
    remove.textContent = "Remove";
    remove.setAttribute("aria-label", `Remove ${file.name}`);
    remove.addEventListener("click", () => {
      createFiles.splice(index, 1);
      renderCreateFiles();
    });
    item.append(name, size, remove);
    list.append(item);
  });
  const total = createFiles.reduce((sum, file) => sum + file.size, 0);
  const help = byId("create-dropzone-help");
  help.textContent = `${createFiles.length} of 10 files · ${formatFileSize(total)} of 20 MB`;
}

function addCreateFiles(files) {
  const incoming = [...files];
  const combined = [...createFiles, ...incoming];
  const totalSize = combined.reduce((sum, file) => sum + file.size, 0);
  if (combined.length > 10) {
    byId("create-message").className = "action-message error";
    byId("create-message").textContent = "Choose no more than 10 files.";
    return;
  }
  if (totalSize > 20 * 1024 * 1024) {
    byId("create-message").className = "action-message error";
    byId("create-message").textContent = "Attachments must total 20 MB or less.";
    return;
  }
  createFiles = combined;
  byId("create-message").textContent = "";
  byId("create-message").className = "action-message";
  renderCreateFiles();
}

async function createTicket() {
  const button = byId("create-ticket-button");
  const message = byId("create-message");
  button.disabled = true;
  button.textContent = "Starting…";
  message.className = "action-message";
  message.textContent = "Uploading attachments and starting the ticket run…";
  try {
    const form = new FormData();
    form.append("mode", "create");
    form.append("description", byId("description").value);
    form.append("attachment_paths", JSON.stringify(byId("attachments").value.split("\n").map((path) => path.trim()).filter(Boolean)));
    for (const file of createFiles) form.append("attachments", file, file.name);
    await api("/api/run", { method: "POST", body: form });
    byId("new-dialog").close();
    byId("description").value = "";
    byId("attachments").value = "";
    byId("create-attachments").value = "";
    createFiles = [];
    renderCreateFiles();
    await refresh();
  } catch (error) {
    message.className = "action-message error";
    message.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "Create with Codex";
  }
}

function initCreateDropzone() {
  const zone = byId("create-dropzone");
  const input = byId("create-attachments");
  zone.addEventListener("click", (event) => {
    if (event.target !== input) input.click();
  });
  zone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      input.click();
    }
  });
  input.addEventListener("change", () => {
    addCreateFiles(input.files);
    input.value = "";
  });
  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    zone.classList.add("is-dragging");
  });
  zone.addEventListener("dragleave", (event) => {
    if (!zone.contains(event.relatedTarget)) zone.classList.remove("is-dragging");
  });
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("is-dragging");
    addCreateFiles(event.dataTransfer.files);
  });
}

async function runTicket() {
  try {
    await api("/api/run", post({ mode: "process", ticket_id: ticketId }));
    await refresh();
  } catch (error) {
    alert(error.message);
  }
}

async function completeTicket() {
  if (!ticketId || !confirm(`Approve ${ticketId} after testing its pull request? This records your acceptance and leaves the PR open for your merge decision.`)) return;
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
    button.textContent = "✓ Approve after test";
  }
}

function showRejection() {
  byId("rejection-description").value = "";
  byId("rejection-attachments").value = "";
  byId("rejection-attachment-list").textContent = "No attachments selected.";
  byId("rejection-message").textContent = "";
  byId("rejection-message").className = "action-message";
  byId("reject-dialog").showModal();
}

function formatFileSize(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function updateAttachmentFilter() {
  const input = byId("rejection-attachments");
  const type = byId("rejection-attachment-type").value;
  input.accept = type === "images" ? "image/*" : type === "files"
    ? ".pdf,.md,.txt,.log,.json,.yaml,.yml,.csv,.zip,.doc,.docx,.xls,.xlsx,.ppt,.pptx,text/*,application/*"
    : "";
}

function updateAttachmentList() {
  const files = [...byId("rejection-attachments").files];
  byId("rejection-attachment-list").textContent = files.length
    ? files.map((file) => `${file.name} · ${formatFileSize(file.size)}`).join("\n")
    : "No attachments selected.";
}

async function rejectTicket() {
  const description = byId("rejection-description").value.trim();
  if (!description) {
    byId("rejection-message").className = "action-message error";
    byId("rejection-message").textContent = "Describe what needs correction before reopening the ticket.";
    byId("rejection-description").focus();
    return;
  }
  if (!ticketId || !confirm(`Reject ${ticketId} and reopen it for corrections? This will save your feedback and start a Codex correction run.`)) return;

  const button = byId("reject-ticket-button");
  const message = byId("rejection-message");
  button.disabled = true;
  button.textContent = "Reopening ticket…";
  message.className = "action-message";
  message.textContent = "Saving feedback and attachments…";
  try {
    const form = new FormData();
    form.append("description", description);
    for (const file of byId("rejection-attachments").files) form.append("attachments", file, file.name);
    const result = await api(`/api/tickets/${encodeURIComponent(ticketId)}/reject`, { method: "POST", body: form });
    byId("reject-dialog").close();
    await refresh();
    byId("action-message").className = "action-message";
    byId("action-message").textContent = result.message;
  } catch (error) {
    message.className = "action-message error";
    message.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "Reopen & start corrections";
  }
}

byId("theme-light").addEventListener("click", () => setTheme("light"));
byId("theme-dark").addEventListener("click", () => setTheme("dark"));
byId("create-open-button").addEventListener("click", showCreate);
byId("create-ticket-button").addEventListener("click", createTicket);
initCreateDropzone();
byId("process-button").addEventListener("click", runTicket);
byId("complete-button").addEventListener("click", completeTicket);
byId("request-changes-button").addEventListener("click", showRejection);
byId("reject-ticket-button").addEventListener("click", rejectTicket);
byId("rejection-attachment-type").addEventListener("change", updateAttachmentFilter);
byId("rejection-attachments").addEventListener("change", updateAttachmentList);
byId("repo-picker-button").addEventListener("click", () => {
  const open = byId("repo-picker-button").getAttribute("aria-expanded") !== "true";
  setRepositoryMenu(open, open);
});
byId("repo-picker-button").addEventListener("keydown", (event) => {
  if (["ArrowDown", "ArrowUp"].includes(event.key)) {
    event.preventDefault();
    setRepositoryMenu(true, true);
  } else if (event.key === "Escape") {
    setRepositoryMenu(false);
  }
});
byId("repo-dropdown").addEventListener("click", (event) => {
  const option = event.target.closest("[data-repo-id]");
  if (!option) return;
  setRepositoryMenu(false);
  selectRepository(option.dataset.repoId);
});
byId("repo-dropdown").addEventListener("keydown", (event) => {
  const options = repositoryOptions();
  const currentIndex = options.indexOf(event.target.closest('[role="option"]'));
  let nextIndex = currentIndex;
  if (event.key === "ArrowDown") nextIndex = Math.min(options.length - 1, currentIndex + 1);
  else if (event.key === "ArrowUp") nextIndex = Math.max(0, currentIndex - 1);
  else if (event.key === "Home") nextIndex = 0;
  else if (event.key === "End") nextIndex = options.length - 1;
  else if (event.key === "Escape") {
    event.preventDefault();
    setRepositoryMenu(false);
    byId("repo-picker-button").focus();
    return;
  } else if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    event.target.closest('[role="option"]')?.click();
    return;
  } else return;
  event.preventDefault();
  options[nextIndex]?.focus();
});
document.addEventListener("pointerdown", (event) => {
  if (!byId("repo-picker").contains(event.target)) setRepositoryMenu(false);
});
byId("repo-picker").addEventListener("focusout", () => {
  window.setTimeout(() => {
    if (!byId("repo-picker").contains(document.activeElement)) setRepositoryMenu(false);
  }, 0);
});
byId("add-repo-button").addEventListener("click", showAddRepository);
byId("browse-repo-button").addEventListener("click", browseRepository);
byId("connect-repo-button").addEventListener("click", connectRepository);
byId("status-board").addEventListener("click", (event) => {
  const card = event.target.closest("[data-ticket-id]");
  if (card) selectTicket(card.dataset.ticketId, card.dataset.focusQa === "true");
});
byId("status-board").addEventListener("keydown", (event) => {
  const card = event.target.closest("[data-ticket-id]");
  if (card && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    selectTicket(card.dataset.ticketId, card.dataset.focusQa === "true");
  }
});
byId("detail").addEventListener("click", (event) => {
  const tab = event.target.closest("[data-tab]");
  if (tab) selectTab(tab.dataset.tab);
});

setTheme(document.documentElement.dataset.theme || "dark", false);
try { repoId = localStorage.getItem("agentops-repo"); } catch { /* Storage may be unavailable. */ }
loadRepositories().then(refresh).catch((error) => {
  byId("connection").textContent = `● Connection error: ${error.message}`;
  byId("connection").className = "connection error";
});
window.setInterval(refresh, 2000);
