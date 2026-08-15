// build_seal.mjs — military-seal asset generator.
// Red-header document + red circular 五角星 seal slam + caption.
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import process from "node:process";
import { composition } from "../../_military-shared/composition.mjs";

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : d; };
const project = arg("project", "demo");
const title = arg("title", "批复文件");
const org = arg("org", "某部装备处");
const sealText = arg("seal-text", "中国人民解放军装备部");
const accent = arg("accent", "#d33");
const duration = Number(arg("duration", "6"));
const BG = "#0a0c12", PAPER = "#f5f1e6", INK = "#1c1a17";

// place chars along the outer ring (top arc, symmetric)
const RING = 120, chars = sealText.split("");
const charSVG = chars.map((c, i) => {
  const total = chars.length;
  const span = Math.min(total * 18, 150);
  const start = -span / 2;
  const ang = ((start + i * (span / (total - 1))) * Math.PI) / 180 - Math.PI / 2;
  const x = RING * Math.cos(ang), y = RING * Math.sin(ang);
  return `<g transform="translate(${x.toFixed(1)},${y.toFixed(1)} ) rotate(${((ang + Math.PI / 2) * 180 / Math.PI).toFixed(1)})"><text x="0" y="7" font-size="20" text-anchor="middle" fill="${accent}">${c}</text></g>`;
}).join("");

const html = composition({
  title: `military-seal :: ${title}`,
  duration,
  bg: BG,
  css: `
    #sheet{position:absolute;left:50%;top:50%;width:1000px;height:660px;margin-left:-500px;margin-top:-330px;background:${PAPER};border-radius:8px;box-shadow:0 30px 60px rgba(0,0,0,.55);padding:48px 64px;box-sizing:border-box}
    #redband{height:13px;background:${accent};position:absolute;left:0;right:0;top:0;border-radius:8px 8px 0 0}
    #doc-title{font-size:48px;font-weight:700;color:${INK};text-align:center;letter-spacing:9px;margin-top:10px}
    #doc-org{font-size:24px;color:${INK};opacity:.7;text-align:center;margin-top:6px;letter-spacing:3px}
    #sealwrap{position:absolute;right:170px;bottom:120px;width:260px;height:260px}
    #seal{transform-origin:50% 50%}
    #caption{position:absolute;left:0;right:0;bottom:60px;text-align:center;font-size:34px;color:${accent};letter-spacing:5px;opacity:0}
  `,
  bodyInner: `
    <div id="sheet">
      <div id="redband"></div>
      <div id="doc-title">${title}</div>
      <div id="doc-org">${org}</div>
      <div id="sealwrap">
        <svg id="seal" viewBox="-145 -145 290 290">
          <circle cx="0" cy="0" r="130" fill="${accent}" opacity=".85"/>
          <circle cx="0" cy="0" r="130" fill="none" stroke="#fff" stroke-width="3"/>
          <circle cx="0" cy="0" r="92" fill="none" stroke="#fff" stroke-width="2" opacity=".9"/>
          ${charSVG}
          <path d="M0,-58 L14,-24 L52,-24 L20,4 L33,42 L0,18 L-33,42 L-20,4 L-52,-24 L-14,-24 Z" fill="#fff"/>
        </svg>
      </div>
      <div id="caption">盖章生效 · 批准</div>
    </div>
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    gsap.set("#sheet", { autoAlpha: 0, scale: 0.92, transformOrigin: "50% 50%" });
    gsap.set("#seal", { scale: 2.4, autoAlpha: 0, rotation: -14, transformOrigin: "50% 50%" });
    tl.to("#sheet", { autoAlpha: 1, scale: 1, duration: 0.6, ease: "power2.out", transformOrigin: "50% 50%" }, 0.2);
    tl.from("#doc-title", { autoAlpha: 0, x: -30, duration: 0.4 }, 0.6);
    tl.from("#doc-org", { autoAlpha: 0, duration: 0.35 }, 0.9);
    // seal slam (landing beat)
    tl.to("#seal", { autoAlpha: 1, duration: 0.04 }, 1.6);
    tl.to("#seal", { scale: 1, rotation: 0, duration: 0.32, ease: "back.out(2.4)", transformOrigin: "50% 50%" }, 1.6);
    // subtle ink pulse (finite)
    tl.to("#seal", { scale: 1.04, duration: 0.22, yoyo: true, repeat: 1 }, 2.0);
    tl.to("#caption", { autoAlpha: 1, duration: 0.5 }, 2.5);
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-seal] wrote ${out}`);
console.log(`[military-seal] next: npx hyperframes lint && validate && render -o ../../renders/seal.mp4`);