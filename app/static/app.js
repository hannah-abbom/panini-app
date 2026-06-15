"use strict";

// --- helpers ---------------------------------------------------------------
async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (res.status === 401) { window.location.href = "/login"; throw new Error("unauth"); }
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}
const jpost = (path, body) => api(path, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});
function fmtTime(v) {
  if (!v) return "";
  const d = typeof v === "number" ? new Date(v * 1000) : new Date(v);
  if (isNaN(d)) return v;
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}
function fmtDay(v) {
  const d = new Date(v); if (isNaN(d)) return "";
  return d.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
}
function heatColor(p) {
  const t = Math.min(1, Math.sqrt(p / 18));   // sqrt makes low cells visible
  return `rgb(${Math.round(16 + t * 6)},${Math.round(26 + t * 188)},${Math.round(42 + t * 40)})`;
}
function formLine(str) {
  if (!str) return "";
  return `<span class="formline">${[...str].map((c) => `<span class="f-${c}">${c}</span>`).join("")}</span>`;
}

const FLAGS = {
  "Argentina":"🇦🇷","Spain":"🇪🇸","France":"🇫🇷","Brazil":"🇧🇷","England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Portugal":"🇵🇹",
  "Netherlands":"🇳🇱","Belgium":"🇧🇪","Germany":"🇩🇪","Croatia":"🇭🇷","Uruguay":"🇺🇾","Colombia":"🇨🇴",
  "Morocco":"🇲🇦","Switzerland":"🇨🇭","United States":"🇺🇸","USA":"🇺🇸","Norway":"🇳🇴","Japan":"🇯🇵",
  "Mexico":"🇲🇽","Senegal":"🇸🇳","Ecuador":"🇪🇨","Austria":"🇦🇹","Korea Republic":"🇰🇷","South Korea":"🇰🇷",
  "Sweden":"🇸🇪","Egypt":"🇪🇬","Australia":"🇦🇺","Turkey":"🇹🇷","Turkiye":"🇹🇷","Canada":"🇨🇦",
  "Ivory Coast":"🇨🇮","Ghana":"🇬🇭","Iran":"🇮🇷","Czechia":"🇨🇿","Algeria":"🇩🇿","Tunisia":"🇹🇳",
  "Scotland":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","Paraguay":"🇵🇾","DR Congo":"🇨🇩","Bosnia and Herzegovina":"🇧🇦","South Africa":"🇿🇦",
  "Qatar":"🇶🇦","Saudi Arabia":"🇸🇦","Panama":"🇵🇦","Uzbekistan":"🇺🇿","Iraq":"🇮🇶","Jordan":"🇯🇴",
  "Cape Verde":"🇨🇻","New Zealand":"🇳🇿","Curacao":"🇨🇼","Haiti":"🇭🇹",
};
const flag = (n) => FLAGS[n] || "🏳️";

const TEAM_COLORS = {
  "Argentina":"#6ca6e0","Spain":"#e63946","France":"#3b5fb0","Brazil":"#f7d000","England":"#e8e8e8",
  "Portugal":"#c8102e","Netherlands":"#f36c21","Belgium":"#e8b923","Germany":"#dadada","Croatia":"#e63946",
  "Uruguay":"#5fa8d3","Colombia":"#f7d000","Morocco":"#c1272d","Switzerland":"#d52b1e","United States":"#3c3b6e",
  "USA":"#3c3b6e","Norway":"#ba0c2f","Japan":"#1b1f7a","Mexico":"#0a7d3e","Senegal":"#00853f","Ecuador":"#ffd100",
  "Austria":"#ed2939","Korea Republic":"#c8102e","South Korea":"#c8102e","Sweden":"#ffcd00","Egypt":"#c8102e",
  "Australia":"#0a7d3e","Turkey":"#e30a17","Turkiye":"#e30a17","Canada":"#d80621","Ivory Coast":"#f77f00",
  "Ghana":"#ce1126","Iran":"#239f40","Czechia":"#11457e","Algeria":"#007a3d","Tunisia":"#e70013","Scotland":"#0065bf",
  "Paraguay":"#d52b1e","DR Congo":"#3da5e0","Bosnia and Herzegovina":"#002395","South Africa":"#007a4d",
  "Qatar":"#8a1538","Saudi Arabia":"#006c35","Panama":"#db0a16","Uzbekistan":"#1eb53a","Iraq":"#ce1126",
  "Jordan":"#007a3d","Cape Verde":"#003893","New Zealand":"#000000","Curacao":"#002b7f","Haiti":"#00209f",
};
const teamColor = (n) => TEAM_COLORS[n] || "#5a6678";

