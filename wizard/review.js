// Checkpoint 1 review: pick a title, read and fix every page, approve or ask for changes.
import { bookMockup } from "./art.js";

const $app = document.getElementById("app");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const TYPE_NAMES = { title: "Title page", copyright: "Copyright", dedication: "Dedication", story: "Story", "the-end": "The End",
  "about-author": "About the author", questions: "Questions", blank: "Blank" };
const EDITABLE = new Set(["dedication", "story", "the-end", "about-author", "questions"]);

let settings, manuscript, listing;
let chosen = 0;            // index into title_options, or -1 for own title
let ownTitle = "";
const edits = {};          // page or chapter number -> text
let notes = "";
let error = "";
let finished = false;

const getJSON = async (name) => (await fetch(`/api/file/${name}`)).json();
const isChapters = () => Array.isArray(manuscript.chapters) && manuscript.chapters.length > 0;

function titleChoice() {
  if (chosen === -1) return { title: ownTitle.trim(), subtitle: "" };
  const t = listing.title_options[chosen];
  return { title: t.title, subtitle: t.subtitle || "" };
}

function titlesHTML() {
  const cards = listing.title_options.map((t, i) => `
    <button class="card${chosen === i ? " sel" : ""}" data-title="${i}" aria-pressed="${chosen === i}">
      <div class="art">${bookMockup(settings, esc(t.title))}</div>
      <span class="badge${i === 0 ? "" : " hidden"}">⭐ Our favorite</span>
      <p class="nm">${esc(t.title)}</p>
      ${t.subtitle ? `<p class="ds">${esc(t.subtitle)}</p>` : ""}
      <p class="ds">${esc(t.why)}</p>
      <span class="tick">✓ Chosen</span>
    </button>`).join("");
  return `<h2>1. Pick a title</h2><p class="sub">Tap the one you like best, or write your own.</p>
    <div class="titles">${cards}</div>
    <div class="own"><input id="own" placeholder="Or type your own title" value="${esc(ownTitle)}"></div>`;
}

function pageHTML(p) {
  const text = edits[p.page] ?? p.text ?? "";
  const editable = EDITABLE.has(p.type);
  const side = p.page % 2 === 0 ? "left" : "right";
  return `<div class="page${editable ? "" : " quiet"}${edits[p.page] != null ? " edited" : ""}">
      <div class="meta"><span>Page ${p.page} · ${side}</span><span class="type">${esc(TYPE_NAMES[p.type] || p.type)}</span></div>
      ${editable ? `<textarea data-page="${p.page}" aria-label="Words on page ${p.page}">${esc(text)}</textarea>`
                 : `<p class="ds" style="margin:0">${p.type === "copyright" ? "Filled in automatically." : esc(text)}</p>`}
      ${p.scene ? `<div class="scene"><span aria-hidden="true">🖼️</span><span>${esc(p.scene)}</span></div>` : ""}
      <div class="meta">${p.page_turn ? '<span class="turn">↪ Page turn moment</span>' : "<span></span>"}
        ${editable && text ? `<button class="speak" data-say="${p.page}">🔊 Read</button>` : ""}</div>
    </div>`;
}

function chapterHTML(c) {
  const text = edits[c.number] ?? c.text ?? "";
  return `<div class="page wide${edits[c.number] != null ? " edited" : ""}">
      <div class="meta"><span>Chapter ${c.number}</span><span class="type">${esc(c.title)}</span></div>
      <textarea data-chapter="${c.number}" aria-label="Chapter ${c.number}">${esc(text)}</textarea>
      ${c.scene ? `<div class="scene"><span aria-hidden="true">🖼️</span><span>${esc(c.scene)}</span></div>` : ""}
    </div>`;
}

