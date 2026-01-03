const dashboard = document.getElementById("dashboard");
const dateLabel = document.getElementById("date");
const capLabel = document.getElementById("daily-cap");
const rateLabel = document.getElementById("exchange-rate");
const parentButton = document.getElementById("parent-button");
const modalRoot = document.getElementById("modal-root");

const DEFAULT_CATEGORIES = ["Schoolwork", "Hygiene", "Family Help"];
const PAGE_SIZE = 6;

const state = {
  kiosk: null,
  parent: {
    unlocked: false,
    pin: null,
    goals: [],
    settings: null,
    tab: "approvals",
  },
  selections: new Map(),
  pages: {
    approvals: 0,
    goals: 0,
    claim: {},
  },
};

const formatDate = () => {
  const now = new Date();
  return now.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
};

const formatMoney = (cents) => `$${(cents / 100).toFixed(2)}`;

const postJson = async (url, payload) => {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
};

const requestJson = async (url, options = {}) => {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
};

const closeModal = () => {
  modalRoot.classList.add("hidden");
  modalRoot.setAttribute("aria-hidden", "true");
  modalRoot.innerHTML = "";
};

const showModal = ({ title, body, footer, onMount }) => {
  modalRoot.innerHTML = `
    <div class="modal-card" role="dialog" aria-modal="true">
      <div class="modal-header">
        <h3>${title}</h3>
        <button class="ghost" data-action="close">Close</button>
      </div>
      <div class="modal-body">${body}</div>
      <div class="modal-footer">${footer}</div>
    </div>
  `;
  modalRoot.classList.remove("hidden");
  modalRoot.setAttribute("aria-hidden", "false");

  modalRoot.querySelectorAll("[data-action='close']").forEach((button) => {
    button.addEventListener("click", closeModal);
  });
  modalRoot.addEventListener(
    "click",
    (event) => {
      if (event.target === modalRoot) {
        closeModal();
      }
    },
    { once: true }
  );

  if (onMount) {
    onMount();
  }
};

const getChildGoals = (childId) =>
  (state.kiosk?.goals ?? []).filter(
    (goal) => goal.child_id === null || goal.child_id === childId
  );

const getCategories = () => {
  const categories = new Set(state.kiosk?.goals?.map((goal) => goal.category) ?? []);
  return categories.size ? Array.from(categories) : DEFAULT_CATEGORIES;
};

const paginate = (items, page) => {
  const totalPages = Math.max(Math.ceil(items.length / PAGE_SIZE), 1);
  const safePage = Math.min(Math.max(page, 0), totalPages - 1);
  const start = safePage * PAGE_SIZE;
  return {
    items: items.slice(start, start + PAGE_SIZE),
    page: safePage,
    totalPages,
  };
};

const renderPager = (container, pageKey, totalPages) => {
  const currentPage = state.pages[pageKey] ?? 0;
  container.innerHTML = `
    <button data-page="prev">Prev</button>
    <span>Page ${currentPage + 1} of ${totalPages}</span>
    <button data-page="next">Next</button>
  `;
  const prev = container.querySelector("[data-page='prev']");
  const next = container.querySelector("[data-page='next']");
  prev.disabled = currentPage === 0;
  next.disabled = currentPage >= totalPages - 1;
  prev.addEventListener("click", () => {
    state.pages[pageKey] = Math.max(currentPage - 1, 0);
    renderParentModal(state.parent.tab);
  });
  next.addEventListener("click", () => {
    state.pages[pageKey] = Math.min(currentPage + 1, totalPages - 1);
    renderParentModal(state.parent.tab);
  });
};

