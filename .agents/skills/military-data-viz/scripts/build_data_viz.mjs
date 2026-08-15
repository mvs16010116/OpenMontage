// build_data_viz.mjs — military-data-viz asset generator.
// Bars / timeline / KPI card with count-up. Deterministic HyperFrames composition.
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
const title = arg("title", "军费对比");
const type = arg("type", "bars");
const accent = arg("accent", "#22c55e");
const kpi = arg("kpi", "");
const duration = Number(arg("duration", "8"));
const BG = "#070b12", FG = "#dbe7ff", DIM = "rgba(219,231,255,.6)";
const bars = list("--bars").map((s) => { const [label, value] = s.split(":"); return { label, value }; });
const timeline = list("--timeline").map((s) => { const [t, ev] = s.split(":"); return { t: +t || 0, ev }; });

const maxV = Math.max(1, ...bars.map((b) => Number.parseFloat(b.value) || 0));

const barHTML = bars.map((b, i) => {
  const v = Number.parseFloat(b.value) || 0;
  return `
  <div class="row" id="row-${i}">
    <div class="blabel">${b.label}</div>
    <div class="btrack"><div class="bar" id="bar-${i}" style="--w:${(v / maxV) * 100}%"></div></div>
    <div class="bval"><span class="num" data-t="${v}">0</span><span class="unit">${b.value.replace(/[0-9.+\-]/g, "").trim()}</span></div>
  </div>`;
}).join("");

const tlHTML = (() => {
  if (type !== "timeline") return "";
  return timeline.map((e, i) => `
    <div class="trow" id="trow-${i}" style="top:${210 + i * 160}px">
      <div class="tdot"></div>
      <div class="tevt"><b>${e.t} 年</b> — ${e.ev}</div>
    </div>`).join("");
})();

const bodyInner = type === "timeline"
  ? `
    <div id="title">${title}</div>
    <div id="rail"></div>
    ${tlHTML}
    ${kpi ? `<div id="kpi">${kpi}</div>` : ""}
  `
  : `
    <div id="title">${title}</div>
    <div id="chart">${barHTML}</div>
    ${kpi ? `<div id="kpi">${kpi}</div>` : ""}
  `;

const html = composition({
  title: `military-data-viz :: ${title}`,
  duration,
  bg: BG,
  css: `
    #title{position:absolute;left:60px;top:44px;font-size:60px;font-weight:700;letter-spacing:6px}
    #chart{position:absolute;left:120px;top:210px;right:140px}
    .row{display:flex;align-items:center;margin-bottom:46px}
    .blabel{width:300px;font-size:34px;color:${FG};letter-spacing:2px}
    .btrack{flex:1;height:56px;background:rgba(255,255,255,.06);border-radius:8px;overflow:hidden}
    .bar{width:var(--w);height:100%;background:${accent};border-radius:8px;transform-origin:left;display:block}
    .bval{width:360px;text-align:right;font-size:44px;color:${FG};font-weight:700}
    .unit{font-size:26px;color:${DIM};margin-left:8px;font-weight:400}
    #kpi{position:absolute;left:120px;bottom:56px;font-size:36px;color:${accent};letter-spacing:2px}
    #rail{position:absolute;left:130px;top:200px;bottom:200px;border-left:3px dashed rgba(255,255,255,.18)}
    .trow{position:absolute;left:150px;right:160px;display:flex;align-items:center;opacity:0}
    .tdot{width:18px;height:18px;border-radius:50%;background:${accent};margin-right:22px}
    .tevt{font-size:32px;color:${FG};letter-spacing:1px}
    .tevt b{color:${accent}}
  `,
  bodyInner,
  script: type === "timeline" ? `
    const tl = gsap.timeline({ paused: true });
    tl.from("#title", { y: -40, opacity: 0, duration: 0.6, ease: "power3.out" }, 0.2);
    ${timeline.map((_, i) => `tl.to("#trow-${i}", { opacity: 1, x: 0, duration: 0.45, ease: "power2.out" }, ${0.9 + i * 0.6});`).join("\n    ")}
    ${kpi ? `tl.from("#kpi", { opacity: 0, y: 20, duration: 0.5 }, ${0.9 + timeline.length * 0.6});` : ""}
    window.__timelines["main"] = tl;
  ` : `
    const tl = gsap.timeline({ paused: true });
    tl.from("#title", { y: -40, opacity: 0, duration: 0.6, ease: "power3.out" }, 0.2);
    ${bars.map((b, i) => {
      const v = Number.parseFloat(b.value) || 0;
      return `
    tl.fromTo("#bar-${i}", { scaleX: 0 }, { scaleX: 1, duration: 0.9, ease: "power2.out" }, ${0.6 + i * 0.35});
    {
      const el = document.querySelector("#row-${i} .num");
      const p = { v: 0 };
      tl.to(p, { v: ${v}, duration: 0.9, ease: "power2.out", onUpdate() { el.textContent = Math.round(p.v); } }, ${0.6 + i * 0.35});
    }`;
    }).join("\n    ")}
    ${kpi ? `tl.from("#kpi", { opacity: 0, y: 20, duration: 0.5 }, ${0.6 + bars.length * 0.35});` : ""}
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-data-viz] wrote ${out}`);
console.log(`[military-data-viz] next: npx hyperframes lint && validate && render -o ../../renders/data_viz.mp4`);