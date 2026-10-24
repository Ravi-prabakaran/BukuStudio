// Picture-card illustrations for the wizard, drawn as inline SVG so they are free,
// sharp at any size and consistent. art(stepId, option, settings) returns markup.

const C = {
  ink: "#2C2C2A", gray: "#888780", line: "#D3D1C7", paper: "#FFFFFF", cream: "#F6EBD3",
  teal: "#5DCAA5", tealDark: "#0F6E56", tealLight: "#9FE1CB",
  purple: "#534AB7", purpleDark: "#26215C", purpleLight: "#CECBF6",
  sun: "#FAC775", coral: "#F0997B", coralDark: "#D85A30", sky: "#B5D4F4", blue: "#378ADD", grass: "#97C459", grassDark: "#639922",
  skin: "#F5C4B3", pink: "#ED93B1",
};

const svg = (body, vb = "0 0 140 120") =>
  `<svg viewBox="${vb}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" aria-hidden="true">${body}</svg>`;
const shadow = (cx, cy, rx) => `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="3.5" fill="${C.gray}" opacity=".22"/>`;
const lines = (x, y, w, n, gap = 7, color = C.line) =>
  Array.from({ length: n }, (_, i) => `<rect x="${x}" y="${y + i * gap}" width="${i === n - 1 ? w * 0.6 : w}" height="3" rx="1.5" fill="${color}"/>`).join("");

