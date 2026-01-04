let appState = null;
let parentToken = null;
let selectedTodayTask = null;
let selectedTemplateTask = null;

const CATEGORY_LABELS = {
  SCHOOLWORK: "Schoolwork",
  HYGIENE: "Hygiene",
  HELPFUL: "Helpful",
};

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2000);
}

async function loadState() {
  const board = document.getElementById("board");
  try {
    const response = await fetch("/api/state");
    if (!response.ok) {
      showToast("Failed to load state");
      board.innerHTML = "<div class=\"empty-message\">Unable to load tasks. Is the server running?</div>";
      return;
    }
    appState = await response.json();
    renderState();
  } catch (error) {
    board.innerHTML = "<div class=\"empty-message\">Unable to load tasks. Check the server connection.</div>";
  }
}

function renderState() {
  const dateEl = document.getElementById("date");
  dateEl.textContent = appState.date;

  const board = document.getElementById("board");
  board.innerHTML = "";

  if (!appState.children.length) {
    board.innerHTML = "<div class=\"empty-message\">No children found. Check the database seed data.</div>";
    return;
  }

  appState.children.forEach((child) => {
    const card = document.createElement("div");
    card.className = "child-card";

    const header = document.createElement("div");
    header.className = "child-header";

    const name = document.createElement("div");
    name.className = "child-name";
    name.textContent = child.name;
    header.appendChild(name);

    const progressRow = document.createElement("div");
    progressRow.className = "progress-row";
    const progressBar = document.createElement("div");
    progressBar.className = "progress-bar";
    const progressFill = document.createElement("span");
    progressFill.style.width = `${child.percent_complete}%`;
    progressBar.appendChild(progressFill);
    const percent = document.createElement("div");
    percent.className = "progress-percent";
    percent.textContent = `${child.percent_complete}%`;
    progressRow.appendChild(progressBar);
    progressRow.appendChild(percent);
    header.appendChild(progressRow);

    card.appendChild(header);

    if (child.unlocked) {
      const banner = document.createElement("div");
      banner.className = "unlock-banner";
      banner.textContent = "PLAYTIME UNLOCKED ✅";
      card.appendChild(banner);

      const reward = document.createElement("div");
      reward.className = "reward-text";
      reward.textContent = appState.daily_reward_text;
      card.appendChild(reward);
    }

    Object.keys(CATEGORY_LABELS).forEach((categoryKey) => {
      const section = document.createElement("div");
      section.className = "category";
      const title = document.createElement("div");
      title.className = "category-title";
      const progress = child.category_progress[categoryKey];
      title.textContent = `${CATEGORY_LABELS[categoryKey]} ${progress.approved}/${progress.total}`;
      section.appendChild(title);

      child.categories[categoryKey].forEach((task) => {
        const taskRow = document.createElement("div");
        taskRow.className = `task ${task.state.toLowerCase()}`;
        const left = document.createElement("div");
        left.className = "task-left";
        const check = document.createElement("div");
        check.className = "task-check";
        check.textContent = task.state === "APPROVED" ? "✓" : task.state === "PENDING" ? "…" : "";
        left.appendChild(check);
        const title = document.createElement("div");
        title.textContent = task.title;
        left.appendChild(title);
        if (!task.required) {
          const bonus = document.createElement("span");
          bonus.className = "bonus";
          bonus.textContent = "Bonus";
          left.appendChild(bonus);
        }
        taskRow.appendChild(left);

        const right = document.createElement("div");
        if (!task.required && task.reward_text) {
          const reward = document.createElement("span");
          reward.className = "reward";
          reward.textContent = task.reward_text;
          right.appendChild(reward);
        }
        taskRow.appendChild(right);

        if (task.state !== "APPROVED") {
          taskRow.addEventListener("click", () => toggleTask(child.id, task));
        }

        section.appendChild(taskRow);
      });

      card.appendChild(section);
    });

    board.appendChild(card);
  });
}

async function toggleTask(childId, task) {
  const endpoint = task.state === "PENDING"
    ? `/api/child/${childId}/tasks/${task.id}/unclaim`
    : `/api/child/${childId}/tasks/${task.id}/claim`;

  const optimisticState = task.state === "PENDING" ? "OPEN" : "PENDING";
  task.state = optimisticState;
  renderState();

  const response = await fetch(endpoint, { method: "POST" });
  if (!response.ok) {
    showToast("Unable to update task");
  }
  await loadState();
}

async function parentUnlock() {
  openPinModal();
}

function openPinModal() {
  const modal = document.getElementById("pinModal");
  const input = document.getElementById("pinInput");
  modal.classList.remove("hidden");
  input.value = "";
  input.focus();
}

