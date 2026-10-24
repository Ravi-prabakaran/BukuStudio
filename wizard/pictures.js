// Checkpoint 2: look at the characters and pictures, keep or redo each one,
// and for your own drawings compare the original with the improved version.
const $app = document.getElementById("app");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const SOURCE = { generated: "Made in the book's style", "upload-keep": "Your drawing, cleaned up", "upload-light": "Your drawing, light touch",
  "upload-full": "Your drawing, redrawn", vector: "Simple shapes by Claude" };

let plan, status, checks, manuscript;
const actions = {};      // slot -> {action, note}
const charActions = {};  // id -> {action, note}
let notes = "";
let error = "";
let finished = false;
const t = Date.now();

const getJSON = async (name) => { const r = await fetch(`/api/file/${name}`); return r.ok ? r.json() : null; };
const img = (path, alt) => `<img src="/api/image/${esc(path)}?t=${t}" alt="${esc(alt)}" data-zoom>`;
const slotsMade = () => Object.keys(status).filter((s) => plan.slots[s]).sort((a, b) => (a === "cover" ? -1 : b === "cover" ? 1 : a.localeCompare(b)));
const stage = () => (slotsMade().length < Object.keys(plan.slots).length ? "sample" : "all");

function words(slot) {
  const m = slot.match(/^page-(\d+)$/);
  if (!m || !manuscript.pages) return "";
  return manuscript.pages.find((p) => p.page === Number(m[1]))?.text || "";
}

function label(slot) {
  if (slot === "cover") return "Front cover";
  const [kind, n] = slot.split("-");
  return `${kind === "page" ? "Page" : "Chapter"} ${Number(n)}`;
}

function buttons(key, current, isUpload, isChar) {
  const opts = [["accept", "✓ Keep this"], ["redo", "↻ Try again"]];
  if (isUpload) opts.push(["original", "Use my original"]);
  return `<div class="actions">${opts.map(([a, l]) => `<button data-${isChar ? "char" : "slot"}="${key}" data-action="${a}" aria-pressed="${current === a}">${l}</button>`).join("")}</div>`;
}

function picCard(slot) {
  const st = status[slot];
  const a = actions[slot] || { action: "accept" };
  const chk = checks[slot];
  const isUpload = st.source?.startsWith("upload-") && st.original;
  const showOriginal = isUpload && st.source !== "upload-keep";
  return `<div class="pic${a.action === "redo" ? " redo" : ""}">
      <div class="meta"><b style="color:var(--text)">${esc(label(slot))}</b><span class="type">${esc(SOURCE[st.source] || st.source)}</span></div>
      <div class="imgs${showOriginal ? " two" : ""}">
        ${showOriginal ? `<figure>${img(st.original, "Your original drawing")}<figcaption>Your drawing</figcaption></figure>` : ""}
        <figure>${img(`art/preview/${slot}.jpg`, label(slot))}${showOriginal ? "<figcaption>Improved</figcaption>" : ""}</figure>
      </div>
      ${words(slot) ? `<p class="ds" style="margin:0">“${esc(words(slot))}”</p>` : ""}
      ${chk && !chk.ok ? `<div class="warn">🔍 Our checker noticed: ${esc((chk.problems || []).join(" "))}</div>` : ""}
      ${buttons(slot, a.action, isUpload, false)}
      ${a.action === "redo" ? `<textarea data-note="${slot}" placeholder="What should change? For example: make Mia smaller, add more stars">${esc(a.note || "")}</textarea>` : ""}
    </div>`;
}

function charCard(c) {
  const a = charActions[c.id] || { action: "accept" };
  return `<div class="pic${a.action === "redo" ? " redo" : ""}">
      <div class="meta"><b style="color:var(--text)">${esc(c.name)}</b></div>
      <div class="imgs"><figure>${img(`art/refs/${c.id}.jpg`, c.name)}</figure></div>
      <p class="ds" style="margin:0">${esc(c.prompt)}</p>
      ${buttons(c.id, a.action, false, true)}
      ${a.action === "redo" ? `<textarea data-cnote="${c.id}" placeholder="What should change? For example: a red scarf instead of green">${esc(a.note || "")}</textarea>` : ""}
    </div>`;
}

