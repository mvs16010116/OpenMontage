// build_map_deduction.mjs — military-map-deduction asset generator.
// Schematized theatre map: region silhouettes fill in, force arrows draw on with
// traveling markers, phase label + pinned callouts. Deterministic composition.
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
  for (let j = i + 1; j < process.argv.length; j++) {
    if (process.argv[j].startsWith("--")) break;
    out.push(process.argv[j]);
  }
  return out;
}
const project = arg("project", "demo");
const theatre = arg("theatre", "亚太");
const phase = arg("phase", "第一阶段 · 集结部署");
const accent = arg("accent", "#fbbf24");
const duration = Number(arg("duration", "9"));
const rng = mulberry32(881);
const BG = "#070b12", FG = "#d9e6ff", DIM = "rgba(217,230,255,.55)";

const regions = list("--regions").map((s) => {
  const [name, style] = s.split(":");
  return { name, style: style || "高亮" };
});
const arrows = list("--arrows").map((s) => {
  const m = s.match(/(.+?)→(.+?)(?::(.*))?$/);
  return { from: m?.[1] || "北", to: m?.[2] || "南", label: m?.[3] || "" };
});

const regionMeta = [];
// deterministic region silhouettes (blobby coast, seeded)
const regionSVG = (r, i) => {
  const cx = 300 + rng() * 1320, cy = 240 + rng() * 560;
  const rx = 150 + rng() * 200, ry = 110 + rng() * 150;
  const d = `M${cx},${cy - ry} C${cx + rx * 1.1},${cy - ry} ${cx + rx},${cy} ${cx},${cy + ry} C${cx - rx},${cy + ry} ${cx - rx * 1.1},${cy - ry} ${cx},${cy - ry} Z`;
  const hi = r.style === "重点" || r.style === "高亮";
  const lw = r.name.length * 38 + 24;
  regionMeta[i] = { cx, cy, name: r.name, lw };
  return `<path id="region-${i}" d="${d}" fill="${hi ? accent : DIM}" opacity="0"/>`;
};
const regionLabelSVG = (i) => {
  const { cx, cy, name, lw } = regionMeta[i];
  return `<g id="region-label-${i}" opacity="0">` +
         `<rect x="${(cx - lw / 2).toFixed(1)}" y="${cy - 30}" width="${lw}" height="60" rx="10" fill="#0a0f16"/>` +
         `<text x="${cx}" y="${cy + 12}" font-size="34" fill="${FG}" text-anchor="middle">${name}</text>` +
         `</g>`;
};

// bezier for an arrow, plus the point-at-t helper
const arrowData = (a, i) => {
  const sx = 200 + rng() * 1520, sy = 640 + rng() * 240;
  const ex = 200 + rng() * 1520, ey = 180 + rng() * 420;
  const mx = (sx + ex) / 2, my = Math.min(sy, ey) - 140;
  return { i, sx, sy, ex, ey, mx, my, label: a.label };
};

const regionFillHTML = regions.map((r, i) => regionSVG(r, i)).join("");
const regionLabelHTML = regions.map((_, i) => regionLabelSVG(i)).join("");
const arrowHTML = arrows.map((a, i) => {
  const { sx, sy, ex, ey, mx, my } = arrowData(a, i);
  const alw = a.label.length * 30 + 24;
  return `<path id="arrow-${i}" d="M${sx},${sy} C${mx},${my} ${mx},${my} ${ex},${ey}" fill="none" stroke="${accent}" stroke-width="5" stroke-linecap="round"/>` +
         `<circle id="dot-${i}" r="11" fill="${accent}" opacity="0" data-layout-allow-overflow/>` +
         `<g id="arrow-label-${i}" opacity="0">` +
         `<rect x="${(((sx + ex) / 2) - alw / 2).toFixed(1)}" y="${((sy + ey) / 2) - 22}" width="${alw}" height="40" rx="8" fill="#0a0f16"/>` +
         `<text x="${(sx + ex) / 2}" y="${((sy + ey) / 2) + 6}" font-size="26" fill="${FG}" text-anchor="middle">${a.label}</text>` +
         `</g>`;
}).join("");

