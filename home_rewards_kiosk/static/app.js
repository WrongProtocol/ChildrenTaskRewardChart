const dashboard = document.getElementById("dashboard");
const dateLabel = document.getElementById("date");
const capLabel = document.getElementById("daily-cap");
const rateLabel = document.getElementById("exchange-rate");

const formatDate = () => {
  const now = new Date();
  return now.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
};

const render = (state) => {
  dateLabel.textContent = formatDate();
  capLabel.textContent = `${state.settings?.daily_minute_cap ?? 0} min`;
  rateLabel.textContent = `${(state.settings?.exchange_rate_cents ?? 0) / 100}/min`;

  dashboard.innerHTML = "";
  state.children.forEach((child) => {
    const wallet = state.wallets.find((w) => w.child_id === child.id) || {
      minutes_balance: 0,
    };
    const pendingCount = state.instances.filter(
      (instance) => instance.child_id === child.id && instance.status === "pending"
    ).length;
    const percent = Math.min((wallet.minutes_balance / (state.settings?.daily_minute_cap ?? 1)) * 100, 100);

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
        <div class="category-tile">Schoolwork</div>
        <div class="category-tile">Hygiene</div>
        <div class="category-tile">Family Help</div>
      </div>
      <div class="actions">
        <button>Claim Task</button>
        <button>Play Time</button>
        <button>Cash Out</button>
      </div>
    `;
    dashboard.appendChild(card);
  });
};

fetch("/kiosk/state")
  .then((response) => response.json())
  .then((state) => render(state))
  .catch(() => {
    dashboard.innerHTML = "<p>Unable to load kiosk state.</p>";
  });