function render() {
  if (finished) {
    $app.innerHTML = `<div class="done"><div class="big">🖼️</div><h1>Thanks!</h1>
      <p class="sub">Go back to Claude. It will ${Object.values(actions).some((a) => a.action !== "accept") || Object.values(charActions).some((a) => a.action === "redo") ? "fix the pictures you marked" : stage() === "sample" ? "make the rest of the pictures" : "make the print files"}.</p></div>`;
    return;
  }
  const s = stage();
  const made = slotsMade();
  const redoCount = Object.values(actions).filter((a) => a.action !== "accept").length + Object.values(charActions).filter((a) => a.action === "redo").length;
  $app.innerHTML = `
    <div class="top"><span class="count">Checkpoint 2 of 3 · Pictures</span></div>
    <div class="bar"><div style="width:${s === "sample" ? 55 : 66}%"></div></div>
    <h1>${s === "sample" ? "Do you like the style?" : "Check every picture"}</h1>
    <p class="sub">${s === "sample" ? `Here are the characters and the first ${made.length} pictures. Once you like them, we'll make the rest the same way.`
      : "Keep the ones you love and ask for another try on any you don't. Tap a picture to see it bigger."}</p>
    <p class="hint">${esc(plan.style.summary || "")}</p>
    ${s === "sample" && plan.characters.length ? `<h2>Characters</h2><div class="chars">${plan.characters.map(charCard).join("")}</div>` : ""}
    <h2>Pictures</h2>
    <div class="pics">${made.map(picCard).join("")}</div>
    <h2>Anything else?</h2>
    <textarea id="notes" style="min-height:70px" placeholder="For example: make all the pictures a bit brighter">${esc(notes)}</textarea>
    ${error ? `<div class="error">${esc(error)}</div>` : ""}
    <div class="nav"><span class="hint">${redoCount ? `${redoCount} to redo` : "Everything kept"}</span>
      <button class="primary" id="done">${redoCount ? "Fix the ones I marked →" : s === "sample" ? "Looks good, make the rest →" : "All done →"}</button></div>`;
  bind();
}

async function submit() {
  const missing = [...Object.entries(actions), ...Object.entries(charActions)].filter(([, a]) => a.action === "redo" && !(a.note || "").trim());
  if (missing.length) { error = "Tell us what to change for each picture you want redone."; return render(); }
  const body = { checkpoint: 2, stage: stage(), approved: !Object.values(actions).some((a) => a.action !== "accept") && !Object.values(charActions).some((a) => a.action === "redo"),
    characters: Object.fromEntries(plan.characters.map((c) => [c.id, charActions[c.id] || { action: "accept" }])),
    slots: Object.fromEntries(slotsMade().map((s) => [s, actions[s] || { action: "accept" }])), notes: notes.trim(), _final: true };
  const r = await fetch("/api/save/picture-review.json", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (r.ok) { finished = true; } else { error = "Couldn't save. Try again."; }
  render();
}

function bind() {
  document.querySelectorAll("[data-slot]").forEach((el) => el.addEventListener("click", () => {
    actions[el.dataset.slot] = { ...(actions[el.dataset.slot] || {}), action: el.dataset.action };
    error = "";
    render();
  }));
  document.querySelectorAll("[data-char]").forEach((el) => el.addEventListener("click", () => {
    charActions[el.dataset.char] = { ...(charActions[el.dataset.char] || {}), action: el.dataset.action };
    error = "";
    render();
  }));
  document.querySelectorAll("[data-note]").forEach((el) => el.addEventListener("input", () => { actions[el.dataset.note].note = el.value; }));
  document.querySelectorAll("[data-cnote]").forEach((el) => el.addEventListener("input", () => { charActions[el.dataset.cnote].note = el.value; }));
  document.getElementById("notes").addEventListener("input", (e) => { notes = e.target.value; });
  document.getElementById("done").addEventListener("click", submit);
  document.querySelectorAll("[data-zoom]").forEach((el) => el.addEventListener("click", () => {
    const z = document.createElement("div");
    z.className = "zoom";
    z.innerHTML = `<img src="${el.src}" alt="${el.alt}">`;
    z.addEventListener("click", () => z.remove());
    document.body.appendChild(z);
  }));
}

async function start() {
  [plan, status, checks, manuscript] = await Promise.all(["art-plan.json", "art/status.json", "art/checks.json", "manuscript.json"].map(getJSON));
  if (!plan || !status) {
    $app.innerHTML = `<h1>No pictures yet</h1><p class="sub">Go back to Claude; the pictures aren't made yet.</p>`;
    return;
  }
  checks ||= {};
  for (const [slot, c] of Object.entries(checks)) if (!c.ok && status[slot]) actions[slot] = { action: "accept" };
  render();
}
start();