function closePinModal() {
  document.getElementById("pinModal").classList.add("hidden");
}

async function submitPin() {
  const input = document.getElementById("pinInput");
  const pin = input.value.trim();
  if (!pin) {
    showToast("Enter a PIN");
    return;
  }
  const response = await fetch("/api/parent/unlock", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pin }),
  });
  if (!response.ok) {
    showToast("Invalid PIN");
    return;
  }
  const data = await response.json();
  parentToken = data.token;
  closePinModal();
  showParentPanel();
}

function showParentPanel() {
  document.getElementById("parentPanel").classList.remove("hidden");
  loadApprovals();
  loadTodayTasks();
  loadCompletedTasks();
  loadTemplates();
  loadSettings();
}

function closeParentPanel() {
  document.getElementById("parentPanel").classList.add("hidden");
}

async function fetchWithAuth(url, options = {}) {
  const headers = options.headers || {};
  headers.Authorization = `Bearer ${parentToken}`;
  return fetch(url, { ...options, headers });
}

async function loadApprovals() {
  const section = document.getElementById("tab-approvals");
  section.innerHTML = "";
  const response = await fetchWithAuth("/api/parent/pending");
  if (!response.ok) {
    section.textContent = "Unable to load pending tasks.";
    return;
  }
  const data = await response.json();
  const pending = data.pending;
  if (pending.length === 0) {
    section.textContent = "No pending tasks.";
    return;
  }

  const grid = document.createElement("div");
  grid.className = "panel-grid";
  const grouped = {};
  pending.forEach((task) => {
    grouped[task.child_name] = grouped[task.child_name] || [];
    grouped[task.child_name].push(task);
  });

  Object.entries(grouped).forEach(([childName, tasks]) => {
    const card = document.createElement("div");
    card.className = "panel-card";
    const title = document.createElement("h3");
    title.textContent = childName;
    card.appendChild(title);
    tasks.forEach((task) => {
      const row = document.createElement("div");
      row.className = "panel-task";
      const label = document.createElement("span");
      label.textContent = `${CATEGORY_LABELS[task.category]} - ${task.title}`;
      const actions = document.createElement("div");
      actions.className = "action-buttons";
      const approve = document.createElement("button");
      approve.className = "approve";
      approve.textContent = "Approve";
      approve.addEventListener("click", () => handleApprove(task.id));
      const reject = document.createElement("button");
      reject.className = "reject";
      reject.textContent = "Reject";
      reject.addEventListener("click", () => handleReject(task.id));
      actions.appendChild(approve);
      actions.appendChild(reject);
      row.appendChild(label);
      row.appendChild(actions);
      card.appendChild(row);
    });
    grid.appendChild(card);
  });

  section.appendChild(grid);
}

async function handleApprove(taskId) {
  await fetchWithAuth(`/api/parent/tasks/${taskId}/approve`, { method: "POST" });
  await loadState();
  loadApprovals();
}

async function handleReject(taskId) {
  await fetchWithAuth(`/api/parent/tasks/${taskId}/reject`, { method: "POST" });
  await loadState();
  loadApprovals();
}

async function loadCompletedTasks() {
  const section = document.getElementById("tab-completed");
  section.innerHTML = "";
  const response = await fetchWithAuth("/api/parent/completed");
  if (!response.ok) {
    section.textContent = "Unable to load completed tasks.";
    return;
  }
  const data = await response.json();
  const completed = data.completed;
  if (completed.length === 0) {
    section.textContent = "No completed tasks.";
    return;
  }

  const grid = document.createElement("div");
  grid.className = "panel-grid";
  const grouped = {};
  completed.forEach((task) => {
    grouped[task.child_name] = grouped[task.child_name] || [];
    grouped[task.child_name].push(task);
  });

  Object.entries(grouped).forEach(([childName, tasks]) => {
    const card = document.createElement("div");
    card.className = "panel-card";
    const title = document.createElement("h3");
    title.textContent = childName;
    card.appendChild(title);
    tasks.forEach((task) => {
      const row = document.createElement("div");
      row.className = "panel-task";
      const label = document.createElement("span");
      label.textContent = `${CATEGORY_LABELS[task.category]} - ${task.title}`;
      const actions = document.createElement("div");
      actions.className = "action-buttons";
      const revoke = document.createElement("button");
      revoke.className = "revoke";
      revoke.textContent = "Uncheck";
      revoke.addEventListener("click", () => handleRevoke(task.id));
      actions.appendChild(revoke);
      row.appendChild(label);
      row.appendChild(actions);
      card.appendChild(row);
    });
    grid.appendChild(card);
  });

  section.appendChild(grid);
}

async function handleRevoke(taskId) {
  await fetchWithAuth(`/api/parent/tasks/${taskId}/revoke`, { method: "POST" });
  await loadState();
  loadCompletedTasks();
}