function countUp(el) {
  const m = el.textContent.trim().match(/^([\d.]+)(.*)$/);
  if (!m) return;
  const target = parseFloat(m[1]), suffix = m[2], dec = (m[1].split(".")[1] || "").length;
  const start = performance.now(), dur = 550;
  (function step(t) {
    const p = Math.min(1, (t - start) / dur);
    const v = target * (0.5 - 0.5 * Math.cos(Math.PI * p));
    el.textContent = v.toFixed(dec) + suffix;
    if (p < 1) requestAnimationFrame(step); else el.textContent = m[1] + suffix;
  })(start);
}
function animateDetail(container) {
  container.querySelectorAll(".poll-row b, .odds b").forEach(countUp);
}

// --- state -----------------------------------------------------------------
let TEAMS = [], ALL_FIXTURES = [], SELECTED = null;

// --- nav -------------------------------------------------------------------
document.querySelectorAll(".rail-item[data-tab]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".rail-item").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});
document.getElementById("logout").addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" }); window.location.href = "/login";
});

// --- match list ------------------------------------------------------------
function rowMarkup(fx) {
  const p = fx.prediction, fin = fx.status === "finished", live = fx.status === "live";
  const mid = live
    ? `<span class="score livescore">${fx.score}</span><span class="livelbl">● LIVE</span>`
    : fin
    ? `<span class="score">${fx.score}</span><span class="ftlabel">FT</span>`
    : `${fmtTime(fx.utc_date)}`;
  return `
    <div class="mrow" data-id="${fx.id}">
      <span class="home"><span class="nm">${fx.home}</span><span class="flag">${flag(fx.home)}</span></span>
      <span class="mid">${mid}</span>
      <span class="away"><span class="flag">${flag(fx.away)}</span><span class="nm">${fx.away}</span></span>
      <span class="winbar">
        <i class="s-h" style="width:${p.home_win}%"></i>
        <i class="s-d" style="width:${p.draw}%"></i>
        <i class="s-a" style="width:${p.away_win}%"></i>
      </span>
      ${!fin && !live && p.tip ? `<span class="rowtip">🎯 ${p.tip.selection} <b>@ ${p.tip.odds}</b> ${stars(p.tip.stars)}</span>` : ""}
    </div>`;
}
function renderMatchList(list) {
  const wrap = document.getElementById("matchlist");
  const groups = {};
  list.forEach((fx) => { (groups[fx.round] = groups[fx.round] || []).push(fx); });
  wrap.innerHTML = Object.keys(groups).sort().map((g) =>
    `<div class="group-head">${g}</div><div class="grp">${groups[g].map(rowMarkup).join("")}</div>`
  ).join("");
  wrap.querySelectorAll(".mrow").forEach((row) => {
    row.addEventListener("click", () => {
      const fx = ALL_FIXTURES.find((f) => f.id === row.dataset.id);
      wrap.querySelectorAll(".mrow").forEach((r) => r.classList.remove("sel"));
      row.classList.add("sel");
      selectMatch(fx);
    });
  });
}
let FILTER_READY = false;
function applyFilter() {
  const sel = document.getElementById("round-filter");
  renderMatchList(sel.value ? ALL_FIXTURES.filter((f) => f.round === sel.value) : ALL_FIXTURES);
  if (SELECTED) {
    const row = document.querySelector(`.mrow[data-id="${SELECTED.id}"]`);
    if (row) row.classList.add("sel");
  }
}
async function loadFixtures() {
  const data = await api("/api/fixtures");
  const badge = document.getElementById("source-badge");
  const anyLive = data.fixtures.some((f) => f.status === "live");
  if (anyLive) { badge.textContent = "● live games in play"; badge.classList.add("live"); }
  else if (data.live) { badge.textContent = "live · " + data.source; badge.classList.add("live"); }
  else { badge.textContent = data.source || "schedule"; badge.classList.remove("live"); }
  ALL_FIXTURES = data.fixtures;
  if (!FILTER_READY) {
    const sel = document.getElementById("round-filter");
    [...new Set(data.fixtures.map((f) => f.round))].forEach((r) => sel.add(new Option(r, r)));
    sel.onchange = applyFilter;
    FILTER_READY = true;
  }
  applyFilter();
  if (!SELECTED) {
    const first = ALL_FIXTURES.find((f) => f.status === "live")
      || ALL_FIXTURES.find((f) => f.status !== "finished") || ALL_FIXTURES[0];
    if (first) { selectMatch(first); const r = document.querySelector(`.mrow[data-id="${first.id}"]`); if (r) r.classList.add("sel"); }
  }
}
function startLivePolling() {
  setInterval(async () => {
    try {
      const data = await api("/api/fixtures");
      ALL_FIXTURES = data.fixtures;
      const badge = document.getElementById("source-badge");
      const anyLive = data.fixtures.some((f) => f.status === "live");
      badge.textContent = anyLive ? "● live games in play" : (data.live ? "live · " + data.source : data.source);
      badge.classList.toggle("live", anyLive || data.live);
      applyFilter();
      if (SELECTED && SELECTED.status === "live") {
        const fresh = ALL_FIXTURES.find((f) => f.id === SELECTED.id);
        if (fresh) selectMatch(fresh);
      }
    } catch (e) { /* ignore transient */ }
  }, 40000);
}