const render = () => {
  if (!state.kiosk) {
    return;
  }
  dateLabel.textContent = formatDate();
  capLabel.textContent = `${state.kiosk.settings?.daily_minute_cap ?? 0} min`;
  rateLabel.textContent = `${formatMoney(state.kiosk.settings?.exchange_rate_cents ?? 0)}/min`;

  dashboard.innerHTML = "";
  state.kiosk.children.forEach((child) => {
    const childGoals = getChildGoals(child.id);
    const wallet = state.kiosk.wallets.find((item) => item.child_id === child.id) || {
      minutes_balance: 0,
      money_balance_cents: 0,
    };
    const pendingCount = state.kiosk.instances.filter(
      (instance) => instance.child_id === child.id && instance.status === "pending"
    ).length;
    const cap = Math.max(state.kiosk.settings?.daily_minute_cap ?? 1, 1);
    const percent = Math.min((wallet.minutes_balance / cap) * 100, 100);
    const categories = getCategories();
    const selectedCategory =
      state.selections.get(child.id) ?? categories[0] ?? DEFAULT_CATEGORIES[0];
    state.selections.set(child.id, selectedCategory);

    const card = document.createElement("section");
    card.className = "child-card";
    card.innerHTML = `
      <div class="child-header">
        <div class="avatar" style="background:${child.avatar_color}"></div>
        <div class="child-title">
          <h2>${child.name}</h2>
          <div class="progress-bar"><span style="width:${percent}%"></span></div>
        </div>
      </div>
      <div class="minutes">${wallet.minutes_balance} min</div>
      <div class="pending">${pendingCount} pending</div>
      <div class="categories">
        ${categories
          .map(
            (category) => `
            <button class="category-tile${
              category === selectedCategory ? " active" : ""
            }" data-category="${category}">
              ${category}
            </button>
          `
          )
          .join("")}
      </div>
      <div class="actions">
        <button data-action="claim">Claim Task</button>
        <button class="secondary" data-action="play">Play Time</button>
        <button class="tertiary" data-action="cashout">Cash Out</button>
      </div>
    `;

    card.querySelectorAll(".category-tile").forEach((tile) => {
      tile.addEventListener("click", () => {
        state.selections.set(child.id, tile.dataset.category);
        render();
      });
    });

    card.querySelectorAll(".actions button").forEach((button) => {
      button.addEventListener("click", () => {
        if (button.dataset.action === "claim") {
          openClaimModal(child);
        }
        if (button.dataset.action === "play") {
          openPlayModal(child);
        }
        if (button.dataset.action === "cashout") {
          openCashoutModal(child);
        }
      });
    });

    dashboard.appendChild(card);
  });
};

const openClaimModal = (child) => {
  const categories = getCategories();
  let selectedCategory = state.selections.get(child.id) ?? categories[0];
  const pageKey = `${child.id}-${selectedCategory}`;
  let page = state.pages.claim[pageKey] ?? 0;

  const renderBody = () => {
    const goals = getChildGoals(child.id).filter(
      (goal) => goal.category === selectedCategory
    );
    const { items, totalPages } = paginate(goals, page);

    return `
      <div class="section-title">
        <h4>${child.name} · ${selectedCategory}</h4>
        <span class="badge">Tap a goal to claim</span>
      </div>
      <div class="inline-actions" id="category-switch">
        ${categories
          .map(
            (category) => `
            <button data-category="${category}" class="${
              category === selectedCategory ? "active" : ""
            }">
              ${category}
            </button>
          `
          )
          .join("")}
      </div>
      <div class="modal-grid" id="goal-grid">
        ${
          items.length
            ? items
                .map(
                  (goal) => `
                <div class="tile">
                  <strong>${goal.title}</strong>
                  <span>${goal.reward_minutes} min · ${goal.repeat_rule}</span>
                  <button data-goal="${goal.id}">Claim</button>
                </div>
              `
                )
                .join("")
            : `<div class="tile"><strong>No goals</strong><span>Ask a parent to add one.</span></div>`
        }
      </div>
      ${totalPages > 1 ? `<div class="pager" id="claim-pager"></div>` : ""}
    `;
  };

  showModal({
    title: "Claim Task",
    body: renderBody(),
    footer: "<button class=\"primary\" data-action=\"close\">Done</button>",
    onMount: () => {
      const switcher = modalRoot.querySelector("#category-switch");
      if (switcher) {
        switcher.querySelectorAll("button").forEach((button) => {
          button.addEventListener("click", () => {
            selectedCategory = button.dataset.category;
            state.selections.set(child.id, selectedCategory);
            state.pages.claim[`${child.id}-${selectedCategory}`] = 0;
            openClaimModal(child);
          });
        });
      }

      const goals = getChildGoals(child.id).filter(
        (goal) => goal.category === selectedCategory
      );
      const { totalPages } = paginate(goals, page);
      const pager = modalRoot.querySelector("#claim-pager");
      if (pager && totalPages > 1) {
        pager.innerHTML = `
          <button data-page="prev">Prev</button>
          <span>Page ${page + 1} of ${totalPages}</span>
          <button data-page="next">Next</button>
        `;
        pager.querySelector("[data-page='prev']").disabled = page === 0;
        pager.querySelector("[data-page='next']").disabled = page >= totalPages - 1;
        pager.querySelector("[data-page='prev']").addEventListener("click", () => {
          page = Math.max(page - 1, 0);
          state.pages.claim[pageKey] = page;
          openClaimModal(child);
        });
        pager.querySelector("[data-page='next']").addEventListener("click", () => {
          page = Math.min(page + 1, totalPages - 1);
          state.pages.claim[pageKey] = page;
          openClaimModal(child);
        });
      }

      modalRoot.querySelectorAll("[data-goal]").forEach((button) => {
        button.addEventListener("click", async () => {
          try {
            await postJson(`/child/${child.id}/claim`, {
              goal_id: Number(button.dataset.goal),
            });
            await loadState();
            closeModal();
          } catch (error) {
            window.alert("Unable to claim this goal right now.");
            console.error(error);
          }
        });
      });
    },
  });
};