const calloutHTML = regions.filter((r) => r.style === "重点").slice(0, 3).map((r, i) => `
  <div id="callout-${i}" class="callout" style="left:${140 + i * 560}px;top:900px;opacity:0">
    <span class="chip" style="background:${accent}"></span>${r.name}
  </div>`).join("");

const html = composition({
  title: `military-map-deduction :: ${theatre}`,
  duration,
  bg: BG,
  css: `
    svg#map{position:absolute;inset:0;width:100%;height:100%}
    #theatre-title{position:absolute;left:60px;top:44px;font-size:62px;font-weight:700;letter-spacing:8px}
    #phase-tag{position:absolute;left:60px;top:150px;font-size:28px;color:${accent};letter-spacing:3px}
    #hint{position:absolute;left:60px;bottom:36px;font-size:20px;color:${DIM}}
    .callout{position:absolute;width:480px;font-size:28px;color:${FG};letter-spacing:2px}
    .chip{display:inline-block;width:14px;height:14px;border-radius:3px;margin-right:12px}
  `,
  bodyInner: `
    <svg id="map" viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice">
      ${regionFillHTML}
      ${regionLabelHTML}
      ${arrowHTML}
    </svg>
    <div id="theatre-title">${theatre}</div>
    <div id="phase-tag">${phase}</div>
    ${calloutHTML}
    <div id="hint">OpenMontage · military-map-deduction · 推演示意</div>
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    gsap.set("#theatre-title", { x: -30 });
    // region fill-in stagger
    ${regions.map((_, i) => `tl.to("#region-${i}", { opacity: ${regions[i].style === "重点" ? 0.85 : 0.5}, duration: 0.7 }, ${0.4 + i * 0.25});
    tl.to("#region-label-${i}", { autoAlpha: 1, duration: 0.4 }, ${0.8 + i * 0.25});`).join("\n    ")}
    // arrows draw-on + traveling marker (proxy tween onUpdate along bezier)
    ${arrows.map((a, i) => {
      const { sx, sy, ex, ey, mx, my } = arrowData(a, i);
      return `
    {
      const path = document.getElementById("arrow-${i}");
      const L = path.getTotalLength();
      path.style.strokeDasharray = L + " " + L;
      path.style.strokeDashoffset = L;
      const prox = { p: 0 };
      const place = (t) => {
        const mt = 1 - t;
        const x = (mt*mt)*sx + 2*mt*t*mx + (t*t)*ex;
        const y = (mt*mt)*sy + 2*mt*t*my + (t*t)*ey;
        const d = document.getElementById("dot-${i}");
        d.setAttribute("cx", x); d.setAttribute("cy", y);
      };
      tl.to(path, { strokeDashoffset: 0, duration: 1.3, ease: "power1.inOut" }, ${1.6 + i * 0.5});
      tl.fromTo("#dot-${i}", { opacity: 1 }, { opacity: 1, duration: 0.05 }, ${1.6 + i * 0.5});
      tl.to(prox, { p: 1, duration: 1.3, ease: "power1.inOut", onUpdate() { place(prox.p); } }, ${1.6 + i * 0.5});
      tl.to("#arrow-label-${i}", { autoAlpha: 1, duration: 0.35 }, ${2.0 + i * 0.5});
    }`;
    }).join("\n    ")}
    // callouts
    ${regions.filter((r) => r.style === "重点").map((_, i) => `tl.to("#callout-${i}", { opacity: 1, y: -10, duration: 0.5 }, ${2.6 + i * 0.3});`).join("\n    ")}
    tl.from("#theatre-title", { autoAlpha: 0, x: -40, duration: 0.6, ease: "power3.out" }, 0.2);
    tl.from("#phase-tag", { autoAlpha: 0, duration: 0.5 }, 0.9);
    tl.from("#hint", { autoAlpha: 0, duration: 0.5 }, 1.2);
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-map-deduction] wrote ${out}`);
console.log(`[military-map-deduction] next: npx hyperframes lint && validate && render -o ../../renders/map_deduction.mp4`);