function buildTodayForm() {
  const form = document.createElement("form");
  form.innerHTML = `
    <div class="form-row">
      <select name="child_id">
        <option value="">All Children</option>
        ${appState.children.map((child) => `<option value="${child.id}">${child.name}</option>`).join("")}
      </select>
      <select name="category">
        ${Object.keys(CATEGORY_LABELS).map((key) => `<option value="${key}">${CATEGORY_LABELS[key]}</option>`).join("")}
      </select>
      <input name="title" placeholder="Task title" required />
      <select name="required">
        <option value="true">Required</option>
        <option value="false">Bonus</option>
      </select>
    </div>
    <div class="form-row">
      <input name="reward_text" placeholder="Reward text (bonus only)" />
      <input name="sort_order" placeholder="Sort order" type="number" value="1" />
      <button type="submit">Add Task</button>
      <button type="button" id="clearTodayEdit">Clear Edit</button>
    </div>
  `;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = {
      child_id: formData.get("child_id") || null,
      category: formData.get("category"),
      title: formData.get("title"),
      required: formData.get("required") === "true",
      reward_text: formData.get("reward_text") || null,
      sort_order: Number(formData.get("sort_order")),
    };

    if (selectedTodayTask) {
      await fetchWithAuth(`/api/parent/today/tasks/${selectedTodayTask}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      await fetchWithAuth("/api/parent/today/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    selectedTodayTask = null;
    await loadState();
    loadTodayTasks();
  });

  form.querySelector("#clearTodayEdit").addEventListener("click", () => {
    selectedTodayTask = null;
    loadTodayTasks();
  });

  return form;
}

async function loadTodayTasks() {
  const section = document.getElementById("tab-today");
  section.innerHTML = "";
  const form = buildTodayForm();
  section.appendChild(form);

  const list = document.createElement("div");
  list.className = "panel-grid";

  appState.children.forEach((child) => {
    const card = document.createElement("div");
    card.className = "panel-card";
    const title = document.createElement("h3");
    title.textContent = child.name;
    card.appendChild(title);

    Object.keys(CATEGORY_LABELS).forEach((category) => {
      child.categories[category].forEach((task) => {
        const row = document.createElement("div");
        row.className = "panel-task";
        const label = document.createElement("span");
        label.textContent = `${CATEGORY_LABELS[category]} - ${task.title}`;
        const actions = document.createElement("div");
        actions.className = "action-buttons";
        const edit = document.createElement("button");
        edit.textContent = "Edit";
        edit.addEventListener("click", () => {
          selectedTodayTask = task.id;
          loadTodayTasks();
        });
        const del = document.createElement("button");
        del.textContent = "Delete";
        del.addEventListener("click", async () => {
          await fetchWithAuth(`/api/parent/today/tasks/${task.id}`, { method: "DELETE" });
          await loadState();
          loadTodayTasks();
        });
        actions.appendChild(edit);
        actions.appendChild(del);
        row.appendChild(label);
        row.appendChild(actions);
        card.appendChild(row);
      });
    });

    list.appendChild(card);
  });

  section.appendChild(list);

  if (selectedTodayTask) {
    const task = findTaskById(selectedTodayTask);
    if (task) {
      form.querySelector("input[name='title']").value = task.title;
      form.querySelector("select[name='category']").value = task.category;
      form.querySelector("select[name='required']").value = task.required ? "true" : "false";
      form.querySelector("input[name='reward_text']").value = task.reward_text || "";
      form.querySelector("input[name='sort_order']").value = task.sort_order || 1;
    }
  }
}

function findTaskById(taskId) {
  for (const child of appState.children) {
    for (const category of Object.keys(CATEGORY_LABELS)) {
      const task = child.categories[category].find((task) => task.id === taskId);
      if (task) {
        return task;
      }
    }
  }
  return null;
}

async function loadTemplates() {
  const section = document.getElementById("tab-templates");
  section.innerHTML = "";

  const response = await fetchWithAuth("/api/parent/templates");
  if (!response.ok) {
    section.textContent = "Unable to load templates.";
    return;
  }
  const data = await response.json();
  const templates = data.templates;

  const form = document.createElement("form");
  form.innerHTML = `
    <div class="form-row">
      <select name="template_type">
        <option value="WEEKDAY">Weekday</option>
        <option value="WEEKEND">Weekend</option>
      </select>
      <select name="category">
        ${Object.keys(CATEGORY_LABELS).map((key) => `<option value="${key}">${CATEGORY_LABELS[key]}</option>`).join("")}
      </select>
      <input name="title" placeholder="Task title" required />
      <select name="required">
        <option value="true">Required</option>
        <option value="false">Bonus</option>
      </select>
    </div>
    <div class="form-row">
      <input name="reward_text" placeholder="Reward text (bonus only)" />
      <input name="sort_order" placeholder="Sort order" type="number" value="1" />
      <button type="submit">Save Template Task</button>
      <button type="button" id="clearTemplateEdit">Clear Edit</button>
    </div>
  `;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = {
      template_type: formData.get("template_type"),
      category: formData.get("category"),
      title: formData.get("title"),
      required: formData.get("required") === "true",
      reward_text: formData.get("reward_text") || null,
      sort_order: Number(formData.get("sort_order")),
    };

    if (selectedTemplateTask) {
      await fetchWithAuth(`/api/parent/templates/tasks/${selectedTemplateTask}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      await fetchWithAuth("/api/parent/templates/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    selectedTemplateTask = null;
    loadTemplates();
  });

  form.querySelector("#clearTemplateEdit").addEventListener("click", () => {
    selectedTemplateTask = null;
    loadTemplates();
  });

  section.appendChild(form);

  const grid = document.createElement("div");
  grid.className = "panel-grid";

  const grouped = { WEEKDAY: [], WEEKEND: [] };
  templates.forEach((item) => grouped[item.template_type].push(item));

  Object.entries(grouped).forEach(([templateType, items]) => {
    const card = document.createElement("div");
    card.className = "panel-card";
    const title = document.createElement("h3");
    title.textContent = templateType === "WEEKDAY" ? "Weekday Template" : "Weekend Template";
    card.appendChild(title);
    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "panel-task";
      const label = document.createElement("span");
      label.textContent = `${CATEGORY_LABELS[item.category]} - ${item.title}`;
      const actions = document.createElement("div");
      actions.className = "action-buttons";
      const edit = document.createElement("button");
      edit.textContent = "Edit";
      edit.addEventListener("click", () => {
        selectedTemplateTask = item.id;
        loadTemplates();
      });
      const del = document.createElement("button");
      del.textContent = "Delete";
      del.addEventListener("click", async () => {
        await fetchWithAuth(`/api/parent/templates/tasks/${item.id}`, { method: "DELETE" });
        loadTemplates();
      });
      actions.appendChild(edit);
      actions.appendChild(del);
      row.appendChild(label);
      row.appendChild(actions);
      card.appendChild(row);
    });
    grid.appendChild(card);
  });

  section.appendChild(grid);

  if (selectedTemplateTask) {
    const item = templates.find((entry) => entry.id === selectedTemplateTask);
    if (item) {
      form.querySelector("select[name='template_type']").value = item.template_type;
      form.querySelector("select[name='category']").value = item.category;
      form.querySelector("input[name='title']").value = item.title;
      form.querySelector("select[name='required']").value = item.required ? "true" : "false";
      form.querySelector("input[name='reward_text']").value = item.reward_text || "";
      form.querySelector("input[name='sort_order']").value = item.sort_order || 1;
    }
  }
}