const openPlayModal = (child) => {
  showModal({
    title: "Play Time",
    body: `
      <div class="form-grid">
        <label>
          Minutes
          <input type="number" min="1" placeholder="30" id="play-minutes" />
        </label>
        <label>
          Current balance
          <input type="text" value="${
            state.kiosk.wallets.find((item) => item.child_id === child.id)?.minutes_balance ??
            0
          } min" disabled />
        </label>
      </div>
      <span class="badge">Start or stop play with approved minutes.</span>
    `,
    footer: `
      <button data-action="start" class="primary">Start Play</button>
      <button data-action="stop">Stop Play</button>
    `,
    onMount: () => {
      const minutesInput = modalRoot.querySelector("#play-minutes");
      const handlePlay = async (action) => {
        const minutes = Number(minutesInput.value);
        if (!minutes || minutes <= 0) {
          window.alert("Enter a valid minute amount.");
          return;
        }
        try {
          await postJson(`/child/${child.id}/play/${action}`, { minutes });
          await loadState();
          closeModal();
        } catch (error) {
          window.alert("Unable to update play time.");
          console.error(error);
        }
      };
      modalRoot.querySelector("[data-action='start']").addEventListener("click", () => {
        handlePlay("start");
      });
      modalRoot.querySelector("[data-action='stop']").addEventListener("click", () => {
        handlePlay("stop");
      });
    },
  });
};

const openCashoutModal = (child) => {
  showModal({
    title: "Cash Out",
    body: `
      <div class="form-grid">
        <label>
          Minutes to convert
          <input type="number" min="1" placeholder="20" id="cashout-minutes" />
        </label>
        <label>
          Exchange rate
          <input type="text" value="${formatMoney(
            state.kiosk.settings?.exchange_rate_cents ?? 0
          )}/min" disabled />
        </label>
      </div>
      <span class="badge">Parent approval required.</span>
    `,
    footer: `
      <button class="primary" data-action="submit">Request Cash-Out</button>
      <button data-action="close">Cancel</button>
    `,
    onMount: () => {
      modalRoot.querySelector("[data-action='submit']").addEventListener("click", async () => {
        const minutes = Number(modalRoot.querySelector("#cashout-minutes").value);
        if (!minutes || minutes <= 0) {
          window.alert("Enter a valid minute amount.");
          return;
        }
        try {
          await postJson(`/child/${child.id}/cashout/request`, { minutes });
          await loadState();
          closeModal();
        } catch (error) {
          window.alert("Unable to request cash-out.");
          console.error(error);
        }
      });
    },
  });
};

