// Art studio: add photos of your own drawings for characters, the cover or any
// page, and choose how much to improve each one. Saves art-choices.json.
import { improveArt } from "./art.js";

const $app = document.getElementById("app");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const slug = (name) => String(name).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40) || "character";

const IMPROVE = {
  service: [
    { value: "keep", name: "Keep as is", desc: "We only clean up the photo. No AI." },
    { value: "light", name: "Light touch", desc: "Keep the drawing, neaten the lines and color it in." },
    { value: "full", name: "Full redraw", desc: "Redraw it in the book's style, same scene." },
    { value: "vector", name: "Simple shapes", desc: "Claude redraws it with clean flat shapes." },
  ],
  claude: [
    { value: "keep", name: "Keep as is", desc: "We only clean up the photo. No AI." },
    { value: "light", name: "Light touch", desc: "Claude colors it in under your own lines." },
    { value: "full", name: "Full redraw", desc: "Claude redraws it in the book's style." },
    { value: "vector", name: "Simple shapes", desc: "Claude redraws it with clean flat shapes." },
  ],
};
let improveOptions = IMPROVE.claude;

let settings, manuscript, analysis;
let choices = { uploads: {}, characters: {} };
const busy = {};
let error = "";
let finished = false;
let cacheBust = Date.now();

const getJSON = async (name) => { const r = await fetch(`/api/file/${name}`); return r.ok ? r.json() : null; };

function pictureSlots() {
  const out = [];
  if (manuscript.pages?.length) {
    for (const p of manuscript.pages) {
      const sideText = settings.layout === "side-by-side" && p.type === "story" && p.page % 2 === 0;
      if (["title", "story", "the-end"].includes(p.type) && !sideText) {
        out.push({ slot: `page-${String(p.page).padStart(2, "0")}`, label: `Page ${p.page}`, words: p.text, scene: p.scene });
      }
    }
  } else {
    for (const c of manuscript.chapters) out.push({ slot: `chapter-${String(c.number).padStart(2, "0")}`, label: `Chapter ${c.number}: ${c.title}`, words: "", scene: c.scene });
  }
  return out;
}

function uploadOf(slot) {
  return slot.startsWith("character-") ? choices.characters[slot.slice(10)] : choices.uploads[slot];
}

function slotCard({ slot, label, words, scene }, isCharacter = false) {
  const up = uploadOf(slot);
  const pick = up && !isCharacter ? `
      <p class="ask">How should we use it?</p>
      <div class="improve">${improveOptions.map((o) => `
        <button class="card${up.improve === o.value ? " sel" : ""}" data-slot="${slot}" data-improve="${o.value}" aria-pressed="${up.improve === o.value}">
          <div class="art">${improveArt(o.value)}</div>
          <p class="nm">${esc(o.name)}</p><p class="ds">${esc(o.desc)}</p>
        </button>`).join("")}</div>` : "";
  return `<div class="slot${up ? " has" : ""}">
      <div class="meta"><b style="color:var(--text)">${esc(label)}</b>${up ? `<button class="link" data-remove="${slot}">Remove</button>` : ""}</div>
      ${words ? `<p class="words">${esc(words)}</p>` : ""}
      ${scene ? `<p class="scene"><span aria-hidden="true">🖼️</span><span>${esc(scene)}</span></p>` : ""}
      ${up ? `<img class="thumb" src="/api/image/${esc(up.file)}?t=${cacheBust}" alt="Your drawing for ${esc(label)}">`
           : `<label class="add">${busy[slot] ? '<span class="busy">Uploading…</span>' : "📷 Add a drawing"}
                <input type="file" accept="image/*" data-file="${slot}"></label>`}
      ${pick}
    </div>`;
}

