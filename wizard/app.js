// BukuStudio setup wizard. Rules mirror engine/settings.py; keep them in sync.
import { art, bookMockup } from "./art.js";

const $app = document.getElementById("app");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch {} },
};

let STEPS = [];
let s = {};
let index = 0;
let kidMode = store.get("kidMode") === "1";
let compareOpen = false;
let spot = 0;
let spotFor = null;
let errors = {};
let finished = false;

// --- rules (same as engine/settings.py) ---------------------------------

const matches = (cond = {}, st) => Object.entries(cond).every(([k, vals]) => vals.includes(st[k]));
const stepActive = (step, st) => matches(step.only_for, st);
const available = (step, st) => (step.options || []).filter((o) => matches(o.only_for, st));

function recommended(step, st) {
  const opts = available(step, st);
  if (step.kind === "multi") return opts.filter((o) => o.default_on).map((o) => o.value);
  const values = opts.map((o) => o.value);
  const r = step.recommend;
  const v = r ? (r.map[String(st[r.by])] ?? r.else) : step.default;
  return values.includes(v) ? v : values[0] ?? null;
}

function optionWarnings(step, value, st) {
  const opt = (step.options || []).find((o) => o.value === value);
  const out = [];
  for (const w of opt?.warn || []) {
    if (w.when && matches(w.when, st)) out.push(w.text);
    if (w.when_below && Object.entries(w.when_below).every(([k, n]) => typeof st[k] === "number" && st[k] < n)) out.push(w.text);
  }
  return out;
}

function fill(st) {
  for (const step of STEPS) {
    if (step.kind !== "cards" && step.kind !== "multi") continue;
    if (!stepActive(step, st)) { st[step.id] = null; continue; }
    const values = available(step, st).map((o) => o.value);
    if (step.kind === "multi") st[step.id] = st[step.id] == null ? recommended(step, st) : st[step.id].filter((v) => values.includes(v));
    else if (!values.includes(st[step.id])) st[step.id] = recommended(step, st);
  }
  return st;
}
const fillAll = () => fill(s);

// Count steps against a filled copy so later steps that depend on unanswered
// choices (like cover finish) don't make the total jump.
const activeSteps = () => {
  const preview = fill({ ...s });
  return STEPS.filter((st) => st.kind === "story" || st.kind === "summary" ||
    (stepActive(st, preview) && (st.kind === "multi" || available(st, preview).length > 1)));
};
const current = () => activeSteps()[index];

// --- saving -------------------------------------------------------------

async function save(final = false) {
  try {
    await fetch("/api/save/book-settings.json", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...s, version: 1, ...(final ? { _final: true } : {}) }),
    });
    return true;
  } catch {
    return false;
  }
}

// --- rendering ----------------------------------------------------------

function header(step) {
  const steps = activeSteps();
  const pct = Math.round(((index + 1) / steps.length) * 100);
  return `<div class="top">
      <span class="count">Step ${index + 1} of ${steps.length}</span>
      <div class="tools">
        <button id="kid" aria-pressed="${kidMode}">Kid mode</button>
        <button id="read">🔊 Read it to me</button>
      </div>
    </div>
    <div class="bar"><div style="width:${pct}%"></div></div>
    <h1>${esc(step.title)}</h1><p class="sub">${esc(step.subtitle || "")}</p>`;
}

function card(step, opt, selected, rec) {
  return `<button class="card${selected ? " sel" : ""}" data-v="${esc(JSON.stringify(opt.value))}" aria-pressed="${selected}">
      <div class="art">${art(step.id, opt, s)}</div>
      <span class="badge${rec ? "" : " hidden"}">⭐ Recommended</span>
      <p class="nm">${esc(opt.name)}</p>
      <p class="ds">${esc(opt.desc)}</p>
      <span class="tick">✓ ${step.kind === "multi" ? "Added" : "Selected"}</span>
    </button>`;
}