// --- detail rendering (FotMob style) --------------------------------------
function insightText(fx, d) {
  const r = d.result;
  if (fx.status === "finished") {
    return `Full time: <b>${fx.home} ${fx.score} ${fx.away}</b>. Pre-match model: ${fx.home} ${r.home_win}% · draw ${r.draw}% · ${fx.away} ${r.away_win}%.`;
  }
  const arr = [["home", r.home_win, fx.home], ["away", r.away_win, fx.away], ["draw", r.draw, "draw"]];
  arr.sort((a, b) => b[1] - a[1]);
  const top = arr[0];
  if (top[0] === "draw") return `Closely matched — the model slightly favours a <b>draw</b> (${r.draw}%).`;
  const opp = top[0] === "home" ? fx.away : fx.home;
  return `<b>${top[2]}</b> are ${top[1]}% likely to beat ${opp}.`;
}
const odd = (pct) => (pct > 0 ? (100 / pct).toFixed(2) : "—");
function marketsMarkup(fx, d) {
  const ou = d.goals.over_under, mk = d.markets, r = d.result;
  const cs = d.correct_scores.map((c) => `<span class="chip">${c.score} <b>${c.prob}%</b></span>`).join("");
  return `<div class="mk-grid">
    <div class="block"><h3>Betting odds (model fair value)</h3>
      <div class="row"><span>${fx.home} win</span><b>${r.fair_odds.home ?? "—"}</b></div>
      <div class="row"><span>Draw</span><b>${r.fair_odds.draw ?? "—"}</b></div>
      <div class="row"><span>${fx.away} win</span><b>${r.fair_odds.away ?? "—"}</b></div>
      <div class="row"><span>Over 2.5 / Under 2.5</span><span>${odd(ou["2.5"].over)} / ${odd(ou["2.5"].under)}</span></div>
      <div class="row"><span>BTTS Yes / No</span><span>${odd(d.goals.btts.yes)} / ${odd(d.goals.btts.no)}</span></div>
    </div>
    <div class="block"><h3>Double chance &amp; qualify</h3>
      <div class="row"><span>${fx.home} or draw (1X)</span><b>${d.result.double_chance["1X"]}%</b></div>
      <div class="row"><span>${fx.away} or draw (X2)</span><b>${d.result.double_chance["X2"]}%</b></div>
      <div class="row"><span>To qualify (ET/pens)</span><span>${d.advance.home}% / ${d.advance.away}%</span></div>
      <div class="row"><span>Expected points</span><span>${d.result.expected_points.home} / ${d.result.expected_points.away}</span></div>
    </div>
    <div class="block"><h3>Goals</h3>
      <div class="row"><span>Over 1.5 / 2.5 / 3.5</span><b>${ou["1.5"].over}% / ${ou["2.5"].over}% / ${ou["3.5"].over}%</b></div>
      <div class="row"><span>Both teams to score</span><b>${d.goals.btts.yes}%</b></div>
      <div class="row"><span>Clean sheet ${fx.home} / ${fx.away}</span><span>${mk.clean_sheet.home}% / ${mk.clean_sheet.away}%</span></div>
      <div class="row"><span>Win to nil ${fx.home} / ${fx.away}</span><span>${mk.win_to_nil.home}% / ${mk.win_to_nil.away}%</span></div>
    </div>
    <div class="block"><h3>Handicap (goal line)</h3>
      <div class="row"><span>${fx.home} -1.5</span><b>${mk.handicap["home_-1.5"]}%</b></div>
      <div class="row"><span>${fx.home} +1.5</span><b>${mk.handicap["home_+1.5"]}%</b></div>
      <div class="row"><span>${fx.away} -1.5</span><b>${mk.handicap["away_-1.5"]}%</b></div>
      <div class="row"><span>${fx.away} +1.5</span><b>${mk.handicap["away_+1.5"]}%</b></div>
    </div>
    <div class="block"><h3>Most likely scores</h3><div class="scores">${cs}</div></div>
  </div>`;
}
const stars = (n) => "★★★".slice(0, n) + "☆☆☆".slice(0, 3 - n);
function statBlock(name, s, unit) {
  const lines = Object.entries(s.lines || {}).map(([l, v]) =>
    `<div class="row"><span>Over ${l}</span><b>${v.over}%</b></div>`).join("");
  return `<div class="block"><h3>${name}</h3>
    <div class="row"><span>Expected total</span><b>${s.total}</b></div>
    <div class="row"><span>Split (H / A)</span><span>${s.home} / ${s.away}</span></div>${lines}</div>`;
}
function statsMarkup(d) {
  const s = d.stats;
  return `<div class="mk-grid">
    ${statBlock("Corners", s.corners)}
    ${statBlock("Cards (yellows)", s.cards)}
    ${statBlock("Shots on target", s.shots_on_target)}
    <div class="block"><h3>Fouls</h3>
      <div class="row"><span>Expected total</span><b>${s.fouls.total}</b></div>
      <div class="row"><span>Split (H / A)</span><span>${s.fouls.home} / ${s.fouls.away}</span></div></div>
  </div>`;
}
function tipBanner(d) {
  if (!d.tip) return "";
  const t = d.tip;
  return `<div class="tip-banner c${t.stars}">
    <div class="tip-label">🎯 Top tip · <span class="conf">${t.confidence} confidence ${stars(t.stars)}</span></div>
    <div class="tip-pick">${t.selection}</div>
    <div class="tip-odds">${t.prob}% · fair odds <b>${t.odds}</b></div>
  </div>`;
}
function heatmapMarkup(d) {
  const m = d.matrix;
  let mx = 0, mi = 0, mj = 0;
  for (let i = 0; i < 6; i++) for (let j = 0; j < 6; j++) if (m[i][j] > mx) { mx = m[i][j]; mi = i; mj = j; }
  let grid = `<div class="hm-corner"></div>`;
  for (let j = 0; j < 6; j++) grid += `<div class="hm-ax">${j}</div>`;
  for (let i = 0; i < 6; i++) {
    grid += `<div class="hm-ax">${i}</div>`;
    for (let j = 0; j < 6; j++) {
      const v = m[i][j], sel = (i === mi && j === mj) ? " sel" : "";
      grid += `<div class="hm-cell${sel}" style="background:${heatColor(v)}" title="${i}-${j}: ${v}%">${v >= 2 ? v : ""}</div>`;
    }
  }
  return `<div class="hm">
    <div class="hm-toplbl">${flag(d.away)} ${d.away} goals →</div>
    <div class="hm-grid">${grid}</div>
    <div class="hm-sidelbl">↓ ${flag(d.home)} ${d.home} goals</div>
    <div class="heat-cap">Brightest cell is the most likely score — <b>${d.expected.most_likely_score}</b> at ${mx}%.</div>
  </div>`;
}
function detailMarkup(fx, d) {
  const fin = fx.status === "finished", live = fx.status === "live";
  const hf = d.form && d.form.home ? formLine(d.form.home.string) : "";
  const af = d.form && d.form.away ? formLine(d.form.away.string) : "";
  const center = live
    ? `<div class="dt-score">${fx.score}</div><div class="dt-ft livenow">● LIVE</div><div class="dt-status">${fx.round}</div>`
    : fin
    ? `<div class="dt-score">${fx.score}</div><div class="dt-ft">FULL TIME</div><div class="dt-status">${fx.round}</div>`
    : `<div class="dt-time">${fmtTime(fx.utc_date)}</div><div class="dt-status">${fmtDay(fx.utc_date)} · ${fx.round}</div>`;
  const fo = d.result.fair_odds;
  return `
    <div class="dt-head" style="--ch:${teamColor(fx.home)};--ca:${teamColor(fx.away)}">
      <div class="dt-team"><div class="dt-flag">${flag(fx.home)}</div><div class="dt-name">${fx.home}</div>
        <div class="dt-sub">Elo ${d.home_elo} ${hf}</div></div>
      <div class="dt-center">${center}</div>
      <div class="dt-team"><div class="dt-flag">${flag(fx.away)}</div><div class="dt-name">${fx.away}</div>
        <div class="dt-sub">Elo ${d.away_elo} ${af}</div></div>
    </div>
    ${tipBanner(d)}
    <div class="dt-tabs">
      <button class="dt-tab active" data-sub="pred">Prediction</button>
      <button class="dt-tab" data-sub="mkts">Markets</button>
      <button class="dt-tab" data-sub="stats">Stats</button>
      <button class="dt-tab" data-sub="heat">Heatmap</button>
    </div>
    <div class="dt-sub-panel active" data-sub="pred">
      <div class="insight">💡 ${insightText(fx, d)}</div>
      <div class="odds-row">
        <div class="odds"><span>1 · ${fx.home}</span><b>${fo.home ?? "—"}</b></div>
        <div class="odds"><span>X · Draw</span><b>${fo.draw ?? "—"}</b></div>
        <div class="odds"><span>2 · ${fx.away}</span><b>${fo.away ?? "—"}</b></div>
      </div>
      <div class="poll">
        <div class="poll-title">Who will win?</div>
        <div class="poll-row"><span>${fx.home}</span><div class="poll-track"><i class="home" style="width:${d.result.home_win}%"></i></div><b>${d.result.home_win}%</b></div>
        <div class="poll-row"><span>Draw</span><div class="poll-track"><i class="draw" style="width:${d.result.draw}%"></i></div><b>${d.result.draw}%</b></div>
        <div class="poll-row"><span>${fx.away}</span><div class="poll-track"><i class="away" style="width:${d.result.away_win}%"></i></div><b>${d.result.away_win}%</b></div>
      </div>
      <div class="block"><h3>Model expectation</h3>
        <div class="row"><span>Expected goals</span><b>${d.expected.goals_home} – ${d.expected.goals_away}</b></div>
        <div class="row"><span>Most likely score</span><b>${d.expected.most_likely_score}</b></div>
        <div class="row"><span>Total goals · BTTS</span><span>${d.expected.total} · ${d.goals.btts.yes}%</span></div>
      </div>
    </div>
    <div class="dt-sub-panel" data-sub="mkts">${marketsMarkup(fx, d)}</div>
    <div class="dt-sub-panel" data-sub="stats">${statsMarkup(d)}</div>
    <div class="dt-sub-panel" data-sub="heat">${heatmapMarkup(d)}</div>`;
}
function wireSubTabs(container) {
  container.querySelectorAll(".dt-tab").forEach((t) => {
    t.addEventListener("click", () => {
      container.querySelectorAll(".dt-tab").forEach((x) => x.classList.remove("active"));
      container.querySelectorAll(".dt-sub-panel").forEach((x) => x.classList.remove("active"));
      t.classList.add("active");
      container.querySelector(`.dt-sub-panel[data-sub="${t.dataset.sub}"]`).classList.add("active");
    });
  });
}
async function selectMatch(fx) {
  SELECTED = fx;
  const pane = document.getElementById("detail-pane");
  pane.innerHTML = `<div class="detail-empty"><p>Loading…</p></div>`;
  const d = await getPrediction(fx.home, fx.away, true, true);
  pane.innerHTML = detailMarkup(fx, d);
  wireSubTabs(pane);
  animateDetail(pane);
}
const getPrediction = (home, away, neutral, useForm) =>
  jpost("/api/predict", { home, away, neutral, use_form: useForm });