function render() {
  if (finished) {
    $app.innerHTML = `<div class="done"><div class="big">✅</div><h1>Thanks!</h1>
      <p class="sub">Your answers are saved. Go back to Claude to continue.</p></div>`;
    return;
  }
  const items = isChapters() ? manuscript.chapters : manuscript.pages;
  const storyPages = isChapters() ? manuscript.chapters.length : manuscript.pages.filter((p) => p.type === "story").length;
  $app.innerHTML = `
    <div class="top"><span class="count">Checkpoint 1 of 3</span></div>
    <div class="bar"><div style="width:33%"></div></div>
    <h1>Read your book</h1>
    <p class="sub">Pick a title, read every page, and fix any words right on the page.</p>
    <div class="stats">
      <div class="stat"><b>${manuscript.page_count}</b>pages</div>
      <div class="stat"><b>${storyPages}</b>${isChapters() ? "chapters" : "story pages"}</div>
      <div class="stat"><b>${manuscript.word_count}</b>words</div>
    </div>
    ${titlesHTML()}
    <h2>2. Read the ${isChapters() ? "chapters" : "pages"}</h2>
    <p class="sub">${esc(manuscript.reading_level || "")} The 🖼️ line says what the picture will show.</p>
    <div class="pages">${items.map(isChapters() ? chapterHTML : pageHTML).join("")}</div>
    ${manuscript.changes?.length ? `<h2>What we changed from your story</h2>
      <div class="info"><ul class="changes">${manuscript.changes.map((c) => `<li>${esc(c)}</li>`).join("")}</ul></div>` : ""}
    <h2>3. Anything else to change?</h2>
    <textarea id="notes" style="min-height:90px" placeholder="Make the owl funnier, and give Mia a red scarf">${esc(notes)}</textarea>
    ${error ? `<div class="error">${esc(error)}</div>` : ""}
    <div class="nav">
      <span></span>
      <div class="right">
        <button id="changes">Ask for changes</button>
        <button class="primary" id="approve">Looks good, keep going →</button>
      </div>
    </div>`;
  bind();
}

async function submit(approved) {
  const t = titleChoice();
  if (!t.title) { error = "Pick a title or type your own."; return render(); }
  if (!approved && !notes.trim() && !Object.keys(edits).length) { error = "Write what you'd like changed, or edit a page."; return render(); }
  const body = { checkpoint: 1, approved, chosen_title: t, notes: notes.trim(), _final: true,
    [isChapters() ? "chapter_edits" : "page_edits"]: edits };
  try {
    const r = await fetch("/api/save/review.json", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error();
    finished = true;
  } catch {
    error = "Couldn't save. Try again.";
  }
  render();
}

function bind() {
  document.querySelectorAll("[data-title]").forEach((el) => el.addEventListener("click", () => { chosen = Number(el.dataset.title); error = ""; render(); }));
  const own = document.getElementById("own");
  own.addEventListener("input", () => {
    ownTitle = own.value;
    const wasOwn = chosen === -1;
    chosen = ownTitle.trim() ? -1 : (wasOwn ? 0 : chosen);
    document.querySelectorAll("[data-title]").forEach((el) => {
      const on = Number(el.dataset.title) === chosen;
      el.classList.toggle("sel", on);
      el.setAttribute("aria-pressed", on);
    });
  });
  document.querySelectorAll("textarea[data-page], textarea[data-chapter]").forEach((el) => el.addEventListener("input", () => {
    const n = el.dataset.page ?? el.dataset.chapter;
    const items = isChapters() ? manuscript.chapters : manuscript.pages;
    const original = items.find((x) => String(x.page ?? x.number) === n)?.text ?? "";
    if (el.value === original) delete edits[n]; else edits[n] = el.value;
    el.closest(".page").classList.toggle("edited", edits[n] != null);
  }));
  document.getElementById("notes").addEventListener("input", (e) => { notes = e.target.value; if (error) { error = ""; document.querySelector(".error")?.remove(); } });
  document.querySelectorAll("[data-say]").forEach((el) => el.addEventListener("click", () => {
    const n = el.dataset.say;
    const text = edits[n] ?? manuscript.pages.find((p) => String(p.page) === n)?.text ?? "";
    try { speechSynthesis.cancel(); speechSynthesis.speak(new SpeechSynthesisUtterance(text)); } catch {}
  }));
  document.getElementById("approve").addEventListener("click", () => submit(true));
  document.getElementById("changes").addEventListener("click", () => submit(false));
}

async function start() {
  try {
    [settings, manuscript, listing] = await Promise.all(["book-settings.json", "manuscript.json", "listing.json"].map(getJSON));
  } catch {
    $app.innerHTML = `<h1>Nothing to review yet</h1><p class="sub">Go back to Claude; the book isn't written yet.</p>`;
    return;
  }
  render();
}
start();