function cardsBody(step) {
  const opts = available(step, s);
  const rec = recommended(step, s);
  const isRec = (v) => (step.kind === "multi" ? false : v === rec);
  const isSel = (v) => (step.kind === "multi" ? (s[step.id] || []).includes(v) : s[step.id] === v);
  let html;
  if (kidMode && step.kind === "cards") {
    if (spotFor !== step.id) { spot = Math.max(0, opts.findIndex((o) => o.value === s[step.id])); spotFor = step.id; }
    spot = Math.max(0, Math.min(spot, opts.length - 1));
    const o = opts[spot];
    html = `<div class="spot">
        <button class="arrow" id="prev" aria-label="Previous">‹</button>
        ${card(step, o, isSel(o.value), isRec(o.value))}
        <button class="arrow" id="next-opt" aria-label="Next">›</button>
      </div>
      <div class="dots">${opts.map((_, i) => `<span class="${i === spot ? "on" : ""}"></span>`).join("")}</div>`;
  } else {
    html = `<div class="grid">${opts.map((o) => card(step, o, isSel(o.value), isRec(o.value))).join("")}</div>`;
  }

  if (step.kind === "multi" && (s.extras || []).includes("dedication") && step.id === "extras") {
    html += `<label for="ded">Dedication <span class="hint">(optional, you can add it later)</span></label>
      <input id="ded" maxlength="160" placeholder="For Grandma, who tells the best stories" value="${esc(s.dedicationText || "")}">`;
  }

  if (step.kind === "cards") {
    const opt = opts.find((o) => o.value === s[step.id]);
    const tip = s.imageService === "none" && opt?.tip_no_service ? opt.tip_no_service : opt?.tip;
    if (tip) html += `<div class="info"><b>Good to know:</b> ${esc(tip)}</div>`;
    if (step.id === "artStyle" && s.imageService === "none") {
      html += `<div class="info">🎨 <b>Claude will draw your pictures.</b> No image service is set up, and none is needed.
        If you add one later (an OpenAI or Gemini key), BukuStudio can also make painted pictures.</div>`;
    }
    for (const w of optionWarnings(step, s[step.id], s)) html += `<div class="warn">⚠️ ${esc(w)}</div>`;
    if (opts.some((o) => o.facts)) {
      html += `<p style="margin:12px 0 0"><button class="link" id="compare">${compareOpen ? "Hide comparison" : "Compare these side by side"}</button></p>`;
      if (compareOpen) {
        const keys = [...new Set(opts.flatMap((o) => Object.keys(o.facts || {})))];
        html += `<table class="compare"><tr><th></th>${opts.map((o) => `<th>${esc(o.name)}</th>`).join("")}</tr>
          ${keys.map((k) => `<tr><td>${esc(k)}</td>${opts.map((o) => `<td>${esc(o.facts?.[k] ?? "—")}</td>`).join("")}</tr>`).join("")}</table>`;
      }
    }
  }
  return html;
}

function storyBody() {
  const err = (k) => (errors[k] ? `<div class="error">${esc(errors[k])}</div>` : "");
  return `<label for="story">Your story <span class="hint">(a few lines up to a full draft)</span></label>
    <textarea id="story" placeholder="Once upon a time, a little fox found a fallen star in the forest...">${esc(s.story || "")}</textarea>${err("story")}
    <label for="author">Author name <span class="hint">(printed on the cover)</span></label>
    <input id="author" placeholder="Sam Rivera" value="${esc(s.author || "")}">${err("author")}
    <label for="coauthor">Co-author or illustrator <span class="hint">(optional)</span></label>
    <input id="coauthor" placeholder="Illustrated by Dad" value="${esc(s.coauthor || "")}">
    <label for="language">Language</label>
    <select id="language">${["English", "Spanish", "French", "German", "Hindi", "Tamil", "Telugu", "Malayalam", "Indonesian", "Portuguese", "Italian", "Japanese"]
      .map((l) => `<option${(s.language || "English") === l ? " selected" : ""}>${l}</option>`).join("")}</select>`;
}

const LABELS = { story: "Story", author: "Author", audience: "For", bookType: "Kind of book", format: "Made as", trim: "Size", pages: "Pages",
  interior: "Inside print", paper: "Paper", finish: "Cover", artStyle: "Pictures", layout: "Words go", tone: "Feeling", extras: "Extras", mode: "Checking" };

function nameOf(stepId, value) {
  const step = STEPS.find((st) => st.id === stepId);
  if (Array.isArray(value)) return value.length ? value.map((v) => nameOf(stepId, v)).join(", ") : "None";
  return step?.options?.find((o) => o.value === value)?.name ?? value;
}

function summaryBody() {
  fillAll();
  const steps = activeSteps();
  const rows = Object.keys(LABELS).filter((k) => s[k] != null).map((k) => {
    const v = k === "story" ? `${String(s.story).trim().split(/\s+/).length} words` : k === "author" ? s.author : nameOf(k, s[k]);
    const at = steps.findIndex((st) => st.id === k || (k === "author" && st.id === "story"));
    return `<div class="row"><div><div class="k">${esc(LABELS[k])}</div><div class="v">${esc(v)}</div></div>
      ${at >= 0 ? `<button class="link" data-goto="${at}">Change</button>` : ""}</div>`;
  }).join("");
  const warns = STEPS.filter((st) => st.kind === "cards" && s[st.id] != null).flatMap((st) => optionWarnings(st, s[st.id], s));
  return `<div class="summary">
      <div class="mock">${bookMockup(s)}</div>
      <div><div class="rows">${rows}</div>
        ${warns.map((w) => `<div class="warn">⚠️ ${esc(w)}</div>`).join("")}
        <div class="info">The Kindle eBook is made too, for free.</div></div>
    </div>`;
}