const openPinModal = () => {
  showModal({
    title: "Parent Unlock",
    body: `
      <div class="form-grid">
        <label>
          Parent PIN
          <input type="password" id="pin-input" placeholder="••••" />
        </label>
      </div>
      <span class="badge">PIN required for approvals and settings.</span>
    `,
    footer: `
      <button class="primary" data-action="unlock">Unlock</button>
      <button data-action="close">Cancel</button>
    `,
    onMount: () => {
      modalRoot.querySelector("[data-action='unlock']").addEventListener("click", async () => {
        const pin = modalRoot.querySelector("#pin-input").value.trim();
        if (!pin) {
          window.alert("Enter the parent PIN.");
          return;
        }
        try {
          await postJson("/parent/unlock", { pin });
          state.parent.unlocked = true;
          state.parent.pin = pin;
          closeModal();
          openParentModal();
        } catch (error) {
          window.alert("Invalid PIN.");
          console.error(error);
        }
      });
    },
  });
};

const fetchParentGoals = async () => {
  if (!state.parent.pin) {
    return [];
  }
  const goals = await requestJson(`/parent/goals?pin=${encodeURIComponent(state.parent.pin)}`);
  state.parent.goals = goals;
  return goals;
};

const fetchParentSettings = async () => {
  if (!state.parent.pin) {
    return null;
  }
  const settings = await requestJson(
    `/parent/settings?pin=${encodeURIComponent(state.parent.pin)}`
  );
  state.parent.settings = settings;
  return settings;
};

const renderParentModal = (tab) => {
  state.parent.tab = tab;
  showModal({
    title: "Parent Controls",
    body: `
      <div class="inline-actions" id="parent-tabs">
        <button data-tab="approvals">Approvals</button>
        <button data-tab="goals">Goals</button>
        <button data-tab="settings">Settings</button>
      </div>
      <div id="parent-content"></div>
    `,
    footer: `
      <button data-action="lock">Lock</button>
      <button class="primary" data-action="close">Done</button>
    `,
    onMount: () => {
      modalRoot.querySelectorAll("#parent-tabs button").forEach((button) => {
        if (button.dataset.tab === tab) {
          button.classList.add("active");
        }
        button.addEventListener("click", () => {
          renderParentModal(button.dataset.tab);
        });
      });

      modalRoot.querySelector("[data-action='lock']").addEventListener("click", () => {
        state.parent.unlocked = false;
        state.parent.pin = null;
        closeModal();
      });

      const content = modalRoot.querySelector("#parent-content");
      if (tab === "approvals") {
        renderApprovals(content);
      }
      if (tab === "goals") {
        renderGoals(content);
      }
      if (tab === "settings") {
        renderSettings(content);
      }
    },
  });
};