// --- rankings --------------------------------------------------------------
async function loadRankings() {
  const { teams } = await api("/api/rankings");
  const max = teams[0].elo, min = teams[teams.length - 1].elo;
  document.getElementById("rankings").innerHTML = teams.map((t) => {
    const pct = Math.round(8 + 92 * (t.elo - min) / Math.max(1, max - min));
    return `<div class="rank-row"><div class="num">${t.rank}</div><div class="rflag">${flag(t.name)}</div>
      <div><div class="name">${t.name}</div><div class="tier">${t.tier}</div></div>
      <div class="rank-bar"><i style="width:${pct}%"></i></div><div class="elo">${t.elo}</div></div>`;
  }).join("");
}

// --- tips board + accumulator ----------------------------------------------
let ACCA = [];   // [{key, label, odds}]
function accaRefresh() {
  const combined = ACCA.reduce((a, l) => a * l.odds, 1);
  const stake = parseFloat(document.getElementById("acca-stake").value) || 0;
  document.getElementById("acca-count").textContent = ACCA.length;
  document.getElementById("acca-odds").textContent = combined.toFixed(2);
  document.getElementById("acca-return").textContent = (combined * stake).toFixed(2);
  document.querySelectorAll(".bc-pick").forEach((b) => {
    b.classList.toggle("on", ACCA.some((l) => l.key === b.dataset.key));
  });
}
function accaToggle(key, label, odds) {
  const i = ACCA.findIndex((l) => l.key === key);
  if (i >= 0) ACCA.splice(i, 1); else ACCA.push({ key, label, odds });
  accaRefresh();
}
document.getElementById("acca-stake").addEventListener("input", accaRefresh);
document.getElementById("acca-clear").addEventListener("click", () => { ACCA = []; accaRefresh(); });

