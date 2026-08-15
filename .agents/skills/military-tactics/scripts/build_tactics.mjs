// build_tactics.mjs — military-tactics asset generator.
// Battlefield grid + own/enemy formations + movement arrows + phase card.
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import process from "node:process";
import { composition } from "../../_military-shared/composition.mjs";

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : d; };
function list(flag) {
  const out = [];
  const i = process.argv.indexOf(flag);
  if (i < 0) return out;
  for (let j = i + 1; j < process.argv.length; j++) { if (process.argv[j].startsWith("--")) break; out.push(process.argv[j]); }
  return out;
}
const project = arg("project", "demo");
const title = arg("title", "合围演练");
const phase = arg("phase", "左右钳击");
const accent = arg("accent", "#38bdf8");
const RED = "#ef4444";
const duration = Number(arg("duration", "8"));
const BG = "#070b12", FG = "#dbe7ff";

const own = list("--own").map((s) => { const [n, u] = s.split(":"); return { name: n, units: u }; });
const enemy = list("--enemy").map((s) => { const [n, u] = s.split(":"); return { name: n, units: u }; });
const arrows = list("--arrows").map((s) => { const p = s.split(":"); return { a: p[0], b: p[1], label: p[2] || "" }; });

// deterministic anchors: own on left/bottom, enemy center-right
const ownPos = own.map((_, i) => ({ x: 240 + (i % 2) * 260, y: 300 + Math.floor(i / 2) * 240 }));
const enemyPos = enemy.map((_, i) => ({ x: 1450, y: 320 + i * 220 }));
const anchor = (key) => {
  if (key.startsWith("own-")) return ownPos[Number(key.slice(4))];
  if (key.startsWith("enemy-")) return enemyPos[Number(key.slice(6))];
  return { x: 960, y: 540 };
};

const ownSVG = own.map((f, i) => {
  const p = ownPos[i];
  return `<g id="f-own-${i}" transform="translate(${p.x},${p.y})">
    <rect x="-60" y="-34" width="120" height="68" rx="8" fill="${accent}" opacity=".85"/>
    <text x="0" y="6" font-size="24" fill="#03111c" text-anchor="middle">${f.name}</text>
  </g>`;
}).join("");
const enemySVG = enemy.map((f, i) => {
  const p = enemyPos[i];
  return `<g id="f-enemy-${i}" transform="translate(${p.x},${p.y})">
    <path d="M0,-40 L46,0 L0,40 L-46,0 Z" fill="${RED}" opacity=".85"/>
    <text x="0" y="8" font-size="24" fill="#1c0300" text-anchor="middle">${f.name}</text>
  </g>`;
}).join("");
const arrowSVG = arrows.map((a, i) => {
  const s = anchor(a.a), e = anchor(a.b);
  const mx = (s.x + e.x) / 2, my = Math.min(s.y, e.y) - 120;
  return `
    <path id="t-arrow-${i}" d="M${s.x},${s.y} C${mx},${my} ${mx},${my} ${e.x},${e.y}" fill="none" stroke="${accent}" stroke-width="6" stroke-linecap="round" stroke-dasharray="26 14"/>
    <circle id="t-dot-${i}" r="12" fill="${accent}"/>
    <text id="t-label-${i}" x="${(s.x + e.x) / 2}" y="${(s.y + e.y) / 2}" font-size="28" fill="${FG}" text-anchor="middle"></text>`;
}).join("");
const legend = `<div id="legend"><span class="lg" style="background:${accent}"></span>本方 <span class="lg" style="background:${RED}"></span>对方</div>`;

const html = composition({
  title: `military-tactics :: ${title}`,
  duration,
  bg: BG,
  css: `
    svg#field{position:absolute;inset:0;width:100%;height:100%}
    #grid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px);background-size:80px 80px}
    #title{position:absolute;left:60px;top:40px;font-size:56px;font-weight:700;letter-spacing:6px}
    #phase-card{position:absolute;left:60px;bottom:70px;font-size:40px;color:${accent};letter-spacing:3px}
    #legend{position:absolute;right:60px;bottom:84px;font-size:26px;color:${FG};letter-spacing:2px}
    .lg{display:inline-block;width:22px;height:22px;border-radius:4px;margin:0 8px 0 18px;vertical-align:-4px}
  `,
  bodyInner: `
    <div id="grid"></div>
    <svg id="field" viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice">
      ${ownSVG}
      ${enemySVG}
      ${arrowSVG}
    </svg>
    <div id="title">${title}</div>
    <div id="phase-card">${phase}</div>
    ${legend}
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    gsap.set("#title", { opacity: 0, y: -30 });
    tl.to("#title", { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 0.2);
    ${own.map((_, i) => `tl.fromTo("#f-own-${i}", { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, transformOrigin: "50% 50%", duration: 0.4, ease: "back.out(1.6)" }, ${0.5 + i * 0.25});`).join("\n    ")}
    ${enemy.map((_, i) => `tl.fromTo("#f-enemy-${i}", { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, transformOrigin: "50% 50%", duration: 0.4, ease: "back.out(1.6)" }, ${0.7 + i * 0.25});`).join("\n    ")}
    ${arrows.map((a, i) => {
      const s = anchor(a.a), e = anchor(a.b);
      return `
    {
      const path = document.getElementById("t-arrow-${i}");
      const L = path.getTotalLength();
      path.style.strokeDasharray = "26 14";
      path.style.strokeDashoffset = L;
      const p = { t: 0 };
      const place = (t) => {
        const mt = 1 - t;
        const x = (mt*mt)*s.x + 2*mt*t*((s.x+e.x)/2) + (t*t)*e.x;
        const y = (mt*mt)*s.y + 2*mt*t*(Math.min(s.y,e.y)-120) + (t*t)*e.y;
        const d = document.getElementById("t-dot-${i}");
        d.setAttribute("cx", x); d.setAttribute("cy", y);
      };
      place(0);
      tl.to(path, { strokeDashoffset: 0, duration: 1.1, ease: "power1.inOut" }, ${1.4 + i * 0.4});
      tl.to(p, { t: 1, duration: 1.1, ease: "power1.inOut", onUpdate() { place(p.t); } }, ${1.4 + i * 0.4});
      tl.fromTo("#t-dot-${i}", { opacity: 1 }, { opacity: 1, duration: 0.05 }, ${1.4 + i * 0.4});
      document.getElementById("t-label-${i}").textContent = "${a.label}";
      tl.fromTo("#t-label-${i}", { opacity: 0 }, { opacity: 1, duration: 0.3 }, ${1.8 + i * 0.4});
    }`;
    }).join("\n    ")}
    tl.from("#phase-card", { opacity: 0, y: 20, duration: 0.5 }, 2.2);
    tl.from("#legend", { opacity: 0, duration: 0.4 }, 1.0);
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-tactics] wrote ${out}`);
console.log(`[military-tactics] next: npx hyperframes lint && validate && render -o ../../renders/tactics.mp4`);