function render() {
  if (finished) {
    $app.innerHTML = `<div class="done"><div class="big">🎨</div><h1>Got it!</h1>
      <p class="sub">Go back to Claude. It will plan the pictures and show you the first ones soon.</p></div>`;
    return;
  }
  const chars = analysis?.characters || [];
  $app.innerHTML = `
    <div class="top"><span class="count">Checkpoint 2 of 3 · Your drawings</span></div>
    <div class="bar"><div style="width:50%"></div></div>
    <h1>Add your own drawings</h1>
    <p class="sub">Take a photo of each drawing from straight above, in daylight. Add as many or as few as you like. We'll make the rest.</p>
    ${chars.length ? `<h2>Characters</h2><p class="sub">A drawing of a character helps us draw them the same way on every page.</p>
      <div class="slots">${chars.map((c) => slotCard({ slot: `character-${slug(c.name)}`, label: c.name, words: "", scene: c.look }, true)).join("")}</div>` : ""}
    <h2>Cover</h2>
    <div class="slots">${slotCard({ slot: "cover", label: "Front cover", words: "", scene: "The picture on the front of the book" })}</div>
    <h2>Pages</h2>
    <div class="slots">${pictureSlots().map((s) => slotCard(s)).join("")}</div>
    ${error ? `<div class="error" style="margin-top:14px">${esc(error)}</div>` : ""}
    <div class="nav">
      <button id="none">No drawings, make all the pictures</button>
      <button class="primary" id="done">Done adding drawings →</button>
    </div>`;
  bind();
}

async function toJpeg(file) {
  // Re-encode in the browser: handles iPhone HEIC photos and keeps uploads small.
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, 3000 / Math.max(bmp.width, bmp.height));
  const c = document.createElement("canvas");
  c.width = Math.round(bmp.width * scale);
  c.height = Math.round(bmp.height * scale);
  c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
  return new Promise((ok) => c.toBlob(ok, "image/jpeg", 0.92));
}

async function upload(slot, file) {
  busy[slot] = true;
  error = "";
  render();
  try {
    const body = await toJpeg(file);
    const r = await fetch(`/api/upload/${slot}`, { method: "POST", body });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Upload failed");
    if (slot.startsWith("character-")) choices.characters[slot.slice(10)] = { file: j.file };
    else choices.uploads[slot] = { file: j.file, improve: null };
    cacheBust = Date.now();
  } catch (e) {
    error = `Couldn't add that picture: ${e.message}. Try a JPEG or PNG photo.`;
  }
  delete busy[slot];
  render();
}

async function save() {
  const missing = Object.entries(choices.uploads).filter(([, u]) => !u.improve).map(([s]) => s);
  if (missing.length) { error = `Choose how to use your drawing for: ${missing.join(", ")}.`; return render(); }
  const r = await fetch("/api/save/art-choices.json", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...choices, _final: true }) });
  if (r.ok) { finished = true; render(); } else { error = "Couldn't save. Try again."; render(); }
}

function bind() {
  document.querySelectorAll("[data-file]").forEach((el) => el.addEventListener("change", () => el.files[0] && upload(el.dataset.file, el.files[0])));
  document.querySelectorAll("[data-improve]").forEach((el) => el.addEventListener("click", () => {
    choices.uploads[el.dataset.slot].improve = el.dataset.improve;
    error = "";
    render();
  }));
  document.querySelectorAll("[data-remove]").forEach((el) => el.addEventListener("click", async () => {
    const slot = el.dataset.remove;
    await fetch(`/api/upload/${slot}`, { method: "DELETE" });
    if (slot.startsWith("character-")) delete choices.characters[slot.slice(10)]; else delete choices.uploads[slot];
    render();
  }));
  document.getElementById("done").addEventListener("click", save);
  document.getElementById("none").addEventListener("click", async () => {
    for (const slot of [...Object.keys(choices.uploads), ...Object.keys(choices.characters).map((c) => `character-${c}`)]) {
      await fetch(`/api/upload/${slot}`, { method: "DELETE" });
    }
    choices = { uploads: {}, characters: {} };
    save();
  });
}

async function start() {
  [settings, manuscript, analysis] = await Promise.all(["book-settings.json", "manuscript.json", "story-analysis.json"].map(getJSON));
  if (!settings || !manuscript) {
    $app.innerHTML = `<h1>Nothing here yet</h1><p class="sub">Go back to Claude; the words aren't written yet.</p>`;
    return;
  }
  try {
    improveOptions = (await (await fetch("/api/capabilities")).json()).image_service ? IMPROVE.service : IMPROVE.claude;
  } catch {}
  choices = (await getJSON("art-choices.json")) || choices;
  choices.uploads ||= {};
  choices.characters ||= {};
  render();
}
start();
