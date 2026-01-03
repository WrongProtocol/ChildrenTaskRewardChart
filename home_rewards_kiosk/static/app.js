const dashboard = document.getElementById("dashboard");
const dateLabel = document.getElementById("date");
const capLabel = document.getElementById("daily-cap");
const rateLabel = document.getElementById("exchange-rate");
const lockButton = document.querySelector(".lock-button");
const selectedCategories = new Map();

const formatDate = () => {
  const now = new Date();
  return now.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
};

const getChildGoals = (state, childId) =>
  state.goals.filter((goal) => goal.child_id === childId);

const requestMinutes = (label, fallbackMinutes = 10) => {
  const input = window.prompt(`How many minutes for ${label}?`, `${fallbackMinutes}`);
  if (input === null) {
    return null;
  }
  const minutes = Number.parseInt(input, 10);
  if (Number.isNaN(minutes) || minutes <= 0) {
    window.alert("Please enter a positive number of minutes.");
    return null;
  }
  return minutes;
};

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

const render = (state) => {
  dateLabel.textContent = formatDate();
  capLabel.textContent = `${state.settings?.daily_minute_cap ?? 0} min`;
  rateLabel.textContent = `${(state.settings?.exchange_rate_cents ?? 0) / 100}/min`;

  dashboard.innerHTML = "";
  state.children.forEach((child) => {
    const childGoals = getChildGoals(state, child.id);
    const wallet = state.wallets.find((w) => w.child_id === child.id) || {
      minutes_balance: 0,
    };
    const pendingCount = state.instances.filter(
      (instance) => instance.child_id === child.id && instance.status === "pending"
    ).length;
    const percent = Math.min((wallet.minutes_balance / (state.settings?.daily_minute_cap ?? 1)) * 100, 100);
    const categories = Array.from(new Set(childGoals.map((goal) => goal.category)));
    const selectedCategory =
      selectedCategories.get(child.id) ?? categories[0] ?? null;

    const card = document.createElement("section");
    card.className = "child-card";
    card.innerHTML = `
      <div class="child-header">
        <div class="avatar" style="background:${child.avatar_color}"></div>
        <div>
          <h2>${child.name}</h2>
          <div class="progress-bar"><span style="width:${percent}%"></span></div>
        </div>
      </div>
      <div class="minutes">${wallet.minutes_balance} min</div>
      <div class="pending">${pendingCount} pending</div>
      <div class="categories">
        ${
          categories.length
            ? categories
                .map(
                  (category) =>
                    `<button class="category-tile${
                      category === selectedCategory ? " active" : ""
                    }" data-category="${category}">${category}</button>`
                )
                .join("")
            : `<div class="category-tile">No tasks</div>`
        }
      </div>
      <div class="actions">
        <button data-action="claim">Claim Task</button>
        <button data-action="play">Play Time</button>
        <button data-action="cashout">Cash Out</button>
      </div>
    `;

    if (categories.length && !selectedCategories.has(child.id)) {
      selectedCategories.set(child.id, categories[0]);
    }

    card.querySelectorAll(".category-tile").forEach((tile) => {
      const category = tile.dataset.category;
      if (!category) {
        return;
      }
      tile.addEventListener("click", () => {
        selectedCategories.set(child.id, category);
        render(state);
      });
    });

    const actionButtons = card.querySelectorAll(".actions button");
    actionButtons.forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          if (button.dataset.action === "claim") {
            const category = selectedCategories.get(child.id);
            const goal =
              childGoals.find((item) => item.category === category) ?? childGoals[0];
            if (!goal) {
              window.alert("No tasks available to claim.");
              return;
            }
            await postJson(`/child/${child.id}/claim`, { goal_id: goal.id });
          }

          if (button.dataset.action === "play") {
            const minutes = requestMinutes("play time");
            if (minutes === null) {
              return;
            }
            await postJson(`/child/${child.id}/play/start`, { minutes });
          }

          if (button.dataset.action === "cashout") {
            const minutes = requestMinutes("cash out");
            if (minutes === null) {
              return;
            }
            await postJson(`/child/${child.id}/cashout/request`, { minutes });
          }

          await loadState();
        } catch (error) {
          window.alert("Something went wrong. Please try again.");
          console.error(error);
        }
      });
    });
    dashboard.appendChild(card);
  });
};

const loadState = async () => {
  try {
    const response = await fetch("/kiosk/state");
    if (!response.ok) {
      throw new Error("Unable to load kiosk state.");
    }
    const state = await response.json();
    render(state);
  } catch (error) {
    dashboard.innerHTML = "<p>Unable to load kiosk state.</p>";
    console.error(error);
  }
};

loadState();

if (lockButton) {
  lockButton.addEventListener("click", async () => {
    const pin = window.prompt("Enter parent PIN");
    if (!pin) {
      return;
    }
    try {
      await postJson("/parent/unlock", { pin });
      window.alert("Parent controls unlocked.");
    } catch (error) {
      window.alert("Invalid PIN. Please try again.");
      console.error(error);
    }
  });
}
