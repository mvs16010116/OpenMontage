// build_equipment_icons.mjs — military-equipment-icons asset generator.
// Consistent vector icon system grid with name plates + focus ring.
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
const title = arg("title", "装备体系概览");
const accent = arg("accent", "#38bdf8");
const duration = Number(arg("duration", "8"));
const BG = "#070b12", FG = "#dbe7ff";
const icons = list("--icons").map((s) => { const [id, name] = s.split(":"); return { id, name }; });

// consistent 2-stroke silhouettes, viewBox 0 0 200 200
const PATHS = {
  tank: `<path d="M40,120 L50,80 L150,80 L160,120 Z" fill="none" stroke="${FG}" stroke-width="5"/><path d="M70,70 L130,70 L120,40 L80,40 Z" fill="none" stroke="${FG}" stroke-width="5"/><circle cx="60" cy="120" r="14" fill="${FG}"/><circle cx="140" cy="120" r="14" fill="${FG}"/><path d="M38,128 L38,144 M162,128 L162,144 M60,146 L140,146" stroke="${FG}" stroke-width="5"/>`,
  fighter: `<path d="M100,40 L160,150 L100,120 L40,150 Z" fill="${FG}"/><path d="M40,120 L160,120 L100,90 Z" fill="none" stroke="${FG}" stroke-width="5"/><circle cx="100" cy="95" r="6" fill="${FG}"/>`,
  missile: `<path d="M95,40 L105,40 L105,110 L95,110 Z" fill="${FG}"/><path d="M88,104 L112,104 L112,150 L88,150 Z" fill="none" stroke="${FG}" stroke-width="4"/><path d="M100,30 L108,48 L92,48 Z" fill="${FG}"/><circle cx="100" cy="70" r="5" fill="${FG}"/>`,
  ship: `<path d="M50,90 L80,120 L160,120 L170,90 Z" fill="${FG}"/><path d="M90,86 L105,40 L130,40 L145,86 Z" fill="none" stroke="${FG}" stroke-width="5"/><circle cx="112" cy="34" r="5" fill="${accent}"/><path d="M30,120 L40,132 L190,132 L200,120" stroke="${FG}" stroke-width="5"/>`,
  drone: `<path d="M80,80 L40,40 M120,80 L160,40 M80,120 L40,160 M120,120 L160,160" stroke="${FG}" stroke-width="5"/><circle cx="40" cy="40" r="16" fill="none" stroke="${FG}" stroke-width="5"/><circle cx="160" cy="40" r="16" fill="none" stroke="${FG}" stroke-width="5"/><circle cx="40" cy="160" r="16" fill="none" stroke="${FG}" stroke-width="5"/><circle cx="160" cy="160" r="16" fill="none" stroke="${FG}" stroke-width="5"/><rect x="90" y="90" width="20" height="20" rx="4" fill="${FG}"/>`,
  radar: `<circle cx="100" cy="100" r="55" fill="none" stroke="${FG}" stroke-width="5"/><circle cx="100" cy="100" r="36" fill="none" stroke="${FG}" stroke-width="3" opacity=".5"/><path d="M100,100 L100,45" stroke="${accent}" stroke-width="6"/><circle cx="100" cy="100" r="7" fill="${accent}"/>`,
  carrier: `<path d="M40,95 L70,120 L200,120 L220,95 Z" fill="${FG}"/><path d="M90,92 L120,60 L160,60 L180,92 Z" fill="none" stroke="${FG}" stroke-width="5"/><rect x="120" y="46" width="50" height="10" fill="${FG}"/>`,
};

// 3x2 grid cells
const layout = icons.length > 4 ? { cols: 3, rows: 2, cell: 560, ox: 150, oy: 210, cw: 540, ch: 330 } : { cols: 4, rows: 1, cell: 420, ox: 140, oy: 300, cw: 400, ch: 360 };

const cellHTML = icons.map((ic, i) => {
  const col = i % layout.cols, row = Math.floor(i / layout.cols);
  const x = layout.ox + col * layout.cell, y = layout.oy + row * layout.cell;
  const focus = i === icons.length - 1;
  const path = PATHS[ic.id] || PATHS.tank;
  return `
  <div id="cell-${i}" class="cell" style="left:${x}px;top:${y}px;width:${layout.cw}px;height:${layout.ch}px">
    <div class="icwrap"><svg viewBox="0 0 200 200" preserveAspectRatio="xMidYMid meet">${path}</svg></div>
    <div class="iname">${ic.name}</div>
    ${focus ? `<div class="ring"></div>` : ""}
  </div>`;
}).join("");

const html = composition({
  title: `military-equipment-icons :: ${title}`,
  duration,
  bg: BG,
  css: `
    #title{position:absolute;left:60px;top:40px;font-size:56px;font-weight:700;letter-spacing:6px}
    .cell{position:absolute;border-radius:16px;background:rgba(56,189,248,.06);display:flex;flex-direction:column;align-items:center;justify-content:center;opacity:0}
    .icwrap{width:200px;height:170px}
    .icwrap svg{width:100%;height:100%}
    .iname{font-size:30px;color:${FG};letter-spacing:2px;margin-top:6px}
    .ring{position:absolute;inset:0;border:3px solid ${accent};border-radius:16px;box-shadow:0 0 30px ${accent}}
  `,
  bodyInner: `
    <div id="title">${title}</div>
    ${cellHTML}
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    tl.from("#title", { y: -40, opacity: 0, duration: 0.6, ease: "power3.out" }, 0.2);
    ${icons.map((_, i) => `
    tl.to("#cell-${i}", { opacity: 1, scale: 1, transformOrigin: "50% 50%", duration: 0.45, ease: "back.out(1.5)" }, ${0.6 + i * 0.28});
    ${i === icons.length - 1 ? `tl.to("#cell-${i} .ring", { opacity: 1, duration: 0.3 }, ${0.6 + i * 0.28 + 0.2});` : ""}`).join("\n    ")}
    ${icons.length > 1 ? `tl.to("#cell-${icons.length - 1}", { scale: 1.04, duration: 0.35, yoyo: true, repeat: 2, transformOrigin: "50% 50%" }, ${0.6 + (icons.length - 1) * 0.28 + 0.5});` : ""}
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-equipment-icons] wrote ${out}`);
console.log(`[military-equipment-icons] next: npx hyperframes lint && validate && render -o ../../renders/equipment_icons.mp4`);