function render() {
  if (finished) {
    $app.innerHTML = `<div class="done"><div class="big">📚</div><h1>All set!</h1>
      <p class="sub">Your choices are saved. Go back to Claude, and it will start writing your book.</p></div>`;
    return;
  }
  const step = current();
  if (step.kind === "cards" || step.kind === "multi") fillAll();
  const body = step.kind === "story" ? storyBody() : step.kind === "summary" ? summaryBody() : cardsBody(step);
  const last = step.kind === "summary";
  $app.innerHTML = `${header(step)}${body}
    <div class="nav">
      <button id="back" ${index === 0 ? 'style="visibility:hidden"' : ""}>← Back</button>
      <div class="right">
        ${step.kind === "cards" ? '<button id="auto">✨ Not sure? Pick for me</button>' : ""}
        <button class="primary" id="go">${last ? "Make my book 📖" : "Next →"}</button>
      </div>
    </div>`;
  bind(step);
}

// --- events -------------------------------------------------------------

function readAloud(step) {
  try {
    let text = `${step.title}. ${step.subtitle || ""}`;
    if (step.kind === "cards" || step.kind === "multi") {
      const opts = available(step, s);
      const list = kidMode && step.kind === "cards" ? [opts[spot]] : opts;
      text += " " + list.map((o) => `${o.name}. ${o.desc}`).join(" ");
    }
    speechSynthesis.cancel();
    speechSynthesis.speak(new SpeechSynthesisUtterance(text));
  } catch {}
}

function collectStory() {
  s.story = document.getElementById("story").value;
  s.author = document.getElementById("author").value.trim();
  s.coauthor = document.getElementById("coauthor").value.trim();
  s.language = document.getElementById("language").value;
}

function bind(step) {
  const on = (id, fn) => document.getElementById(id)?.addEventListener("click", fn);
  on("kid", () => { kidMode = !kidMode; store.set("kidMode", kidMode ? "1" : "0"); render(); });
  on("read", () => readAloud(step));
  on("back", () => { if (step.kind === "story") collectStory(); index--; spot = 0; compareOpen = false; render(); });
  on("compare", () => { compareOpen = !compareOpen; render(); });
  on("auto", () => { s[step.id] = recommended(step, s); spot = available(step, s).findIndex((o) => o.value === s[step.id]); render(); });
  on("prev", () => { const n = available(step, s).length; spot = (spot + n - 1) % n; s[step.id] = available(step, s)[spot].value; render(); });
  on("next-opt", () => { const n = available(step, s).length; spot = (spot + 1) % n; s[step.id] = available(step, s)[spot].value; render(); });

  document.querySelectorAll(".card").forEach((el) => el.addEventListener("click", () => {
    const v = JSON.parse(el.dataset.v);
    if (step.kind === "multi") {
      const set = new Set(s[step.id] || []);
      set.has(v) ? set.delete(v) : set.add(v);
      s[step.id] = (step.options || []).map((o) => o.value).filter((x) => set.has(x));
    } else {
      s[step.id] = v;
    }
    render();
  }));
  document.getElementById("ded")?.addEventListener("input", (e) => { s.dedicationText = e.target.value; });
  for (const id of ["story", "author"]) {
    document.getElementById(id)?.addEventListener("input", (e) => {
      if (!errors[id]) return;
      delete errors[id];
      e.target.nextElementSibling?.classList.contains("error") && e.target.nextElementSibling.remove();
    });
  }
  document.querySelectorAll("[data-goto]").forEach((el) => el.addEventListener("click", () => { index = Number(el.dataset.goto); render(); }));

  on("go", async () => {
    if (step.kind === "story") {
      collectStory();
      errors = {};
      if (s.story.trim().split(/\s+/).filter(Boolean).length < 5) errors.story = "Write at least one sentence about your story.";
      if (!s.author) errors.author = "Enter the name to print on the cover.";
      if (Object.keys(errors).length) return render();
    }
    if (step.kind === "summary") {
      const btn = document.getElementById("go");
      btn.textContent = "Saving…";
      if (await save(true)) { finished = true; render(); }
      else { btn.textContent = "Couldn't save. Try again"; }
      return;
    }
    index++;
    spot = 0;
    compareOpen = false;
    save();
    render();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

document.addEventListener("keydown", (e) => {
  if (!kidMode || finished || e.target.matches("input, textarea, select")) return;
  if (e.key === "ArrowLeft") document.getElementById("prev")?.click();
  if (e.key === "ArrowRight") document.getElementById("next-opt")?.click();
});

async function start() {
  STEPS = (await (await fetch("steps.json")).json()).steps;
  try {
    const r = await fetch("/api/file/book-settings.json");
    if (r.ok) s = await r.json();
  } catch {}
  try {
    const caps = await (await fetch("/api/capabilities")).json();
    s.imageService = caps.image_service ? "available" : "none";
  } catch {
    s.imageService = "none";
  }
  render();
}
start();