async function loadTips() {
  const data = await api("/api/tips");
  const bod = data.bet_of_the_day;
  const bodEl = document.getElementById("bet-of-day");
  if (bod) {
    bodEl.innerHTML = `<div class="bod">
      <div class="bod-tag">⭐ Bet of the day</div>
      <div class="bod-match">${flag(bod.home)} ${bod.home} vs ${bod.away} ${flag(bod.away)}<span class="bod-grp">${bod.round}</span></div>
      <div class="bod-pick">${bod.tip.selection}</div>
      <div class="bod-meta">${bod.tip.confidence} confidence ${stars(bod.tip.stars)} · ${bod.tip.prob}% · fair odds <b>${bod.tip.odds}</b></div>
    </div>`;
  }
  const board = document.getElementById("tips-board");
  board.innerHTML = data.tips.map((b) => {
    const r = b.result || { home_win: 0, draw: 0, away_win: 0 };
    const picks = (b.picks && b.picks.length ? b.picks : [b.tip]).map((p) => {
      const key = `${b.id}|${p.selection}`;
      return `<button class="bc-pick c${p.stars}" data-key="${key}" data-label="${b.home}-${b.away}: ${p.selection}" data-odds="${p.odds}">
        <span class="bcp-sel">${p.selection} ${stars(p.stars)}</span>
        <span class="bcp-od">@ ${p.odds}</span></button>`;
    }).join("");
    return `<div class="bet-card c${b.tip.stars}">
      <div class="bc-top">
        <span class="bc-teams">${flag(b.home)} ${b.home} <i>v</i> ${b.away} ${flag(b.away)}</span>
        <span class="bc-when">${b.round} · ${fmtDay(b.utc_date)}</span>
      </div>
      <div class="bc-bar"><i class="s-h" style="width:${r.home_win}%"></i><i class="s-d" style="width:${r.draw}%"></i><i class="s-a" style="width:${r.away_win}%"></i></div>
      <div class="bc-prob"><span>${b.home} ${r.home_win}%</span><span>Draw ${r.draw}%</span><span>${b.away} ${r.away_win}%</span></div>
      <div class="bc-picks">${picks}</div>
    </div>`;
  }).join("");
  board.querySelectorAll(".bc-pick").forEach((btn) => {
    btn.addEventListener("click", () => accaToggle(btn.dataset.key, btn.dataset.label, parseFloat(btn.dataset.odds)));
  });
  accaRefresh();
}

