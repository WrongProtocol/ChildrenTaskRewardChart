/**
 * Home Rewards Kiosk - Frontend JavaScript
 * 
 * Main UI logic for the kiosk display and parent admin panel.
 * Handles:
 * - Child task display with real-time progress tracking
 * - Child task claiming/unclaiming (optimistic updates)
 * - Parent authentication (PIN → token)
 * - Parent admin panel: approvals, today's tasks, templates, settings
 */

// ============================================
// GLOBAL STATE & CONFIGURATION
// ============================================

/** @type {Object} Current complete kiosk state from /api/state */
let appState = null;

/** @type {String|null} Parent authentication token (Bearer token) */
let parentToken = null;

/** @type {Number|null} ID of today's task being edited, if any */
let selectedTodayTask = null;

/** @type {Number|null} ID of template task being edited, if any */
let selectedTemplateTask = null;

/** Map of task category keys to display labels */
const CATEGORY_LABELS = {
  SCHOOLWORK: "Schoolwork",
  HYGIENE: "Hygiene",
  HELPFUL: "Helpful",
};

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Display a temporary toast notification message
 * @param {string} message - Message to display
 */
function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2000);
}

// ============================================
// MAIN STATE & RENDERING
// ============================================

/**
 * Fetch complete kiosk state from server and render the main display
 * Called on page load and after any task state changes
 */
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