// A small scene (sun, hills, fox) reused for pages and style samples.
function scene(x, y, w, h, pal = {}) {
  const p = { sky: C.sky, sun: C.sun, hill: C.grass, hill2: C.grassDark, fox: C.coral, ...pal };
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${p.sky}"/>
    <circle cx="${x + w * 0.78}" cy="${y + h * 0.28}" r="${h * 0.14}" fill="${p.sun}"/>
    <path d="M${x} ${y + h * 0.75} Q${x + w * 0.3} ${y + h * 0.5} ${x + w * 0.6} ${y + h * 0.72} T${x + w} ${y + h * 0.66} V${y + h} H${x} Z" fill="${p.hill}"/>
    <path d="M${x} ${y + h * 0.88} Q${x + w * 0.5} ${y + h * 0.74} ${x + w} ${y + h * 0.9} V${y + h} H${x} Z" fill="${p.hill2}"/>
    <circle cx="${x + w * 0.32}" cy="${y + h * 0.62}" r="${h * 0.1}" fill="${p.fox}"/>
    <path d="M${x + w * 0.27} ${y + h * 0.56} l${h * 0.03} -${h * 0.1} l${h * 0.05} ${h * 0.07} Z M${x + w * 0.37} ${y + h * 0.56} l-${h * 0.03} -${h * 0.1} l-${h * 0.05} ${h * 0.07} Z" fill="${p.fox}"/>`;
}

function person(cx, base, scale, shirt) {
  const s = scale;
  return `<circle cx="${cx}" cy="${base - 78 * s}" r="${11 * s}" fill="${C.skin}"/>
    <rect x="${cx - 12 * s}" y="${base - 66 * s}" width="${24 * s}" height="${36 * s}" rx="${9 * s}" fill="${shirt}"/>
    <rect x="${cx - 10 * s}" y="${base - 34 * s}" width="${8 * s}" height="${34 * s}" rx="${4 * s}" fill="${C.ink}" opacity=".75"/>
    <rect x="${cx + 2 * s}" y="${base - 34 * s}" width="${8 * s}" height="${34 * s}" rx="${4 * s}" fill="${C.ink}" opacity=".75"/>
    <rect x="${cx + 6 * s}" y="${base - 56 * s}" width="${18 * s}" height="${14 * s}" rx="2" fill="${C.purple}"/>`;
}

const books = {
  paperback: () => svg(`${shadow(70, 112, 42)}
    <path d="M44 16 L102 12 L102 106 L44 110 Z" fill="#F1EFE8" stroke="#B4B2A9"/>
    <path d="M36 12 Q72 6 98 8 L98 102 Q72 100 36 106 Z" fill="${C.teal}" stroke="${C.tealDark}" stroke-width="1.5"/>
    <rect x="36" y="12" width="4" height="94" fill="#1D9E75"/>
    <circle cx="68" cy="42" r="13" fill="${C.sun}"/>
    <path d="M46 88 Q62 66 74 80 T96 76 L96 96 L46 98 Z" fill="${C.tealLight}"/>`),
  hardcover: () => svg(`${shadow(70, 112, 44)}
    <rect x="44" y="14" width="64" height="96" fill="#fff" stroke="${C.line}"/>
    <rect x="30" y="8" width="74" height="104" rx="3" fill="${C.purple}" stroke="${C.purpleDark}" stroke-width="2"/>
    <rect x="30" y="8" width="11" height="104" fill="#3C3489"/>
    <rect x="49" y="22" width="44" height="58" rx="2" fill="#EEEDFE"/>
    <circle cx="71" cy="42" r="10" fill="${C.coral}"/>
    <rect x="51" y="90" width="40" height="5" rx="2" fill="${C.purpleLight}"/>`),
  ebook: () => svg(`${shadow(70, 114, 38)}
    <rect x="33" y="6" width="74" height="106" rx="10" fill="${C.ink}"/>
    ${scene(39, 14, 62, 88, { sky: "#E6F1FB", hill: "#85B7EB", hill2: C.blue })}
    <circle cx="70" cy="107" r="2" fill="#5F5E5A"/>`),
};

function pageWith(kind) {
  const page = (inner) => svg(`${shadow(70, 114, 34)}<rect x="38" y="6" width="64" height="104" rx="3" fill="${C.paper}" stroke="${C.line}"/>${inner}`);
  if (kind === "picture") return page(`${scene(44, 12, 52, 64)}${lines(48, 86, 44, 2)}`);
  if (kind === "early") return page(`${scene(44, 12, 52, 44)}${lines(48, 64, 44, 5)}`);
  if (kind === "chapter") return page(`<rect x="48" y="14" width="30" height="4" rx="2" fill="${C.purple}"/>${scene(48, 24, 44, 26)}${lines(48, 58, 44, 7)}`);
  return page(`<rect x="48" y="14" width="30" height="4" rx="2" fill="${C.purple}"/>${lines(48, 26, 44, 11)}`);
}

function trimArt(opt) {
  const k = 8.2, w = opt.w * k, h = opt.h * k, base = 108, x = 18;
  const hand = `<g transform="translate(${x + w + 10} ${base - 46})" fill="${C.skin}" stroke="#D9A08A" stroke-width="1">
      <rect x="0" y="20" width="24" height="26" rx="8"/>
      <rect x="1" y="2" width="5" height="22" rx="2.5"/><rect x="7" y="0" width="5" height="24" rx="2.5"/>
      <rect x="13" y="1" width="5" height="23" rx="2.5"/><rect x="19" y="5" width="5" height="19" rx="2.5"/>
      <rect x="-6" y="24" width="6" height="14" rx="3" transform="rotate(-25 -3 31)"/></g>`;
  return svg(`${shadow(x + w / 2 + 14, base + 3, w / 2 + 16)}
    <rect x="${x}" y="${base - h}" width="${w}" height="${h}" rx="2" fill="${C.teal}" stroke="${C.tealDark}" stroke-width="1.5"/>
    <rect x="${x + w * 0.15}" y="${base - h * 0.85}" width="${w * 0.7}" height="${h * 0.45}" rx="2" fill="${C.tealLight}"/>
    <rect x="${x + w * 0.2}" y="${base - h * 0.28}" width="${w * 0.6}" height="3.5" rx="1.5" fill="${C.tealDark}" opacity=".6"/>
    ${hand}`);
}

function pagesArt(opt) {
  if (opt.value === "auto") {
    return svg(`${shadow(70, 112, 40)}
      <rect x="40" y="22" width="56" height="84" rx="2" fill="${C.paper}" stroke="${C.line}"/>
      <rect x="35" y="17" width="56" height="84" rx="2" fill="${C.paper}" stroke="${C.line}"/>
      <rect x="30" y="12" width="56" height="84" rx="2" fill="${C.paper}" stroke="${C.line}"/>
      ${lines(38, 24, 40, 6)}
      <circle cx="96" cy="34" r="14" fill="${C.sun}"/><text x="96" y="40" text-anchor="middle" font-size="17" font-weight="600" fill="#854F0B">?</text>`);
  }
  const t = 4 + (opt.value - 24) * 0.35;
  return svg(`${shadow(70 + t / 2, 112, 38 + t)}
    <path d="M${40} ${16} l${t} -${t * 0.6} h58 l-${t} ${t * 0.6} Z" fill="#F1EFE8" stroke="#B4B2A9"/>
    <path d="M${98} ${16} l${t} -${t * 0.6} v92 l-${t} ${t * 0.6} Z" fill="#fff" stroke="#B4B2A9"/>
    ${Array.from({ length: Math.round(t / 2.5) }, (_, i) => `<path d="M${99 + i * 2.5} ${16 - i * 1.5} v92" stroke="${C.line}" stroke-width=".6"/>`).join("")}
    <rect x="40" y="16" width="58" height="92" rx="2" fill="${C.coral}" stroke="${C.coralDark}" stroke-width="1.5"/>
    <rect x="48" y="26" width="42" height="40" rx="2" fill="#FAECE7"/>
    <text x="69" y="92" text-anchor="middle" font-size="15" font-weight="600" fill="#712B13">${opt.value}</text>`);
}

function interiorArt(opt) {
  const pal = {
    "premium-color": {},
    "standard-color": { sky: "#CFE0EF", sun: "#F2D49C", hill: "#B5C995", hill2: "#8FA56B", fox: "#E6B5A0" },
    bw: { sky: "#E8E8E6", sun: "#C9C8C2", hill: "#B4B2A9", hill2: "#888780", fox: "#9E9D97" },
  }[opt.value];
  return svg(`${shadow(70, 114, 34)}<rect x="38" y="6" width="64" height="104" rx="3" fill="#fff" stroke="${C.line}"/>
    ${scene(44, 12, 52, 64, pal)}${lines(48, 86, 44, 2, 7, opt.value === "bw" ? "#B4B2A9" : C.line)}`);
}

function paperArt(opt) {
  const fill = opt.value === "cream" ? C.cream : C.paper;
  return svg(`${shadow(70, 112, 46)}
    <path d="M70 18 Q50 10 26 14 V104 Q50 100 70 108 Z" fill="${fill}" stroke="${C.line}"/>
    <path d="M70 18 Q90 10 114 14 V104 Q90 100 70 108 Z" fill="${fill}" stroke="${C.line}"/>
    ${lines(34, 28, 28, 8, 8, "#C9C7BD")}${lines(78, 28, 28, 8, 8, "#C9C7BD")}`);
}

function finishArt(opt) {
  const shine = opt.value === "glossy"
    ? `<path d="M44 10 L64 10 L40 60 L30 60 Z" fill="#fff" opacity=".55"/><path d="M70 10 L76 10 L46 74 L40 74 Z" fill="#fff" opacity=".35"/>`
    : Array.from({ length: 40 }, (_, i) => `<circle cx="${34 + (i * 37) % 66}" cy="${14 + (i * 23) % 92}" r=".8" fill="#fff" opacity=".25"/>`).join("");
  return svg(`${shadow(70, 112, 40)}
    <rect x="30" y="8" width="76" height="102" rx="3" fill="${C.purple}"/>
    <rect x="44" y="24" width="48" height="50" rx="2" fill="#EEEDFE" opacity=".9"/>
    <circle cx="68" cy="46" r="11" fill="${C.coral}"/>
    ${shine}`);
}

function styleArt(opt) {
  const id = "st-" + opt.value;
  const x = 14, y = 10, w = 112, h = 100;
  const frame = (inner, defs = "") => svg(`<defs>${defs}<clipPath id="${id}-c"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="6"/></clipPath></defs>
    <g clip-path="url(#${id}-c)">${inner}</g>`);
  switch (opt.value) {
    case "watercolor":
      return frame(`<g filter="url(#${id}-b)" opacity=".85">${scene(x, y, w, h)}</g>
        <circle cx="${x + w * 0.78}" cy="${y + h * 0.28}" r="18" fill="${C.sun}" opacity=".5" filter="url(#${id}-b)"/>`,
        `<filter id="${id}-b"><feGaussianBlur stdDeviation="1.6"/></filter>`);
    case "cartoon":
      return frame(`<g stroke="${C.ink}" stroke-width="2.5" stroke-linejoin="round">${scene(x, y, w, h, { sky: "#85B7EB", hill: "#7DC940", hill2: "#4E8A1A", fox: "#FF7A33", sun: "#FFC933" })}</g>
        <circle cx="${x + w * 0.29}" cy="${y + h * 0.6}" r="2" fill="${C.ink}"/><circle cx="${x + w * 0.35}" cy="${y + h * 0.6}" r="2" fill="${C.ink}"/>`);
    case "crayon":
      return frame(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#fff"/><g filter="url(#${id}-r)" stroke-width="3" stroke-linecap="round">
        <path d="M${x + 4} ${y + 72} Q${x + 34} ${y + 50} ${x + 68} ${y + 70} T${x + w - 4} ${y + 64}" stroke="${C.grassDark}" fill="none"/>
        ${Array.from({ length: 14 }, (_, i) => `<path d="M${x + 6 + i * 8} ${y + 98} L${x + 12 + i * 8} ${y + 72}" stroke="${C.grass}"/>`).join("")}
        <circle cx="${x + w * 0.78}" cy="${y + 28}" r="12" stroke="#EF9F27" fill="none"/>
        ${Array.from({ length: 8 }, (_, i) => { const a = i * Math.PI / 4; return `<path d="M${x + w * 0.78 + Math.cos(a) * 16} ${y + 28 + Math.sin(a) * 16} L${x + w * 0.78 + Math.cos(a) * 22} ${y + 28 + Math.sin(a) * 22}" stroke="#EF9F27"/>`; }).join("")}
        <circle cx="${x + w * 0.32}" cy="${y + 62}" r="9" stroke="${C.coralDark}" fill="none"/>
        <path d="M${x + 28} ${y + 56} l3 -10 l5 7 M${x + 44} ${y + 56} l-3 -10 l-5 7" stroke="${C.coralDark}" fill="none"/></g>`,
        `<filter id="${id}-r"><feTurbulence baseFrequency=".9" numOctaves="2" seed="3"/><feDisplacementMap in="SourceGraphic" scale="3"/></filter>`);
    case "3d":
      return frame(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="url(#${id}-sky)"/>
        <circle cx="${x + w * 0.78}" cy="${y + 28}" r="14" fill="url(#${id}-sun)"/>
        <ellipse cx="${x + w / 2}" cy="${y + h + 20}" rx="${w * 0.8}" ry="${h * 0.45}" fill="url(#${id}-hill)"/>
        <ellipse cx="${x + w * 0.34}" cy="${y + 80}" rx="14" ry="3" fill="#000" opacity=".18"/>
        <circle cx="${x + w * 0.34}" cy="${y + 64}" r="14" fill="url(#${id}-fox)"/>
        <circle cx="${x + w * 0.3}" cy="${y + 62}" r="2.4" fill="${C.ink}"/><circle cx="${x + w * 0.38}" cy="${y + 62}" r="2.4" fill="${C.ink}"/>
        <circle cx="${x + w * 0.31}" cy="${y + 61}" r=".8" fill="#fff"/><circle cx="${x + w * 0.39}" cy="${y + 61}" r=".8" fill="#fff"/>`,
        `<linearGradient id="${id}-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#85B7EB"/><stop offset="1" stop-color="#E6F1FB"/></linearGradient>
         <radialGradient id="${id}-sun" cx=".35" cy=".35"><stop offset="0" stop-color="#FFF4D6"/><stop offset="1" stop-color="#EF9F27"/></radialGradient>
         <radialGradient id="${id}-hill" cx=".5" cy=".2"><stop offset="0" stop-color="#B8E07A"/><stop offset="1" stop-color="#3B6D11"/></radialGradient>
         <radialGradient id="${id}-fox" cx=".35" cy=".3"><stop offset="0" stop-color="#FFD0B8"/><stop offset=".5" stop-color="#F0784A"/><stop offset="1" stop-color="#993C1D"/></radialGradient>`);
    case "lineart":
      return frame(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#fff"/>
        <g fill="none" stroke="${C.ink}" stroke-width="1.6" stroke-linejoin="round">${scene(x, y, w, h, { sky: "none", sun: "none", hill: "none", hill2: "none", fox: "none" })}</g>`);
    case "coloredpencil":
      return frame(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#FDFCF8"/>
        <g opacity=".9">${scene(x, y, w, h, { sky: `url(#${id}-hs)`, sun: `url(#${id}-hy)`, hill: `url(#${id}-hg)`, hill2: `url(#${id}-hd)`, fox: `url(#${id}-ho)` })}</g>
        <g fill="none" stroke="#5F5E5A" stroke-width=".8" opacity=".6">${scene(x, y, w, h, { sky: "none", sun: "none", hill: "none", hill2: "none", fox: "none" })}</g>`,
        ["hs:#85B7EB", "hy:#EF9F27", "hg:#97C459", "hd:#639922", "ho:#D85A30"].map((p) => {
          const [k, c] = p.split(":");
          return `<pattern id="${id}-${k}" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><rect width="4" height="4" fill="${c}" opacity=".18"/><line x1="0" y1="0" x2="0" y2="4" stroke="${c}" stroke-width="1.6"/></pattern>`;
        }).join(""));
    default:
      return frame(scene(x, y, w, h));
  }
}

function layoutArt(opt) {
  const page = (x, inner) => `<rect x="${x}" y="10" width="56" height="96" rx="2" fill="#fff" stroke="${C.line}"/>${inner}`;
  if (opt.value === "fullbleed-box") return svg(`${shadow(70, 112, 30)}<rect x="42" y="10" width="56" height="96" rx="2" fill="#fff" stroke="${C.line}"/>${scene(42, 10, 56, 96)}
    <rect x="48" y="78" width="44" height="22" rx="5" fill="#fff" opacity=".92"/>${lines(53, 83, 34, 2)}`);
  if (opt.value === "text-below") return svg(`${shadow(70, 112, 30)}${page(42, scene(46, 14, 48, 54) + lines(48, 76, 44, 3))}`);
  if (opt.value === "side-by-side") return svg(`${shadow(70, 112, 58)}${page(14, lines(22, 40, 40, 5))}${page(70, scene(70, 10, 56, 96))}
    <path d="M70 10 V106" stroke="${C.gray}" stroke-width="1" opacity=".5"/>`);
  return svg(`${shadow(70, 112, 30)}${page(42, `<rect x="50" y="16" width="26" height="4" rx="2" fill="${C.purple}"/>${scene(50, 26, 40, 26)}${lines(50, 60, 40, 6)}`)}`);
}

function face(mouth, eyes, extra = "", color = C.sun) {
  return svg(`<circle cx="70" cy="60" r="38" fill="${color}"/>${eyes}${mouth}${extra}`);
}

const toneArt = {
  auto: () => svg(`${shadow(64, 108, 36)}<rect x="30" y="26" width="62" height="78" rx="3" fill="#fff" stroke="${C.line}"/>${lines(38, 38, 46, 8)}
    <circle cx="92" cy="52" r="18" fill="none" stroke="${C.purple}" stroke-width="5"/><path d="M104 64 L118 80" stroke="${C.purple}" stroke-width="7" stroke-linecap="round"/>`),
  funny: () => face(`<path d="M50 66 Q70 92 90 66 Z" fill="#712B13"/><path d="M58 76 Q70 84 82 76" fill="${C.coral}"/>`,
    `<path d="M50 50 Q56 42 62 50 M78 50 Q84 42 90 50" stroke="#412402" stroke-width="3.5" fill="none" stroke-linecap="round"/>`),
  cozy: () => face(`<path d="M56 68 Q70 80 84 68" stroke="#412402" stroke-width="3.5" fill="none" stroke-linecap="round"/>`,
    `<circle cx="56" cy="52" r="4" fill="#412402"/><circle cx="84" cy="52" r="4" fill="#412402"/>`,
    `<circle cx="48" cy="64" r="6" fill="${C.pink}" opacity=".6"/><circle cx="92" cy="64" r="6" fill="${C.pink}" opacity=".6"/>
     <path d="M104 24 c-6 -8 -18 -2 -12 8 l12 12 l12 -12 c6 -10 -6 -16 -12 -8 Z" fill="${C.coralDark}"/>`),
  adventurous: () => face(`<path d="M58 72 Q70 78 82 70" stroke="#412402" stroke-width="3.5" fill="none" stroke-linecap="round"/>`,
    `<circle cx="56" cy="54" r="4" fill="#412402"/><circle cx="84" cy="54" r="4" fill="#412402"/>
     <path d="M48 42 L62 46 M92 42 L78 46" stroke="#412402" stroke-width="3.5" stroke-linecap="round"/>`,
    `<path d="M108 14 V50" stroke="${C.ink}" stroke-width="2.5"/><path d="M108 14 L126 22 L108 30 Z" fill="${C.coralDark}"/>`),
  sleepy: () => face(`<ellipse cx="70" cy="74" rx="6" ry="4" fill="#412402"/>`,
    `<path d="M48 54 Q56 60 64 54 M76 54 Q84 60 92 54" stroke="#412402" stroke-width="3.5" fill="none" stroke-linecap="round"/>`,
    `<text x="104" y="34" font-size="16" font-weight="600" fill="${C.purple}">z</text><text x="114" y="22" font-size="12" font-weight="600" fill="${C.purple}">z</text>`,
    C.purpleLight),
};

const extrasArt = {
  dedication: () => svg(`${shadow(70, 112, 30)}<rect x="42" y="10" width="56" height="96" rx="2" fill="#fff" stroke="${C.line}"/>
    <path d="M70 52 c-8 -12 -24 -4 -16 10 l16 16 l16 -16 c8 -14 -8 -22 -16 -10 Z" fill="${C.coral}"/>${lines(52, 86, 36, 2)}`),
  "the-end": () => svg(`${shadow(70, 112, 30)}<rect x="42" y="10" width="56" height="96" rx="2" fill="#fff" stroke="${C.line}"/>
    <text x="70" y="62" text-anchor="middle" font-size="13" font-style="italic" font-family="Georgia, serif" fill="${C.ink}">The End</text>
    <path d="M56 72 Q70 78 84 72" stroke="${C.coral}" stroke-width="2" fill="none"/>`),
  "about-author": () => svg(`${shadow(70, 112, 30)}<rect x="42" y="10" width="56" height="96" rx="2" fill="#fff" stroke="${C.line}"/>
    <circle cx="70" cy="38" r="14" fill="${C.purpleLight}"/><circle cx="70" cy="34" r="6" fill="${C.skin}"/><path d="M60 48 Q70 38 80 48" fill="${C.purple}"/>${lines(50, 62, 40, 5)}`),
  questions: () => svg(`<path d="M24 20 H116 a8 8 0 0 1 8 8 V76 a8 8 0 0 1 -8 8 H60 L42 102 V84 H24 a8 8 0 0 1 -8 -8 V28 a8 8 0 0 1 8 -8 Z" fill="${C.sky}"/>
    <text x="70" y="66" text-anchor="middle" font-size="36" font-weight="600" fill="#0C447C">?</text>`),
};

const modeArt = {
  checkpoints: () => svg(`<path d="M18 92 Q50 30 70 70 T122 30" stroke="${C.line}" stroke-width="4" fill="none" stroke-dasharray="2 6" stroke-linecap="round"/>
    ${[[30, 74], [70, 68], [112, 36]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="13" fill="${C.teal}"/><path d="M${x - 6} ${y} l4 5 l8 -9" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>`).join("")}`),
  auto: () => svg(`${shadow(64, 108, 30)}<rect x="40" y="56" width="50" height="48" rx="4" fill="${C.coral}"/><rect x="36" y="46" width="58" height="14" rx="3" fill="${C.coralDark}"/>
    <rect x="61" y="46" width="8" height="58" fill="${C.sun}"/><path d="M65 46 c-12 -16 -26 -4 -12 0 Z M65 46 c12 -16 26 -4 12 0 Z" fill="${C.sun}"/>
    ${[[104, 30, 7], [116, 54, 5], [24, 34, 5]].map(([x, y, r]) => `<path d="M${x} ${y - r} Q${x} ${y} ${x + r} ${y} Q${x} ${y} ${x} ${y + r} Q${x} ${y} ${x - r} ${y} Q${x} ${y} ${x} ${y - r} Z" fill="${C.purple}"/>`).join("")}`),
};

// The same child's sketch (a fox under a sun) shown four ways, for choosing how to improve a drawing.
export function improveArt(value) {
  const sketch = (stroke, sw, fills) => `
    <circle cx="104" cy="30" r="13" fill="${fills ? fills.sun : "none"}" stroke="${stroke}" stroke-width="${sw}"/>
    ${[0, 1, 2, 3, 4, 5, 6, 7].map((i) => { const a = (i * Math.PI) / 4; return `<path d="M${104 + Math.cos(a) * 17} ${30 + Math.sin(a) * 17} L${104 + Math.cos(a) * 23} ${30 + Math.sin(a) * 23}" stroke="${fills ? fills.sunLine : stroke}" stroke-width="${sw}" stroke-linecap="round"/>`; }).join("")}
    <path d="M12 98 Q50 88 80 96 T130 92" fill="none" stroke="${fills ? fills.groundLine : stroke}" stroke-width="${sw}"/>
    ${fills ? `<path d="M10 97 Q50 87 80 95 T132 91 V112 H10 Z" fill="${fills.ground}"/>` : ""}
    <path d="M44 66 L41 44 L54 56 M70 66 L73 44 L60 56" fill="${fills ? fills.fox : "none"}" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round"/>
    <circle cx="57" cy="68" r="16" fill="${fills ? fills.fox : "none"}" stroke="${stroke}" stroke-width="${sw}"/>
    <path d="M48 82 L44 98 L70 98 L66 82" fill="${fills ? fills.fox : "none"}" stroke="${stroke}" stroke-width="${sw}" stroke-linejoin="round"/>
    <path d="M70 94 Q88 92 92 80 Q84 88 70 90" fill="${fills ? fills.tail : "none"}" stroke="${stroke}" stroke-width="${sw}"/>
    <circle cx="51" cy="66" r="2" fill="${C.ink}"/><circle cx="63" cy="66" r="2" fill="${C.ink}"/>
    <path d="M53 73 Q57 76 61 73" fill="none" stroke="${C.ink}" stroke-width="1.5"/>`;
  const paper = (inner, bg = "#fff") => svg(`<rect x="8" y="8" width="124" height="104" rx="4" fill="${bg}" stroke="${C.line}"/>${inner}`);
  const colors = { sun: C.sun, sunLine: "#EF9F27", ground: C.grass, groundLine: C.grassDark, fox: C.coral, tail: "#F1EFE8" };
  if (value === "keep") return paper(`<g opacity=".85">${sketch("#5F5E5A", 1.6)}</g>`);
  if (value === "light") return paper(sketch("#444441", 1.6, { ...colors, fox: "#F5C4B3", sun: "#FAEEDA", ground: "#C0DD97" }));
  if (value === "full") return paper(`<defs><filter id="imp-soft"><feGaussianBlur stdDeviation=".6"/></filter></defs>
    <rect x="8" y="8" width="124" height="104" rx="4" fill="${C.sky}"/><g filter="url(#imp-soft)">${sketch("none", 0, colors)}</g>`, C.sky);
  return paper(`<rect x="8" y="8" width="124" height="104" rx="4" fill="#E6F1FB"/>${sketch(C.ink, 2.6, colors)}`, "#E6F1FB");
}

export function drawingsArt(value) {
  if (value === "none") {
    return svg(`${shadow(70, 112, 40)}<rect x="30" y="14" width="80" height="94" rx="3" fill="#fff" stroke="${C.line}"/>${scene(36, 20, 68, 60)}${lines(40, 88, 60, 2)}
      ${[[112, 22, 7], [22, 40, 5], [116, 70, 5]].map(([x, y, r]) => `<path d="M${x} ${y - r} Q${x} ${y} ${x + r} ${y} Q${x} ${y} ${x} ${y + r} Q${x} ${y} ${x - r} ${y} Q${x} ${y} ${x} ${y - r} Z" fill="${C.purple}"/>`).join("")}`);
  }
  return svg(`${shadow(70, 112, 44)}<rect x="22" y="16" width="96" height="84" rx="3" fill="#fff" stroke="${C.line}" transform="rotate(-4 70 58)"/>
    <g transform="rotate(-4 70 58)" fill="none" stroke="#5F5E5A" stroke-width="1.8" stroke-linecap="round">
      <circle cx="94" cy="34" r="9"/><path d="M30 86 Q60 78 110 84"/><circle cx="56" cy="62" r="11"/><path d="M48 54 L46 40 L55 50 M64 54 L66 40 L58 50"/></g>
    <g transform="rotate(35 106 86)"><rect x="96" y="60" width="9" height="46" rx="2" fill="${C.sun}"/><path d="M96 106 L100.5 116 L105 106 Z" fill="#F6EBD3"/><path d="M99 112 L100.5 116 L102 112 Z" fill="${C.ink}"/><rect x="96" y="56" width="9" height="6" fill="${C.pink}"/></g>`);
}

export function bookMockup(settings, title = "Your book") {
  const [w, h] = (settings.trim || "8.5x8.5").split("x").map(Number);
  const k = 10, W = w * k, H = h * k, x = 70 - W / 2, y = 112 - H;
  const t = settings.pages === "auto" ? 12 : 4 + ((settings.pages || 32) - 24) * 0.3;
  const hard = settings.format === "hardcover";
  const shine = settings.finish === "glossy" ? `<path d="M${x + W * 0.15} ${y} h${W * 0.25} L${x} ${y + H * 0.6} v-${H * 0.25} Z" fill="#fff" opacity=".35"/>` : "";
  // Wrap the (already escaped) title into up to three centered lines.
  const titleLines = (cx, top, width, color) => {
    const fs = Math.min(10, width / 7), max = Math.max(6, Math.floor(width / (fs * 0.56)));
    const out = [];
    for (const word of title.split(" ")) {
      const last = out[out.length - 1];
      if (last !== undefined && (last + " " + word).length <= max) out[out.length - 1] = last + " " + word;
      else out.push(word);
    }
    return out.slice(0, 3).map((l, i) =>
      `<text x="${cx}" y="${top + fs + i * fs * 1.15}" text-anchor="middle" font-size="${fs}" font-weight="600" fill="${color}">${l}</text>`).join("");
  };
  if (settings.format === "ebook") {
    return svg(`${shadow(70, 116, 40)}<rect x="28" y="4" width="84" height="110" rx="10" fill="${C.ink}"/>${scene(34, 12, 72, 92, { sky: "#E6F1FB" })}
      ${titleLines(70, 16, 64, "#0C447C")}`, "0 0 140 120");
  }
  return svg(`${shadow(70 + t / 2, 115, W / 2 + t)}
    <path d="M${x + W} ${y + (hard ? 2 : 0)} l${t} -${t * 0.5} v${H - (hard ? 4 : 0)} l-${t} ${t * 0.5} Z" fill="${settings.paper === "cream" ? C.cream : "#fff"}" stroke="#B4B2A9"/>
    <path d="M${x} ${y} l${t} -${t * 0.5} h${W} l-${t} ${t * 0.5} Z" fill="${hard ? "#3C3489" : "#E4E2DA"}"/>
    <rect x="${x}" y="${y}" width="${W}" height="${H}" rx="${hard ? 3 : 1}" fill="${C.purple}" stroke="${C.purpleDark}" stroke-width="${hard ? 2 : 1}"/>
    ${scene(x + W * 0.1, y + H * 0.42, W * 0.8, H * 0.48)}
    ${titleLines(x + W / 2, y + H * 0.05, W * 0.86, "#fff")}
    ${shine}`, "0 -10 140 130");
}

export function art(stepId, opt, settings) {
  switch (stepId) {
    case "audience": {
      const i = ["0-3", "3-7", "6-9", "8-12", "teen", "adult"].indexOf(opt.value);
      return svg(`${shadow(70, 112, 30)}${person(70, 110, 0.5 + i * 0.1, [C.coral, C.teal, C.sun, C.blue, C.purple, C.gray][i])}`);
    }
    case "bookType": return pageWith(opt.value);
    case "format": return books[opt.value]();
    case "trim": return trimArt(opt);
    case "pages": return pagesArt(opt);
    case "interior": return interiorArt(opt);
    case "paper": return paperArt(opt);
    case "finish": return finishArt(opt);
    case "artStyle": return styleArt(opt);
    case "layout": return layoutArt(opt);
    case "tone": return toneArt[opt.value]();
    case "extras": return extrasArt[opt.value]();
    case "mode": return modeArt[opt.value]();
    case "drawings": return drawingsArt(opt.value);
    default: return "";
  }
}