async function loadSettings() {
  const section = document.getElementById("tab-settings");
  section.innerHTML = "";
  const response = await fetchWithAuth("/api/parent/settings");
  if (!response.ok) {
    section.textContent = "Unable to load settings.";
    return;
  }
  const data = await response.json();
  const form = document.createElement("form");
  form.innerHTML = `
    <div class="form-row">
      <input name="daily_reward_text" placeholder="Daily reward text" value="${data.daily_reward_text}" />
      <input name="old_pin" placeholder="Old PIN" type="password" />
      <input name="new_pin" placeholder="New PIN" type="password" />
      <button type="submit">Save Settings</button>
    </div>
  `;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = {
      daily_reward_text: formData.get("daily_reward_text"),
      old_pin: formData.get("old_pin") || null,
      new_pin: formData.get("new_pin") || null,
    };
    await fetchWithAuth("/api/parent/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    showToast("Settings saved");
  });
  section.appendChild(form);
}

function setupTabs() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab-button").forEach((btn) => btn.classList.remove("active"));
      document.querySelectorAll(".tab-section").forEach((section) => section.classList.add("hidden"));
      button.classList.add("active");
      document.getElementById(`tab-${button.dataset.tab}`).classList.remove("hidden");
    });
  });
}

function setupListeners() {
  document.getElementById("parentButton").addEventListener("click", parentUnlock);
  document.getElementById("closeParent").addEventListener("click", closeParentPanel);
  document.getElementById("pinCancel").addEventListener("click", closePinModal);
  document.getElementById("pinSubmit").addEventListener("click", submitPin);
  document.getElementById("pinInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      submitPin();
    }
  });
  setupTabs();
}

setupListeners();
loadState();
setInterval(loadState, 60000);
