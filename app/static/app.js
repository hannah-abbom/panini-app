"use strict";

// --- helpers ---------------------------------------------------------------
async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (res.status === 401) { window.location.href = "/login"; throw new Error("unauth"); }
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}
const jpost = (path, body) => api(path, {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});
function fmtDate(v) {
  if (!v) return "";
  const d = typeof v === "number" ? new Date(v * 1000) : new Date(v);
  if (isNaN(d)) return v;
  return d.toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
function heatColor(p) {
  // p is a percent 0..~40; map to a blue->green ramp.
  const t = Math.min(1, p / 22);
  const r = Math.round(20 + t * 10), g = Math.round(40 + t * 150), b = Math.round(90 - t * 40);
  return `rgb(${r},${g},${b})`;
}
function formLine(str) {
  if (!str) return "";
  return `<span class="formline">${[...str].map((c) => `<span class="f-${c}">${c}</span>`).join("")}</span>`;
}

// --- state -----------------------------------------------------------------
let TEAMS = [];
let ALL_FIXTURES = [];

// --- tabs ------------------------------------------------------------------
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
function renderFixtures(list) {
  const wrap = document.getElementById("fixtures");
  wrap.innerHTML = "";
  list.forEach((fx) => {
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
        <span>Score <b>${p.most_likely_score}</b></span>
        <span>Goals <b>${p.total_goals}</b></span>
        <span>O2.5 <b>${p.over25}%</b></span>
        <span>BTTS <b>${p.btts}%</b></span>
      </div>`;
    card.addEventListener("click", () => showDetail(fx.home, fx.away, true));
    wrap.appendChild(card);
  });
}
async function loadFixtures() {
  const data = await api("/api/fixtures");
  const badge = document.getElementById("source-badge");
  if (data.live) { badge.textContent = "live · " + data.source; badge.classList.add("live"); }
  else badge.textContent = data.source || "schedule";

  ALL_FIXTURES = data.fixtures;
  const rounds = [...new Set(data.fixtures.map((f) => f.round).filter(Boolean))];
  const sel = document.getElementById("round-filter");
  rounds.forEach((r) => sel.add(new Option(r, r)));
  sel.onchange = () => renderFixtures(sel.value ? ALL_FIXTURES.filter((f) => f.round === sel.value) : ALL_FIXTURES);
  renderFixtures(ALL_FIXTURES);
}

// --- detailed prediction ---------------------------------------------------
function heatmap(matrix, home, away) {
  let cells = `<div class="lbl"></div>`;
  for (let j = 0; j < 6; j++) cells += `<div class="lbl">${j}</div>`;
  for (let i = 0; i < 6; i++) {
    cells += `<div class="lbl">${i}</div>`;
    for (let j = 0; j < 6; j++) {
      const v = matrix[i][j];
      cells += `<div class="cell" style="background:${heatColor(v)}" title="${i}-${j}: ${v}%">${v >= 3 ? v : ""}</div>`;
    }
  }
  return `<div class="heat">${cells}</div>
    <div class="heat-cap">Rows = ${home} goals, columns = ${away} goals (% likelihood)</div>`;
}
function predictionMarkup(d) {
  const ou = d.goals.over_under, mk = d.markets;
  const cs = d.correct_scores.map((c) => `<span class="chip">${c.score} <b>${c.prob}%</b></span>`).join("");
  const hf = d.form && d.form.home ? `Form ${formLine(d.form.home.string)}` : "";
  const af = d.form && d.form.away ? `Form ${formLine(d.form.away.string)}` : "";
  return `
    <div class="detail">
      <h2>${d.home} vs ${d.away}</h2>
      <p class="sub">Elo ${d.home_elo} ${hf} &nbsp;·&nbsp; ${d.away_elo} ${af}<br/>
        Expected goals ${d.expected.goals_home} – ${d.expected.goals_away} ·
        most likely ${d.expected.most_likely_score}</p>
      <div class="grid2">
        <div class="block">
          <h3>Match result (1X2)</h3>
          <div class="row"><span>${d.home} win</span><b>${d.result.home_win}%</b></div>
          <div class="row"><span>Draw</span><b>${d.result.draw}%</b></div>
          <div class="row"><span>${d.away} win</span><b>${d.result.away_win}%</b></div>
          <div class="row"><span>Fair odds</span><span>${d.result.fair_odds.home} / ${d.result.fair_odds.draw} / ${d.result.fair_odds.away}</span></div>
          <div class="row"><span>Expected points</span><span>${d.result.expected_points.home} / ${d.result.expected_points.away}</span></div>
        </div>
        <div class="block">
          <h3>Double chance &amp; qualify</h3>
          <div class="row"><span>${d.home} or draw (1X)</span><b>${d.result.double_chance["1X"]}%</b></div>
          <div class="row"><span>${d.away} or draw (X2)</span><b>${d.result.double_chance["X2"]}%</b></div>
          <div class="row"><span>Either team (12)</span><b>${d.result.double_chance["12"]}%</b></div>
          <div class="row"><span>To qualify (ET/pens)</span><span>${d.advance.home}% / ${d.advance.away}%</span></div>
        </div>
        <div class="block">
          <h3>Goals</h3>
          <div class="row"><span>Over 1.5 / 2.5 / 3.5</span><b>${ou["1.5"].over}% / ${ou["2.5"].over}% / ${ou["3.5"].over}%</b></div>
          <div class="row"><span>Both teams to score</span><b>${d.goals.btts.yes}%</b></div>
          <div class="row"><span>Clean sheet ${d.home} / ${d.away}</span><span>${mk.clean_sheet.home}% / ${mk.clean_sheet.away}%</span></div>
          <div class="row"><span>Win to nil ${d.home} / ${d.away}</span><span>${mk.win_to_nil.home}% / ${mk.win_to_nil.away}%</span></div>
        </div>
        <div class="block">
          <h3>Handicap (goal line)</h3>
          <div class="row"><span>${d.home} -1.5</span><b>${mk.handicap["home_-1.5"]}%</b></div>
          <div class="row"><span>${d.home} +1.5</span><b>${mk.handicap["home_+1.5"]}%</b></div>
          <div class="row"><span>${d.away} -1.5</span><b>${mk.handicap["away_-1.5"]}%</b></div>
          <div class="row"><span>${d.away} +1.5</span><b>${mk.handicap["away_+1.5"]}%</b></div>
        </div>
        <div class="block">
          <h3>Most likely scores</h3>
          <div class="scores">${cs}</div>
        </div>
        <div class="block">
          <h3>Scoreline heatmap</h3>
          ${heatmap(d.matrix, d.home, d.away)}
        </div>
      </div>
    </div>`;
}
const getPrediction = (home, away, neutral, useForm) =>
  jpost("/api/predict", { home, away, neutral, use_form: useForm });
async function showDetail(home, away, neutral) {
  const d = await getPrediction(home, away, neutral, true);
  document.getElementById("modal-body").innerHTML = predictionMarkup(d);
  document.getElementById("modal").hidden = false;
}
document.getElementById("modal-close").addEventListener("click", () => { document.getElementById("modal").hidden = true; });
document.getElementById("modal").addEventListener("click", (e) => { if (e.target.id === "modal") document.getElementById("modal").hidden = true; });

// --- rankings --------------------------------------------------------------
async function loadRankings() {
  const { teams } = await api("/api/rankings");
  const max = teams[0].elo, min = teams[teams.length - 1].elo;
  document.getElementById("rankings").innerHTML = teams.map((t) => {
    const pct = Math.round(8 + 92 * (t.elo - min) / Math.max(1, max - min));
    return `<div class="rank-row">
      <div class="num">${t.rank}</div>
      <div><div class="name">${t.name}</div><div class="tier">${t.tier}</div></div>
      <div class="rank-bar"><i style="width:${pct}%"></i></div>
      <div class="elo">${t.elo}</div></div>`;
  }).join("");
}

// --- team selects ----------------------------------------------------------
function fillTeamSelect(sel, selectedIndex = 0) {
  TEAMS.forEach((t) => sel.add(new Option(`${t.name} (${t.elo})`, t.name)));
  sel.selectedIndex = Math.min(selectedIndex, TEAMS.length - 1);
}
async function loadTeams() {
  const { teams } = await api("/api/teams");
  TEAMS = teams;
  fillTeamSelect(document.getElementById("home-team"), 0);
  fillTeamSelect(document.getElementById("away-team"), 1);
  fillTeamSelect(document.getElementById("r-home"), 0);
  fillTeamSelect(document.getElementById("r-away"), 1);
}
document.getElementById("run-matchup").addEventListener("click", async () => {
  const home = document.getElementById("home-team").value;
  const away = document.getElementById("away-team").value;
  const neutral = !document.getElementById("home-adv").checked;
  const useForm = document.getElementById("use-form").checked;
  const d = await getPrediction(home, away, neutral, useForm);
  document.getElementById("matchup-result").innerHTML = predictionMarkup(d);
});

// --- knockout simulator ----------------------------------------------------
function renderBracketPicks(size, seedTop) {
  const wrap = document.getElementById("bracket-picks");
  wrap.innerHTML = "";
  for (let i = 0; i < size; i++) {
    const sel = document.createElement("select");
    TEAMS.forEach((t) => sel.add(new Option(t.name, t.name)));
    sel.selectedIndex = seedTop ? Math.min(i, TEAMS.length - 1) : i % TEAMS.length;
    sel.className = "bracket-pick";
    wrap.appendChild(sel);
  }
}
document.getElementById("bracket-size").addEventListener("change", (e) => renderBracketPicks(+e.target.value, true));
document.getElementById("seed-top").addEventListener("click", () => renderBracketPicks(+document.getElementById("bracket-size").value, true));
document.getElementById("run-bracket").addEventListener("click", async () => {
  const teams = [...document.querySelectorAll(".bracket-pick")].map((s) => s.value);
  const res = document.getElementById("bracket-result");
  res.innerHTML = "<p class='hint'>Simulating…</p>";
  const data = await jpost("/api/bracket", { teams, sims: 20000 });
  const cols = data.rounds.map((r) => `<th>${r}</th>`).join("");
  const rows = data.teams.map((t) => `
    <tr><td>${t.team}</td>
    ${data.rounds.map((r) => `<td>${t[r]}%</td>`).join("")}
    <td class="champ">${t.champion}%</td></tr>`).join("");
  res.innerHTML = `<p class="hint">${data.sims.toLocaleString()} simulations</p>
    <table class="bracket-table"><thead><tr><th>Team</th>${cols}<th>Champion</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
});

// --- value calculator ------------------------------------------------------
document.getElementById("run-value").addEventListener("click", async () => {
  const probability = parseFloat(document.getElementById("v-prob").value);
  const odds = parseFloat(document.getElementById("v-odds").value);
  if (isNaN(probability) || isNaN(odds)) return;
  const v = await jpost("/api/value", { probability, odds });
  const cls = v.value ? "good" : "bad";
  document.getElementById("value-result").innerHTML = `
    <div class="verdict ${cls}">
      <div class="big">${v.value ? "✅ Value bet" : "❌ No value"}</div>
      <div class="row"><span>Your model probability</span><b>${probability}%</b></div>
      <div class="row"><span>Bookmaker implied probability</span><b>${v.implied_pct}%</b></div>
      <div class="row"><span>Edge (expected return)</span><b>${v.edge_pct}%</b></div>
      <div class="row"><span>Full Kelly stake</span><b>${v.kelly_pct}% of bankroll</b></div>
      <div class="row"><span>Half Kelly (safer)</span><b>${v.half_kelly_pct}% of bankroll</b></div>
    </div>`;
});

// --- results ---------------------------------------------------------------
async function loadResultsLog() {
  const { results } = await api("/api/results");
  const wrap = document.getElementById("results-log");
  if (!results.length) { wrap.innerHTML = "<p class='hint'>No results recorded yet.</p>"; return; }
  wrap.innerHTML = results.map((r) => `
    <div class="log-row">
      <span>${r.home} <b>${r.goals_home}–${r.goals_away}</b> ${r.away}</span>
      <span class="delta">${r.home} ${r.home_delta >= 0 ? "+" : ""}${r.home_delta} · ${r.away} ${r.away_delta >= 0 ? "+" : ""}${r.away_delta}</span>
    </div>`).join("");
}
document.getElementById("run-result").addEventListener("click", async () => {
  const home = document.getElementById("r-home").value;
  const away = document.getElementById("r-away").value;
  const gh = parseInt(document.getElementById("r-gh").value, 10);
  const ga = parseInt(document.getElementById("r-ga").value, 10);
  if (isNaN(gh) || isNaN(ga)) return;
  const r = await jpost("/api/result", { home, away, goals_home: gh, goals_away: ga });
  document.getElementById("result-feedback").innerHTML =
    `<div class="toast">Saved. ${r.home} ${r.home_before}→${r.home_after} (${r.home_delta >= 0 ? "+" : ""}${r.home_delta}),
     ${r.away} ${r.away_before}→${r.away_after} (${r.away_delta >= 0 ? "+" : ""}${r.away_delta}).</div>`;
  await Promise.all([loadResultsLog(), loadRankings(), refreshTeams()]);
});
document.getElementById("reset-ratings").addEventListener("click", async () => {
  if (!confirm("Reset all ratings to their seed values and clear the result log?")) return;
  await api("/api/ratings/reset", { method: "POST" });
  document.getElementById("result-feedback").innerHTML = "<div class='toast'>Ratings reset to seed values.</div>";
  await Promise.all([loadResultsLog(), loadRankings(), refreshTeams()]);
});

async function refreshTeams() {
  const { teams } = await api("/api/teams");
  TEAMS = teams;
  ["home-team", "away-team", "r-home", "r-away"].forEach((id) => {
    const el = document.getElementById(id), keep = el.selectedIndex;
    el.innerHTML = "";
    fillTeamSelect(el, keep < 0 ? 0 : keep);
  });
}

// --- boot ------------------------------------------------------------------
(async function init() {
  try {
    await loadTeams();
    await Promise.all([loadFixtures(), loadRankings(), loadResultsLog()]);
    renderBracketPicks(8, true);
  } catch (e) { /* 401 already redirected */ }
})();
