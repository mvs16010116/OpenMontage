// build_org_chart.mjs — military-org-chart asset generator.
// Command-tree diagram: root + fan-out nodes, draw-on links, focus accent.
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
const title = arg("title", "战区指挥体系");
const root = arg("root", "联合参谋部");
const accent = arg("accent", "#38bdf8");
const focus = Number(arg("focus", "-1"));
const duration = Number(arg("duration", "8"));
const BG = "#070b12", FG = "#dbe7ff";
const nodes = list("--nodes").map((s) => {
  const [name, level] = s.split(":");
  return { name, level: level ? Number(level) : 1 };
});

const rootX = 960, rootY = 120, W = 320, H = 90;
// level 1 children under root; level 2 children under their level-1 parent slot
const l1 = nodes.filter((n) => n.level === 1);
const l2 = nodes.filter((n) => n.level === 2);
const l1X = (i) => 180 + (i * (1920 - 360)) / Math.max(1, l1.length - 1 || 1);
const l1Y = 380;
const l2X = (i) => { const li = Math.min(i, Math.max(0, l1.length - 1)); return l1X(li); };
const l2Y = 640;

const nodeHTML = `
  <div id="node-root" class="node root" style="left:${rootX - W / 2}px;top:${rootY}px">
    <div class="nlabel">${root}</div>
  </div>
  ${l1.map((n, i) => `
  <div id="node-l1-${i}" class="node" style="left:${l1X(i) - W / 2}px;top:${l1Y}px">
    <div class="nlabel">${n.name}</div>
  </div>`).join("")}
  ${l2.map((n, i) => `
  <div id="node-l2-${i}" class="node" style="left:${l2X(i) - W / 2}px;top:${l2Y}px">
    <div class="nlabel">${n.name}</div>
  </div>`).join("")}
`;
const linkHTML = `
  ${l1.map((_, i) => `<div id="link-l1-${i}" class="link v" style="left:${l1X(i)}px;top:${rootY + H}px;height:${l1Y - rootY - H}px"></div>`).join("")}
  ${l1.map((_, i) => `<div id="link-l1b-${i}" class="link h" style="left:${Math.min(l1X(0), l1X(i))}px;top:${l1Y}px;width:${Math.abs(l1X(i) - l1X(0))}px"></div>`).join("")}
  ${l2.map((_, i) => { const li = Math.min(i, Math.max(0, l1.length - 1)); return `<div id="link-l2-${i}" class="link v" style="left:${l1X(li)}px;top:${l1Y + H}px;height:${l2Y - l1Y - H}px"></div>`; }).join("")}
`;

const html = composition({
  title: `military-org-chart :: ${title}`,
  duration,
  bg: BG,
  css: `
    #title{position:absolute;left:60px;top:40px;font-size:56px;font-weight:700;letter-spacing:6px}
    .node{position:absolute;width:${W}px;height:${H}px;display:flex;align-items:center;justify-content:center;background:rgba(56,189,248,.08);border:2px solid ${accent};border-radius:12px;opacity:0}
    .node.root{background:rgba(56,189,248,.18)}
    .nlabel{font-size:30px;color:${FG};letter-spacing:2px}
    .focus .node{background:rgba(56,189,248,.28);box-shadow:0 0 24px ${accent}}
    .link{position:absolute;background:rgba(56,189,248,.5);transform-origin:top left;opacity:0}
    .link.v{width:3px}
    .link.h{height:3px}
  `,
  bodyInner: `
    <div id="title">${title}</div>
    ${linkHTML}
    ${nodeHTML}
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    tl.from("#title", { y: -40, opacity: 0, duration: 0.6, ease: "power3.out" }, 0.2);
    tl.to("#node-root", { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.4)" }, 0.6);
    ${l1.map((_, i) => `
    tl.to("#link-l1-${i}", { opacity: 1, scaleY: 1, duration: 0.4, ease: "power2.out" }, ${1.0 + i * 0.25});
    tl.to("#node-l1-${i}", { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }, ${1.05 + i * 0.25});`).join("\n    ")}
    ${l2.map((_, i) => `
    tl.to("#link-l2-${i}", { opacity: 1, scaleY: 1, duration: 0.4, ease: "power2.out" }, ${1.2 + i * 0.2});
    tl.to("#node-l2-${i}", { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }, ${1.25 + i * 0.2});`).join("\n    ")}
    ${focus > 0 ? `
    {
      const targets = ["#node-root"].concat(${JSON.stringify(l1.map((_, i) => "#node-l1-" + i))});
      const t = targets[${focus}];
      if (t) tl.to(t, { boxShadow: "0 0 30px ${accent}", duration: 0.5, ease: "power2.out" }, 2.4);
    }` : ""}
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-org-chart] wrote ${out}`);
console.log(`[military-org-chart] next: npx hyperframes lint && validate && render -o ../../renders/org_chart.mp4`);