"use strict";

// --- helpers ---------------------------------------------------------------
async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("unauthorized");
  }
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

function fmtDate(value) {
  if (!value) return "";
  let d;
  if (typeof value === "number") d = new Date(value * 1000);
  else d = new Date(value);
  if (isNaN(d)) return value;
  return d.toLocaleString(undefined, {
    weekday: "short", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

// --- tab switching ---------------------------------------------------------
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

document.getElementById("logout").addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  window.location.href = "/login";
});

// --- fixtures --------------------------------------------------------------
async function loadFixtures() {
  const data = await api("/api/fixtures");
  const badge = document.getElementById("source-badge");
  if (data.live) {
    badge.textContent = "live · " + data.source;
    badge.classList.add("live");
  } else {
    badge.textContent = "sample data (providers offline)";
  }

  const wrap = document.getElementById("fixtures");
  wrap.innerHTML = "";
  data.fixtures.forEach((fx) => {
    const p = fx.prediction;
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="round">${fx.round || ""} <span class="date">· ${fmtDate(fx.utc_date)}</span></div>
      <div class="teams">${fx.home} <span style="color:var(--muted)">v</span> ${fx.away}</div>
      <div class="bar">
        <div class="seg home" style="width:${p.home_win}%">${p.home_win}%</div>
        <div class="seg draw" style="width:${p.draw}%">${p.draw}%</div>
        <div class="seg away" style="width:${p.away_win}%">${p.away_win}%</div>
      </div>
      <div class="meta">
        <span>Likely score <b>${p.most_likely_score}</b></span>
        <span>Total goals <b>${p.total_goals}</b></span>
      </div>`;
    card.addEventListener("click", () => showDetail(fx.home, fx.away, true));
    wrap.appendChild(card);
  });
}

// --- detailed prediction ---------------------------------------------------
function predictionMarkup(d) {
  const ou = d.goals.over_under;
  const cs = d.correct_scores.map(
    (c) => `<span class="chip">${c.score} <b>${c.prob}%</b></span>`
  ).join("");
  return `
    <div class="detail">
      <h2>${d.home} vs ${d.away}</h2>
      <p class="sub">Elo ${d.home_elo} vs ${d.away_elo} ·
        expected goals ${d.expected.goals_home} – ${d.expected.goals_away}</p>
      <div class="grid2">
        <div class="block">
          <h3>Match result (1X2)</h3>
          <div class="row"><span>${d.home} win</span><b>${d.result.home_win}%</b></div>
          <div class="row"><span>Draw</span><b>${d.result.draw}%</b></div>
          <div class="row"><span>${d.away} win</span><b>${d.result.away_win}%</b></div>
          <div class="row"><span>Fair odds</span>
            <span>${d.result.fair_odds.home} / ${d.result.fair_odds.draw} / ${d.result.fair_odds.away}</span></div>
        </div>
        <div class="block">
          <h3>Double chance</h3>
          <div class="row"><span>${d.home} or draw (1X)</span><b>${d.result.double_chance["1X"]}%</b></div>
          <div class="row"><span>${d.away} or draw (X2)</span><b>${d.result.double_chance["X2"]}%</b></div>
          <div class="row"><span>Either team (12)</span><b>${d.result.double_chance["12"]}%</b></div>
        </div>
        <div class="block">
          <h3>Goals</h3>
          <div class="row"><span>Over 1.5</span><b>${ou["1.5"].over}%</b></div>
          <div class="row"><span>Over 2.5</span><b>${ou["2.5"].over}%</b></div>
          <div class="row"><span>Over 3.5</span><b>${ou["3.5"].over}%</b></div>
          <div class="row"><span>Both teams to score</span><b>${d.goals.btts.yes}%</b></div>
        </div>
        <div class="block">
          <h3>Most likely scores</h3>
          <div class="scores">${cs}</div>
        </div>
      </div>
    </div>`;
}

async function getPrediction(home, away, neutral) {
  return api("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ home, away, neutral }),
  });
}

async function showDetail(home, away, neutral) {
  const d = await getPrediction(home, away, neutral);
  document.getElementById("modal-body").innerHTML = predictionMarkup(d);
  document.getElementById("modal").hidden = false;
}

document.getElementById("modal-close").addEventListener("click", () => {
  document.getElementById("modal").hidden = true;
});
document.getElementById("modal").addEventListener("click", (e) => {
  if (e.target.id === "modal") document.getElementById("modal").hidden = true;
});

// --- custom matchup --------------------------------------------------------
async function loadTeams() {
  const { teams } = await api("/api/teams");
  const home = document.getElementById("home-team");
  const away = document.getElementById("away-team");
  teams.forEach((t) => {
    const o1 = new Option(`${t.name} (${t.elo})`, t.name);
    const o2 = new Option(`${t.name} (${t.elo})`, t.name);
    home.add(o1);
    away.add(o2);
  });
  if (teams.length > 1) away.selectedIndex = 1;
}

document.getElementById("run-matchup").addEventListener("click", async () => {
  const home = document.getElementById("home-team").value;
  const away = document.getElementById("away-team").value;
  const neutral = !document.getElementById("home-adv").checked;
  const d = await getPrediction(home, away, neutral);
  document.getElementById("matchup-result").innerHTML = predictionMarkup(d);
});

// --- value calculator ------------------------------------------------------
document.getElementById("run-value").addEventListener("click", async () => {
  const probability = parseFloat(document.getElementById("v-prob").value);
  const odds = parseFloat(document.getElementById("v-odds").value);
  if (isNaN(probability) || isNaN(odds)) return;
  const v = await api("/api/value", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ probability, odds }),
  });
  const cls = v.value ? "good" : "bad";
  const verdict = v.value ? "✅ Value bet" : "❌ No value";
  document.getElementById("value-result").innerHTML = `
    <div class="verdict ${cls}">
      <div class="big">${verdict}</div>
      <div class="row"><span>Edge (expected return)</span><b>${v.edge_pct}%</b></div>
      <div class="row"><span>Full Kelly stake</span><b>${v.kelly_pct}% of bankroll</b></div>
      <div class="row"><span>Half Kelly (safer)</span><b>${v.half_kelly_pct}% of bankroll</b></div>
    </div>`;
});

// --- boot ------------------------------------------------------------------
(async function init() {
  try {
    await loadFixtures();
    await loadTeams();
  } catch (e) {
    /* 401 already redirected */
  }
})();