// --- news ------------------------------------------------------------------
async function loadNews() {
  const wrap = document.getElementById("newslist");
  try {
    const { items } = await api("/api/news");
    if (!items.length) {
      wrap.innerHTML = "<p class='hint'>No news right now (the feeds may be unreachable from this server).</p>";
      return;
    }
    wrap.innerHTML = items.map((n) => `
      <a class="news-card" href="${n.link}" target="_blank" rel="noopener">
        <div class="news-src">${n.source}</div>
        <div class="news-title">${n.title}</div>
        <div class="news-date">${n.date || ""}</div>
      </a>`).join("");
  } catch (e) {
    wrap.innerHTML = "<p class='hint'>Couldn't load news.</p>";
  }
}

// --- team selects ----------------------------------------------------------
function fillTeamSelect(sel, idx = 0) {
  TEAMS.forEach((t) => sel.add(new Option(`${flag(t.name)} ${t.name} (${t.elo})`, t.name)));
  sel.selectedIndex = Math.min(idx, TEAMS.length - 1);
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
  const fx = { home, away, round: "Custom matchup", status: "upcoming", utc_date: null };
  const el = document.getElementById("matchup-result");
  el.innerHTML = detailMarkup(fx, d);
  wireSubTabs(el);
  animateDetail(el);
});