/**
 * Render the main kiosk display with all children and their tasks
 * Shows:
 * - Current date
 * - Each child's progress bar and task list organized by category
 * - Unlock banner and reward text if all required tasks are approved
 * - Task states with visual indicators (Open, Pending, Approved)
 */
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
    // Create child card container
    const card = document.createElement("div");
    card.className = "child-card";

    // Create header with name and progress bar
    const header = document.createElement("div");
    header.className = "child-header";

    const name = document.createElement("div");
    name.className = "child-name";
    name.textContent = child.name;
    header.appendChild(name);

    // Progress bar showing % of tasks approved
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

    // Show unlock banner if all required tasks approved
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

    // Render tasks organized by category
    Object.keys(CATEGORY_LABELS).forEach((categoryKey) => {
      const section = document.createElement("div");
      section.className = "category";
      const title = document.createElement("div");
      title.className = "category-title";
      const progress = child.category_progress[categoryKey];
      // Show category progress like "Schoolwork 2/5"
      title.textContent = `${CATEGORY_LABELS[categoryKey]} ${progress.approved}/${progress.total}`;
      section.appendChild(title);

      child.categories[categoryKey].forEach((task) => {
        const taskRow = document.createElement("div");
        taskRow.className = `task ${task.state.toLowerCase()}`;  // CSS class for state styling
        const left = document.createElement("div");
        left.className = "task-left";
        
        // Checkmark indicator: ✓ for approved, … for pending, blank for open
        const check = document.createElement("div");
        check.className = "task-check";
        check.textContent = task.state === "APPROVED" ? "✓" : task.state === "PENDING" ? "…" : "";
        left.appendChild(check);
        
        const titleEl = document.createElement("div");
        titleEl.textContent = task.title;
        left.appendChild(titleEl);
        
        // Show "Bonus" label for non-required tasks
        if (!task.required) {
          const bonus = document.createElement("span");
          bonus.className = "bonus";
          bonus.textContent = "Bonus";
          left.appendChild(bonus);
        }
        taskRow.appendChild(left);

        // Right side: reward text for bonus tasks
        const right = document.createElement("div");
        if (!task.required && task.reward_text) {
          const reward = document.createElement("span");
          reward.className = "reward";
          reward.textContent = task.reward_text;
          right.appendChild(reward);
        }
        taskRow.appendChild(right);

        // Add click handler to claim/unclaim task (not for already approved)
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

// ============================================
// TASK INTERACTION (Child claiming/unclaiming)
// ============================================

/**
 * Toggle task state between OPEN and PENDING
 * Uses optimistic update: immediately shows new state, then validates with server
 * 
 * @param {number} childId - ID of child claiming/unclaiming
 * @param {object} task - Task object with current state
 */
async function toggleTask(childId, task) {
  // Determine endpoint: unclaim if pending, claim if open
  const endpoint = task.state === "PENDING"
    ? `/api/child/${childId}/tasks/${task.id}/unclaim`
    : `/api/child/${childId}/tasks/${task.id}/claim`;

  // Optimistic update: immediately change UI without waiting for server
  const optimisticState = task.state === "PENDING" ? "OPEN" : "PENDING";
  task.state = optimisticState;
  renderState();

  // Send request to server
  const response = await fetch(endpoint, { method: "POST" });
  if (!response.ok) {
    showToast("Unable to update task");
  }
  // Reload state from server to confirm changes
  await loadState();
}

// ============================================
// PARENT AUTHENTICATION & PANEL
// ============================================

/**
 * Initiate parent unlock flow - show PIN entry modal
 */
async function parentUnlock() {
  openPinModal();
}

/**
 * Display PIN entry modal dialog
 */
function openPinModal() {
  const modal = document.getElementById("pinModal");
  const input = document.getElementById("pinInput");
  modal.classList.remove("hidden");
  input.value = "";
  input.focus();
}

/**
 * Close PIN entry modal dialog
 */
function closePinModal() {
  document.getElementById("pinModal").classList.add("hidden");
}

/**
 * Handle PIN submission - authenticate and get token
 * Called when parent submits PIN in modal
 */
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
  parentToken = data.token;  // Store token for authenticated requests
  closePinModal();
  showParentPanel();
}

/**
 * Display parent admin panel and load all tabs
 */
function showParentPanel() {
  document.getElementById("parentPanel").classList.remove("hidden");
  loadApprovals();
  loadTodayTasks();
  loadCompletedTasks();
  loadTemplates();
  loadSettings();
}

/**
 * Close parent admin panel
 */
function closeParentPanel() {
  document.getElementById("parentPanel").classList.add("hidden");
}

/**
 * Make authenticated fetch request using stored parent token
 * @param {string} url - API endpoint URL
 * @param {object} options - Fetch options (method, body, headers, etc.)
 * @returns {Promise} Fetch response
 */
async function fetchWithAuth(url, options = {}) {
  const headers = options.headers || {};
  headers.Authorization = `Bearer ${parentToken}`;
  return fetch(url, { ...options, headers });
}

async function loadApprovals() {
  const section = document.getElementById("tab-approvals");
  section.innerHTML = "";
  const response = await fetchWithAuth("/api/parent/pending");
  // Validate API response - show error if request failed
  if (!response.ok) {
    section.textContent = "Unable to load pending tasks.";
    return;
  }
  // Extract pending tasks from response
  const data = await response.json();
  const pending = data.pending;
  
  // Show empty state if no pending tasks exist
  if (pending.length === 0) {
    section.textContent = "No pending tasks.";
    return;
  }

  // Create container grid for grouping tasks by child
  const grid = document.createElement("div");
  grid.className = "panel-grid";
  
  // Group tasks by child_name for cleaner UI presentation
  // Groups pending tasks so all tasks from one child are together
  const grouped = {};
  pending.forEach((task) => {
    grouped[task.child_name] = grouped[task.child_name] || [];
    grouped[task.child_name].push(task);
  });

  // Iterate through each child's grouped tasks and create approval cards
  Object.entries(grouped).forEach(([childName, tasks]) => {
    // Create a card container for this child's pending tasks
    const card = document.createElement("div");
    card.className = "panel-card";
    
    // Add child name as card title
    const title = document.createElement("h3");
    title.textContent = childName;
    card.appendChild(title);
    
    // For each pending task, build a task row with action buttons
    tasks.forEach((task) => {
      const row = document.createElement("div");
      row.className = "panel-task";
      
      // Task display label shows category and title
      const label = document.createElement("span");
      label.textContent = `${CATEGORY_LABELS[task.category]} - ${task.title}`;
      
      // Create action buttons container for approve/reject
      const actions = document.createElement("div");
      actions.className = "action-buttons";
      
      // Approve button - sends POST to /api/parent/tasks/{id}/approve endpoint
      const approve = document.createElement("button");
      approve.className = "approve";
      approve.textContent = "Approve";
      approve.addEventListener("click", () => handleApprove(task.id));
      
      // Reject button - sends POST to /api/parent/tasks/{id}/reject endpoint
      const reject = document.createElement("button");
      reject.className = "reject";
      reject.textContent = "Reject";
      reject.addEventListener("click", () => handleReject(task.id));
      
      // Assemble the task row
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

/**
 * Approve a pending task by sending POST request to backend
 * Transitions task from PENDING state to APPROVED
 * @param {number} taskId - ID of the task to approve
 */
async function handleApprove(taskId) {
  await fetchWithAuth(`/api/parent/tasks/${taskId}/approve`, { method: "POST" });
  // Refresh kiosk state to show updated task status
  await loadState();
  // Refresh approvals tab to remove approved task from pending list
  loadApprovals();
}

/**
 * Reject a pending task by sending POST request to backend
 * Transitions task from PENDING state back to OPEN (can be claimed again)
 * @param {number} taskId - ID of the task to reject
 */
async function handleReject(taskId) {
  await fetchWithAuth(`/api/parent/tasks/${taskId}/reject`, { method: "POST" });
  // Refresh kiosk state to show updated task status
  await loadState();
  // Refresh approvals tab to remove rejected task from pending list
  loadApprovals();
}

/**
 * Load and display completed (approved) tasks for parent management
 * Allows parent to view and revoke (unchecked) completed tasks
 * Fetches list from /api/parent/completed endpoint
 */
async function loadCompletedTasks() {
  const section = document.getElementById("tab-completed");
  section.innerHTML = "";
  
  // Fetch completed tasks from backend
  const response = await fetchWithAuth("/api/parent/completed");
  
  // Validate response and show error if request failed
  if (!response.ok) {
    section.textContent = "Unable to load completed tasks.";
    return;
  }
  
  // Extract completed tasks data
  const data = await response.json();
  const completed = data.completed;
  
  // Show empty state if no completed tasks
  if (completed.length === 0) {
    section.textContent = "No completed tasks.";
    return;
  }

  // Create container grid for organizing completed tasks by child
  const grid = document.createElement("div");
  grid.className = "panel-grid";
  
  // Group completed tasks by child_name for organized display
  const grouped = {};
  completed.forEach((task) => {
    grouped[task.child_name] = grouped[task.child_name] || [];
    grouped[task.child_name].push(task);
  });

  // Iterate through each child's completed tasks and build cards
  Object.entries(grouped).forEach(([childName, tasks]) => {
    // Create card for this child's completed tasks
    const card = document.createElement("div");
    card.className = "panel-card";
    
    // Add child name as card header
    const title = document.createElement("h3");
    title.textContent = childName;
    card.appendChild(title);
    
    // Build task rows with revoke button for each completed task
    tasks.forEach((task) => {
      const row = document.createElement("div");
      row.className = "panel-task";
      
      // Display task category and title
      const label = document.createElement("span");
      label.textContent = `${CATEGORY_LABELS[task.category]} - ${task.title}`;
      
      // Create action buttons container
      const actions = document.createElement("div");
      actions.className = "action-buttons";
      
      // Revoke button - allows parent to unchecked/revert completed task
      // This sends POST to /api/parent/tasks/{id}/revoke endpoint
      const revoke = document.createElement("button");
      revoke.className = "revoke";
      revoke.textContent = "Uncheck";
      revoke.addEventListener("click", () => handleRevoke(task.id));
      
      // Assemble task row
      actions.appendChild(revoke);
      row.appendChild(label);
      row.appendChild(actions);
      card.appendChild(row);
    });
    grid.appendChild(card);
  });

  section.appendChild(grid);
}

/**
 * Revoke (uncheck) a completed task by sending POST request to backend
 * Transitions task from APPROVED state back to PENDING for re-evaluation
 * @param {number} taskId - ID of the task to revoke
 */
async function handleRevoke(taskId) {
  await fetchWithAuth(`/api/parent/tasks/${taskId}/revoke`, { method: "POST" });
  // Refresh kiosk state to reflect revoked task status
  await loadState();
  // Refresh completed tasks tab to remove revoked task from list
  loadCompletedTasks();
}

// ============================================
// TODAY'S TASKS CRUD - CREATE, READ, UPDATE, DELETE
// ============================================

/**
 * Build form UI for creating or editing today's daily tasks
 * Supports creating tasks for specific child or all children
 * Tasks can be required or bonus with optional reward text
 * @returns {HTMLFormElement} Form element with task creation/edit fields
 */
function buildTodayForm() {
  const form = document.createElement("form");
  // Build form HTML with dropdowns and input fields for task configuration
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
  
  // Handle form submission for creating or updating today's task
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    
    // Build task payload from form fields
    const payload = {
      child_id: formData.get("child_id") || null,  // null means apply to all children
      category: formData.get("category"),
      title: formData.get("title"),
      required: formData.get("required") === "true",  // Boolean conversion
      reward_text: formData.get("reward_text") || null,  // Optional reward label
      sort_order: Number(formData.get("sort_order")),
    };

    // If editing an existing task, send PUT request; otherwise POST for new task
    if (selectedTodayTask) {
      await fetchWithAuth(`/api/parent/today/tasks/${selectedTodayTask}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      // Create new task via POST request
      await fetchWithAuth("/api/parent/today/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    // Clear selection, refresh state, and reload UI
    selectedTodayTask = null;
    await loadState();
    loadTodayTasks();
  });

  // Handle "Clear Edit" button - resets form and selected task
  form.querySelector("#clearTodayEdit").addEventListener("click", () => {
    selectedTodayTask = null;
    loadTodayTasks();
  });

  return form;
}

/**
 * Load and display today's tasks for the current day
 * Shows tasks for each child organized by category
 * Allows parent to create, edit, and delete today's tasks
 */
async function loadTodayTasks() {
  const section = document.getElementById("tab-today");
  section.innerHTML = "";
  
  // Build and display the task creation/edit form
  const form = buildTodayForm();
  section.appendChild(form);

  // Create container grid for organizing today's tasks by child
  const list = document.createElement("div");
  list.className = "panel-grid";

  // Iterate through each child to display their today's tasks
  appState.children.forEach((child) => {
    // Create a card for this child's daily tasks
    const card = document.createElement("div");
    card.className = "panel-card";
    const title = document.createElement("h3");
    title.textContent = child.name;
    card.appendChild(title);

    // Organize tasks by category within each child's card
    Object.keys(CATEGORY_LABELS).forEach((category) => {
      // Display each task in this category for this child
      child.categories[category].forEach((task) => {
        const row = document.createElement("div");
        row.className = "panel-task";
        
        // Task label shows category and title
        const label = document.createElement("span");
        label.textContent = `${CATEGORY_LABELS[category]} - ${task.title}`;
        
        // Create action buttons for edit and delete
        const actions = document.createElement("div");
        actions.className = "action-buttons";
        
        // Edit button - sets selectedTodayTask and reloads to pre-fill form
        const edit = document.createElement("button");
        edit.textContent = "Edit";
        edit.addEventListener("click", () => {
          selectedTodayTask = task.id;
          loadTodayTasks();
        });
        
        // Delete button - sends DELETE request to backend
        const del = document.createElement("button");
        del.textContent = "Delete";
        del.addEventListener("click", async () => {
          await fetchWithAuth(`/api/parent/today/tasks/${task.id}`, { method: "DELETE" });
          await loadState();
          loadTodayTasks();
        });
        
        // Assemble task row
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

  // If a task is selected for editing, pre-fill the form with its values
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

/**
 * Helper function to find a task by ID across all children and categories
 * Used to locate task details when editing
 * @param {number} taskId - ID of the task to find
 * @returns {Object|null} Task object if found, null otherwise
 */
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

// ============================================
// TEMPLATE TASKS CRUD - CREATE, READ, UPDATE, DELETE
// ============================================

/**
 * Load and manage task templates for weekday and weekend days
 * Allows parent to configure which tasks appear by default for each day type
 * Fetches templates from /api/parent/templates endpoint
 */
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

  // If a template is selected for editing, pre-fill form with its values
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

// ============================================
// SETTINGS - DAILY REWARD TEXT & PIN MANAGEMENT
// ============================================

/**
 * Load and display settings form for parent configuration
 * Allows changing daily reward text and updating parent PIN
 * Fetches current settings from /api/parent/settings endpoint
 */
async function loadSettings() {
  const section = document.getElementById("tab-settings");
  section.innerHTML = "";
  
  // Fetch current settings from backend
  const response = await fetchWithAuth("/api/parent/settings");
  
  // Validate response and show error if request failed
  if (!response.ok) {
    section.textContent = "Unable to load settings.";
    return;
  }
  
  // Extract settings data
  const data = await response.json();
  
  // Build settings configuration form
  const form = document.createElement("form");
  form.innerHTML = `
    <div class="form-row">
      <input name="daily_reward_text" placeholder="Daily reward text" value="${data.daily_reward_text}" />
      <input name="old_pin" placeholder="Old PIN" type="password" />
      <input name="new_pin" placeholder="New PIN" type="password" />
      <button type="submit">Save Settings</button>
    </div>
  `;
  
  // Handle settings form submission
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    
    // Build settings payload from form fields
    const payload = {
      daily_reward_text: formData.get("daily_reward_text"),
      old_pin: formData.get("old_pin") || null,  // Optional PIN change
      new_pin: formData.get("new_pin") || null,  // Optional PIN change
    };
    
    // Send settings update via PUT request
    const saveResponse = await fetchWithAuth("/api/parent/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!saveResponse.ok) {
      showToast("Unable to save settings");
      return;
    }

    // Show success message to user
    showToast("Settings saved");
  });
  
  section.appendChild(form);

  const maxChildren = 5;
  const children = appState?.children || [];
  const childManager = document.createElement("div");
  childManager.className = "child-management";

  const childHeader = document.createElement("div");
  childHeader.className = "child-management-header";
  const childTitle = document.createElement("h3");
  childTitle.textContent = "Manage Children";
  childHeader.appendChild(childTitle);
  childManager.appendChild(childHeader);

  const childList = document.createElement("div");
  childList.className = "child-list";

  children.forEach((child) => {
    const row = document.createElement("div");
    row.className = "child-row";

    const input = document.createElement("input");
    input.type = "text";
    input.value = child.name;
    input.setAttribute("aria-label", `Child name for ${child.name}`);

    const actions = document.createElement("div");
    actions.className = "child-actions";

    const saveButton = document.createElement("button");
    saveButton.type = "button";
    saveButton.className = "secondary";
    saveButton.textContent = "Save";
    saveButton.addEventListener("click", async () => {
      const name = input.value.trim();
      if (!name) {
        showToast("Child name is required");
        return;
      }
      const response = await fetchWithAuth(`/api/parent/children/${child.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!response.ok) {
        showToast("Unable to update child");
        return;
      }
      await loadState();
      loadSettings();
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "danger";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", async () => {
      // Confirm deletion before proceeding
      if (!confirm(`Are you sure you want to delete ${child.name}? This action cannot be undone.`)) {
        return;
      }
      
      const response = await fetchWithAuth(`/api/parent/children/${child.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        showToast("Unable to delete child");
        return;
      }
      await loadState();
      loadSettings();
    });

    actions.appendChild(saveButton);
    actions.appendChild(deleteButton);
    row.appendChild(input);
    row.appendChild(actions);
    childList.appendChild(row);
  });

  childManager.appendChild(childList);

  const addRow = document.createElement("div");
  addRow.className = "child-add";
  const addInput = document.createElement("input");
  addInput.type = "text";
  addInput.placeholder = "New child name";

  const addButton = document.createElement("button");
  addButton.type = "button";
  addButton.textContent = "Add Child";

  const limitNote = document.createElement("div");
  limitNote.className = "child-limit";

  if (children.length >= maxChildren) {
    addInput.disabled = true;
    addButton.disabled = true;
    limitNote.textContent = "Maximum of 5 children reached.";
  } else {
    limitNote.textContent = "You can add up to 5 children.";
  }

  const submitNewChild = async () => {
    const name = addInput.value.trim();
    if (!name) {
      showToast("Enter a child name");
      return;
    }
    if (children.length >= maxChildren) {
      showToast("Child limit reached (max 5)");
      return;
    }
    const response = await fetchWithAuth("/api/parent/children", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!response.ok) {
      showToast("Unable to add child");
      return;
    }
    addInput.value = "";
    await loadState();
    loadSettings();
  };

  addButton.addEventListener("click", submitNewChild);
  addInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      submitNewChild();
    }
  });

  addRow.appendChild(addInput);
  addRow.appendChild(addButton);
  childManager.appendChild(addRow);
  childManager.appendChild(limitNote);
  section.appendChild(childManager);
}

// ============================================
// TAB NAVIGATION & EVENT SETUP
// ============================================

/**
 * Setup tab navigation for parent panel
 * Handles switching between Approvals, Completed, Today, Templates, Settings tabs
 * Uses data-tab attribute to match buttons with tab sections
 */
function setupTabs() {
  // Add click listener to each tab button
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      // Remove active class from all tab buttons
      document.querySelectorAll(".tab-button").forEach((btn) => btn.classList.remove("active"));
      
      // Hide all tab sections by adding hidden class
      document.querySelectorAll(".tab-section").forEach((section) => section.classList.add("hidden"));
      
      // Mark clicked button as active
      button.classList.add("active");
      
      // Show the corresponding tab section by removing hidden class
      document.getElementById(`tab-${button.dataset.tab}`).classList.remove("hidden");
    });
  });
}

/**
 * Setup all event listeners for the application
 * Attaches click and keyboard handlers to buttons and inputs
 * Initializes tab navigation system
 */
function setupListeners() {
  // Parent unlock button - shows PIN modal when clicked
  document.getElementById("parentButton").addEventListener("click", parentUnlock);
  
  // Close parent panel button
  document.getElementById("closeParent").addEventListener("click", closeParentPanel);
  
  // Cancel PIN entry modal
  document.getElementById("pinCancel").addEventListener("click", closePinModal);
  
  // Submit PIN button
  document.getElementById("pinSubmit").addEventListener("click", submitPin);
  
  // Allow Enter key to submit PIN (UX improvement)
  document.getElementById("pinInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      submitPin();
    }
  });
  
  // Setup tab navigation system
  setupTabs();
}

// ============================================
// INITIALIZATION - STARTUP SEQUENCE
// ============================================

// Attach all event listeners on page load
setupListeners();

// Load initial state/data and render kiosk display
loadState();

// Refresh state every 60 seconds (1 minute)
// Keeps kiosk display up-to-date without full page reload
setInterval(loadState, 60000);