const renderApprovals = (container) => {
  const pending = (state.kiosk?.instances ?? []).filter(
    (instance) => instance.status === "pending"
  );
  const { items, totalPages } = paginate(pending, state.pages.approvals);

  container.innerHTML = `
    <div class="section-title">
      <h4>Pending Approvals</h4>
      <span class="badge">${pending.length} pending</span>
    </div>
    <div class="modal-grid">
      ${
        items.length
          ? items
              .map((instance) => {
                const goal = state.kiosk.goals.find((item) => item.id === instance.goal_id);
                const child = state.kiosk.children.find((item) => item.id === instance.child_id);
                return `
                <div class="tile">
                  <strong>${goal?.title ?? "Goal"}</strong>
                  <span>${child?.name ?? "Child"}</span>
                  <span>Claimed ${new Date(instance.claimed_at).toLocaleTimeString()}</span>
                  <div class="inline-actions">
                    <button class="approve" data-approve="true" data-instance="${
                      instance.id
                    }">Approve</button>
                    <button class="reject" data-approve="false" data-instance="${
                      instance.id
                    }">Not Yet</button>
                  </div>
                </div>
              `;
              })
              .join("")
          : `<div class="tile"><strong>All clear</strong><span>No pending approvals.</span></div>`
      }
    </div>
    <div class="pager" id="approval-pager"></div>
  `;

  if (totalPages > 1) {
    renderPager(container.querySelector("#approval-pager"), "approvals", totalPages);
  }

  container.querySelectorAll("[data-instance]").forEach((button) => {
    button.addEventListener("click", async () => {
      const instanceId = Number(button.dataset.instance);
      const approve = button.dataset.approve === "true";
      try {
        await requestJson(
          `/parent/approve?pin=${encodeURIComponent(state.parent.pin)}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ instance_id: instanceId, approve }),
          }
        );
        await loadState();
        renderParentModal("approvals");
      } catch (error) {
        window.alert("Unable to update approval.");
        console.error(error);
      }
    });
  });
};

const renderGoals = async (container) => {
  container.innerHTML = `
    <div class="section-title">
      <h4>Goals Library</h4>
      <button class="primary" id="new-goal">New Goal</button>
    </div>
    <div class="modal-grid" id="goal-grid"></div>
    <div class="pager" id="goal-pager"></div>
  `;

  try {
    const goals = await fetchParentGoals();
    const { items, totalPages } = paginate(goals, state.pages.goals);
    const grid = container.querySelector("#goal-grid");
    grid.innerHTML = items
      .map((goal) => {
        const child = state.kiosk.children.find((item) => item.id === goal.child_id);
        return `
        <div class="tile">
          <strong>${goal.title}</strong>
          <span>${goal.category}</span>
          <span>${goal.reward_minutes} min · ${goal.repeat_rule}</span>
          <span>${child ? child.name : "Shared"}</span>
          <div class="inline-actions">
            <button data-edit="${goal.id}">Edit</button>
            <button class="danger" data-delete="${goal.id}">Delete</button>
          </div>
        </div>
      `;
      })
      .join("");

    if (totalPages > 1) {
      renderPager(container.querySelector("#goal-pager"), "goals", totalPages);
    }

    container.querySelectorAll("[data-edit]").forEach((button) => {
      button.addEventListener("click", () => {
        const goal = goals.find((item) => item.id === Number(button.dataset.edit));
        if (goal) {
          openGoalForm(goal);
        }
      });
    });

    container.querySelectorAll("[data-delete]").forEach((button) => {
      button.addEventListener("click", async () => {
        if (!window.confirm("Delete this goal?")) {
          return;
        }
        try {
          await requestJson(
            `/parent/goals/${button.dataset.delete}?pin=${encodeURIComponent(state.parent.pin)}`,
            { method: "DELETE" }
          );
          await fetchParentGoals();
          renderParentModal("goals");
        } catch (error) {
          window.alert("Unable to delete goal.");
          console.error(error);
        }
      });
    });

    container.querySelector("#new-goal").addEventListener("click", () => {
      openGoalForm();
    });
  } catch (error) {
    container.querySelector("#goal-grid").innerHTML =
      "<div class='tile'><strong>Error</strong><span>Unable to load goals.</span></div>";
    console.error(error);
  }
};

const openGoalForm = (goal) => {
  const categories = getCategories();
  const children = state.kiosk.children;
  const isEditing = Boolean(goal);

  showModal({
    title: isEditing ? "Edit Goal" : "Create Goal",
    body: `
      <div class="form-grid">
        <label>
          Title
          <input type="text" id="goal-title" value="${goal?.title ?? ""}" />
        </label>
        <label>
          Category
          <select id="goal-category">
            ${categories
              .map(
                (category) => `
                <option value="${category}" ${
                  goal?.category === category ? "selected" : ""
                }>${category}</option>
              `
              )
              .join("")}
          </select>
        </label>
        <label>
          Reward Minutes
          <input type="number" min="1" id="goal-minutes" value="${
            goal?.reward_minutes ?? 10
          }" />
        </label>
        <label>
          Repeat Rule
          <select id="goal-repeat">
            ${["daily", "weekdays", "custom"]
              .map(
                (rule) => `
                <option value="${rule}" ${goal?.repeat_rule === rule ? "selected" : ""}>
                  ${rule}
                </option>
              `
              )
              .join("")}
          </select>
        </label>
        <label>
          Assigned Child
          <select id="goal-child">
            <option value="">Shared</option>
            ${children
              .map(
                (child) => `
                <option value="${child.id}" ${
                  goal?.child_id === child.id ? "selected" : ""
                }>${child.name}</option>
              `
              )
              .join("")}
          </select>
        </label>
        <label>
          Proof Required
          <select id="goal-proof">
            <option value="false" ${goal?.proof_required ? "" : "selected"}>No</option>
            <option value="true" ${goal?.proof_required ? "selected" : ""}>Yes</option>
          </select>
        </label>
        <label>
          Auto Approve
          <select id="goal-auto">
            <option value="false" ${goal?.auto_approve ? "" : "selected"}>No</option>
            <option value="true" ${goal?.auto_approve ? "selected" : ""}>Yes</option>
          </select>
        </label>
      </div>
    `,
    footer: `
      <button class="primary" data-action="save">${isEditing ? "Save" : "Create"}</button>
      <button data-action="close">Cancel</button>
    `,
    onMount: () => {
      modalRoot.querySelector("[data-action='save']").addEventListener("click", async () => {
        const payload = {
          title: modalRoot.querySelector("#goal-title").value.trim(),
          category: modalRoot.querySelector("#goal-category").value,
          reward_minutes: Number(modalRoot.querySelector("#goal-minutes").value),
          repeat_rule: modalRoot.querySelector("#goal-repeat").value,
          child_id: modalRoot.querySelector("#goal-child").value
            ? Number(modalRoot.querySelector("#goal-child").value)
            : null,
          proof_required: modalRoot.querySelector("#goal-proof").value === "true",
          auto_approve: modalRoot.querySelector("#goal-auto").value === "true",
        };

        if (!payload.title) {
          window.alert("Goal title is required.");
          return;
        }

        try {
          if (isEditing) {
            await requestJson(
              `/parent/goals/${goal.id}?pin=${encodeURIComponent(state.parent.pin)}`,
              {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
              }
            );
          } else {
            await requestJson(`/parent/goals?pin=${encodeURIComponent(state.parent.pin)}`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            });
          }
          await fetchParentGoals();
          await loadState();
          closeModal();
          openParentModal("goals");
        } catch (error) {
          window.alert("Unable to save goal.");
          console.error(error);
        }
      });
    },
  });
};

const renderSettings = async (container) => {
  container.innerHTML = `
    <div class="section-title">
      <h4>Settings</h4>
    </div>
    <div class="form-grid">
      <label>
        Daily Minute Cap
        <input type="number" min="1" id="settings-cap" />
      </label>
      <label>
        Exchange Rate ($/min)
        <input type="number" step="0.01" min="0" id="settings-rate" />
      </label>
      <label>
        Update Parent PIN
        <input type="password" id="settings-pin" placeholder="Leave blank to keep" />
      </label>
    </div>
    <div class="inline-actions">
      <button class="primary" id="save-settings">Save Settings</button>
    </div>
  `;

  try {
    const settings = await fetchParentSettings();
    if (settings) {
      container.querySelector("#settings-cap").value = settings.daily_minute_cap;
      container.querySelector("#settings-rate").value = (
        settings.exchange_rate_cents / 100
      ).toFixed(2);
    }

    container.querySelector("#save-settings").addEventListener("click", async () => {
      const dailyCap = Number(container.querySelector("#settings-cap").value);
      const rate = Number(container.querySelector("#settings-rate").value);
      const pin = container.querySelector("#settings-pin").value.trim();

      if (!dailyCap || dailyCap <= 0) {
        window.alert("Enter a valid daily cap.");
        return;
      }

      const payload = {
        daily_minute_cap: dailyCap,
        exchange_rate_cents: Math.round(rate * 100),
      };
      if (pin) {
        payload.pin = pin;
      }

      try {
        await requestJson(`/parent/settings?pin=${encodeURIComponent(state.parent.pin)}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        await fetchParentSettings();
        await loadState();
        openParentModal("settings");
      } catch (error) {
        window.alert("Unable to save settings.");
        console.error(error);
      }
    });
  } catch (error) {
    container.innerHTML +=
      "<div class='tile'><strong>Error</strong><span>Unable to load settings.</span></div>";
    console.error(error);
  }
};

const openParentModal = (tab = "approvals") => {
  if (!state.parent.unlocked) {
    openPinModal();
    return;
  }
  renderParentModal(tab);
};

const loadState = async () => {
  try {
    state.kiosk = await requestJson("/kiosk/state");
    render();
  } catch (error) {
    dashboard.innerHTML = "<p>Unable to load kiosk state.</p>";
    console.error(error);
  }
};

loadState();

if (parentButton) {
  parentButton.addEventListener("click", () => {
    openParentModal();
  });
}