// --- knockout --------------------------------------------------------------
function renderBracketPicks(size) {
  const wrap = document.getElementById("bracket-picks");
  wrap.innerHTML = "";
  for (let i = 0; i < size; i++) {
    const sel = document.createElement("select");
    sel.className = "bracket-pick pill-select";
    TEAMS.forEach((t) => sel.add(new Option(`${flag(t.name)} ${t.name}`, t.name)));
    sel.selectedIndex = Math.min(i, TEAMS.length - 1);
    wrap.appendChild(sel);
  }
}
document.getElementById("bracket-size").addEventListener("change", (e) => renderBracketPicks(+e.target.value));
document.getElementById("seed-top").addEventListener("click", () => renderBracketPicks(+document.getElementById("bracket-size").value));
document.getElementById("run-bracket").addEventListener("click", async () => {
  const teams = [...document.querySelectorAll(".bracket-pick")].map((s) => s.value);
  const res = document.getElementById("bracket-result");
  res.innerHTML = "<p class='hint'>Simulating…</p>";
  const data = await jpost("/api/bracket", { teams, sims: 20000 });
  const cols = data.rounds.map((r) => `<th>${r}</th>`).join("");
  const rows = data.teams.map((t) => `<tr><td>${flag(t.team)} ${t.team}</td>${data.rounds.map((r) => `<td>${t[r]}%</td>`).join("")}<td class="champ">${t.champion}%</td></tr>`).join("");
  res.innerHTML = `<p class="hint">${data.sims.toLocaleString()} simulations</p>
    <table class="bracket-table"><thead><tr><th>Team</th>${cols}<th>Champion</th></tr></thead><tbody>${rows}</tbody></table>`;
});

