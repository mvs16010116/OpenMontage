// build_radar_ew.mjs — military-radar-ew asset generator.
// Radar screen: rings, rotating sweep, blips; EW mode: noise bands + jamming.
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import process from "node:process";
import { composition, mulberry32 } from "../../_military-shared/composition.mjs";

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : d; };
function list(flag) {
  const out = [];
  const i = process.argv.indexOf(flag);
  if (i < 0) return out;
  for (let j = i + 1; j < process.argv.length; j++) { if (process.argv[j].startsWith("--")) break; out.push(process.argv[j]); }
  return out;
}
const project = arg("project", "demo");
const title = arg("title", "防空预警网");
const mode = arg("mode", "radar");
const range = arg("range", "400km");
const accent = mode === "ew" ? "#f87171" : "#4ade80";
const duration = Number(arg("duration", "8"));
const BG = "#04120b", FG = "#c7ffe0";
const rng = mulberry32(77123);

const blips = list("--blips").map((s) => {
  const [b, r, sev] = s.split(":").map(Number);
  return { b, r, sev: sev || 1 };
});
const CX = 1300, CY = 540, R = 360;

const ringHTML = [0.33, 0.56, 0.78, 1].map((f) =>
  `<circle cx="${CX}" cy="${CY}" r="${(R * f).toFixed(1)}" fill="none" stroke="${FG}" stroke-width="${f === 1 ? 2 : 1}" opacity="${f === 1 ? 0.7 : 0.25}"/>`).join("");
const axisHTML = `
  <line x1="${CX - R}" y1="${CY}" x2="${CX + R}" y2="${CY}" stroke="${FG}" stroke-width="1" opacity="0.2"/>
  <line x1="${CX}" y1="${CY - R}" x2="${CX}" y2="${CY + R}" stroke="${FG}" stroke-width="1" opacity="0.2"/>`;
const blipHTML = blips.map((x, i) => {
  const rad = (x.b * Math.PI) / 180;
  const px = CX + Math.cos(rad) * R * (x.r / 100);
  const py = CY - Math.sin(rad) * R * (x.r / 100);
  return `<circle id="blip-${i}" cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="${(8 + x.sev * 3).toFixed(1)}" fill="${accent}"/>`;
}).join("");

const ewNoise = Array.from({ length: 24 }, () => {
  const bar = { x: CX - R + rng() * R * 2, w: 4 + rng() * 26, y: CY - R + rng() * R * 2, o: 0.05 + rng() * 0.3 };
  return `<rect id="noise-${bar.x}" x="${bar.x}" y="${bar.y}" width="${bar.w}" height="${R * 2 - (bar.y - (CY - R))}" fill="${accent}" opacity="${bar.o}"/>`;
}).join("");

const html = composition({
  title: `military-radar-ew :: ${title}`,
  duration,
  bg: BG,
  css: `
    #title{position:absolute;left:60px;top:40px;font-size:56px;font-weight:700;letter-spacing:6px}
    #readout{position:absolute;left:60px;top:150px;font-size:28px;color:${FG};letter-spacing:2px}
    #range-tag{position:absolute;left:${CX - R}px;top:${CY + R + 30}px;font-size:26px;color:${FG};opacity:.7}
    #sweep{transform-origin:${CX}px ${CY}px}
    .blip{opacity:0}
  `,
  bodyInner: `
    <svg id="screen" viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice">
      <circle cx="${CX}" cy="${CY}" r="${R}" fill="rgba(74,222,128,.05)" stroke="${FG}" stroke-width="2"/>
      ${ringHTML}
      ${axisHTML}
      ${mode === "radar" ? `<path id="sweep" d="M${CX},${CY} L${CX + R},${CY - R * 0.02} L${CX + R * 0.97},${CY + R * 0.18} Z" fill="${accent}" opacity="0.2"/>` : ""}
      ${mode === "radar" ? blipHTML : ewNoise}
    </svg>
    <div id="title">${title}</div>
    <div id="readout">${mode === "ew" ? "电子战 · ECM" : "雷达扫描 · 脉冲多普勒"}</div>
    <div id="range-tag">探测范围 ${range}</div>
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    gsap.set("#title", { opacity: 0, y: -30 });
    tl.to("#title", { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 0.2);
    tl.from("#readout", { opacity: 0, duration: 0.4 }, 0.8);
    ${mode === "radar" ? `
    tl.fromTo("#sweep", { rotation: 0 }, { rotation: 360, duration: 2.4, ease: "none", repeat: Math.max(0, Math.floor((${duration} - 0.5) / 2.4)) }, 0.3);
    ${blips.map((b, i) => `
    tl.fromTo("#blip-${i}", { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, transformOrigin: "50% 50%", duration: 0.25 }, ${1.2 + i * 0.6});
    tl.to("#blip-${i}", { scale: 1.25, duration: 0.4, ease: "power1.inOut", repeat: Math.max(0, Math.floor((2.5) / 0.8)) }, ${1.5 + i * 0.6});`).join("\n    ")}` : `
    ${Array.from({ length: 24 }, (_, i) => `
    tl.fromTo(document.getElementById("noise-${i}"), { opacity: 0 }, { opacity: ${0.08 + rng() * 0.2}, duration: 0.6, ease: "power2.out" }, ${0.6 + rng() * 1.5});`).join("\n    ")}
    tl.fromTo("#readout", { color: "${accent}" }, { color: "${FG}", duration: 1, repeat: Math.max(0, Math.floor(2.4 / 2)) }, 1.2);`}
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-radar-ew] wrote ${out}`);
console.log(`[military-radar-ew] next: npx hyperframes lint && validate && render -o ../../renders/radar_ew.mp4`);