// --- value -----------------------------------------------------------------
document.getElementById("run-value").addEventListener("click", async () => {
  const probability = parseFloat(document.getElementById("v-prob").value);
  const odds = parseFloat(document.getElementById("v-odds").value);
  if (isNaN(probability) || isNaN(odds)) return;
  const v = await jpost("/api/value", { probability, odds });
  document.getElementById("value-result").innerHTML = `
    <div class="verdict ${v.value ? "good" : "bad"}">
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
  if (!results.length) { wrap.innerHTML = "<p class='hint'>No manually recorded results yet.</p>"; return; }
  wrap.innerHTML = results.map((r) => `<div class="log-row">
      <span>${flag(r.home)} ${r.home} <b>${r.goals_home}–${r.goals_away}</b> ${r.away} ${flag(r.away)}</span>
      <span class="delta">${r.home} ${r.home_delta >= 0 ? "+" : ""}${r.home_delta} · ${r.away} ${r.away_delta >= 0 ? "+" : ""}${r.away_delta}</span>
    </div>`).join("");
}
document.getElementById("run-result").addEventListener("click", async () => {
  const home = document.getElementById("r-home").value, away = document.getElementById("r-away").value;
  const gh = parseInt(document.getElementById("r-gh").value, 10), ga = parseInt(document.getElementById("r-ga").value, 10);
  if (isNaN(gh) || isNaN(ga)) return;
  const r = await jpost("/api/result", { home, away, goals_home: gh, goals_away: ga });
  document.getElementById("result-feedback").innerHTML =
    `<div class="toast">Saved. ${r.home} ${r.home_before}→${r.home_after} (${r.home_delta >= 0 ? "+" : ""}${r.home_delta}), ${r.away} ${r.away_before}→${r.away_after} (${r.away_delta >= 0 ? "+" : ""}${r.away_delta}).</div>`;
  await Promise.all([loadResultsLog(), loadRankings(), refreshTeams()]);
});
document.getElementById("reset-ratings").addEventListener("click", async () => {
  if (!confirm("Reset all ratings to their seed + played-results baseline?")) return;
  await api("/api/ratings/reset", { method: "POST" });
  document.getElementById("result-feedback").innerHTML = "<div class='toast'>Ratings reset.</div>";
  await Promise.all([loadResultsLog(), loadRankings(), refreshTeams()]);
});
async function refreshTeams() {
  const { teams } = await api("/api/teams"); TEAMS = teams;
  ["home-team", "away-team", "r-home", "r-away"].forEach((id) => {
    const el = document.getElementById(id), keep = el.selectedIndex; el.innerHTML = "";
    fillTeamSelect(el, keep < 0 ? 0 : keep);
  });
}

// --- AI helper -------------------------------------------------------------
const CHAT = [];
const escHtml = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const fmtMsg = (s) => escHtml(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
function chatBubble(role, text) {
  const wrap = document.getElementById("chat-msgs");
  const div = document.createElement("div");
  div.className = "chat-msg " + role;
  if (role === "bot") div.innerHTML = fmtMsg(text); else div.textContent = text;
  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
  return div;
}
function addChips() {
  const wrap = document.getElementById("chat-msgs");
  const div = document.createElement("div");
  div.className = "chat-chips";
  ["Best bets", "Build me an acca", "Value picks", "Brazil vs Morocco", "Group H"].forEach((c) => {
    const b = document.createElement("button");
    b.className = "chat-chip"; b.type = "button"; b.textContent = c;
    b.addEventListener("click", () => {
      document.getElementById("chat-input").value = c;
      document.getElementById("chat-form").requestSubmit();
    });
    div.appendChild(b);
  });
  wrap.appendChild(div);
}
function initChat(aiEnabled) {
  const fab = document.getElementById("chat-fab");
  const panel = document.getElementById("chat-panel");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  fab.addEventListener("click", () => {
    const open = panel.hasAttribute("hidden");
    if (open) {
      panel.removeAttribute("hidden");
      if (!CHAT.length) {
        chatBubble("bot", "Hi, I'm **Predi AI** ⚽ — your World Cup betting assistant. Ask me for the **best bets**, a match prediction, an accumulator, or tap a suggestion below."
          + (aiEnabled ? "" : ""));
        addChips();
      }
      input.focus();
    } else {
      panel.setAttribute("hidden", "");
    }
  });
  document.getElementById("chat-close").addEventListener("click", () => panel.setAttribute("hidden", ""));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    CHAT.push({ role: "user", content: text });
    chatBubble("user", text);
    const typing = chatBubble("bot typing", "…");
    try {
      const res = await jpost("/api/chat", { messages: CHAT });
      typing.remove();
      CHAT.push({ role: "assistant", content: res.reply });
      chatBubble("bot", res.reply);
    } catch (err) {
      typing.remove();
      chatBubble("bot", "Sorry, I couldn't answer that just now.");
    }
  });
}

// --- theme -----------------------------------------------------------------
(function initTheme() {
  const btn = document.getElementById("theme-toggle");
  const apply = (t) => {
    document.body.classList.toggle("light", t === "light");
    btn.querySelector(".ico").textContent = t === "light" ? "☀️" : "🌙";
  };
  apply(localStorage.getItem("theme") || "dark");
  btn.addEventListener("click", () => {
    const t = document.body.classList.contains("light") ? "dark" : "light";
    localStorage.setItem("theme", t);
    apply(t);
  });
})();

// --- boot ------------------------------------------------------------------
async function loadMeta() {
  try {
    const m = await api("/api/meta");
    const lo = document.getElementById("logout");
    if (lo) lo.hidden = !m.auth_required;
    initChat(!!m.ai_enabled);
  } catch (e) { initChat(false); }
}
(async function init() {
  try {
    await loadMeta();
    await loadTeams();
    await Promise.all([loadFixtures(), loadTips(), loadRankings(), loadResultsLog(), loadNews()]);
    renderBracketPicks(8);
    startLivePolling();
  } catch (e) { /* 401 redirected */ }
})();
