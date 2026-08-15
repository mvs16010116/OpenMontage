// build_agreement.mjs — military-agreement asset generator.
// Red-header official document + clause typewriter reveal + red seal slam +
// signature draw-on. Deterministic HyperFrames composition.
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import process from "node:process";
import { composition } from "../../_military-shared/composition.mjs";

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : d; };
function clauses() {
  const out = [];
  const i = process.argv.indexOf("--clauses");
  if (i < 0) return out;
  for (let j = i + 1; j < process.argv.length; j++) {
    if (process.argv[j].startsWith("--")) break;
    out.push(process.argv[j]);
  }
  return out;
}
const project = arg("project", "demo");
const title = arg("title", "联合声明");
const org = arg("org", "××集团");
const accent = arg("accent", "#ef4444");
const duration = Number(arg("duration", "8"));
const cls = clauses();
const BG = "#0a0c12", PAPER = "#f5f1e6", INK = "#1c1a17", RED = accent;

const clauseHTML = cls.map((c, i) => `<div class="clause" id="clause-${i}"><span class="num">${i + 1}</span> ${c}</div>`).join("");

const html = composition({
  title: `military-agreement :: ${title}`,
  duration,
  bg: BG,
  css: `
    #sheet{position:absolute;left:50%;top:50%;width:1180px;height:780px;margin-left:-590px;margin-top:-390px;
      background:${PAPER};border-radius:8px;box-shadow:0 30px 60px rgba(0,0,0,.55);padding:56px 70px;box-sizing:border-box}
    #redband{height:14px;background:${RED};position:absolute;left:0;right:0;top:0;border-radius:8px 8px 0 0}
    #doc-title{font-size:54px;font-weight:700;color:${INK};text-align:center;letter-spacing:10px;margin-top:14px}
    #doc-org{font-size:24px;color:${INK};opacity:.7;text-align:center;margin-top:8px;letter-spacing:3px}
    .clause{font-size:30px;color:${INK};line-height:1.9;margin-top:16px}
    .num{display:inline-block;width:34px;height:34px;line-height:34px;text-align:center;background:${RED};color:#fff;border-radius:50%;font-size:20px;margin-right:14px}
    #seal{position:absolute;right:120px;bottom:90px;width:170px;height:170px}
    #seal circle{fill:${RED};opacity:.16}
    #sigt{position:absolute;right:130px;bottom:36px;text-align:right;color:${INK}}
    #sigline{width:300px;height:0;border-top:2px solid ${INK};margin:0 auto 4px}
    #signame{font-size:22px;letter-spacing:2px}
  `,
  bodyInner: `
    <div id="sheet">
      <div id="redband"></div>
      <div id="doc-title">${title}</div>
      <div id="doc-org">${org}</div>
      <div id="doc-body">${clauseHTML}</div>
      <svg id="seal" viewBox="0 0 170 170">
        <circle cx="85" cy="85" r="80"></circle>
        <circle cx="85" cy="85" r="68" fill="none" stroke="${RED}" stroke-width="4"></circle>
        <path d="M85 28 L94 70 L136 70 L101 94 L113 136 L85 112 L57 136 L69 94 L34 70 L76 70 Z" fill="${RED}" opacity=".9"></path>
      </svg>
      <div id="sigt"><div id="sigline"></div><div id="signame">${org}</div></div>
    </div>
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    gsap.set("#sheet", { scale: 0.6, autoAlpha: 0, transformOrigin: "50% 50%" });
    gsap.set("#seal", { scale: 3, autoAlpha: 0, rotation: -30, transformOrigin: "50% 50%" });
    gsap.set(["#clause-0","#clause-1","#clause-2","#clause-3"], { x: 60, autoAlpha: 0 });

    tl.to("#sheet", { autoAlpha: 1, scale: 1, duration: 0.6, ease: "back.out(1.2)", transformOrigin: "50% 50%" }, 0.3);
    tl.from("#doc-title", { autoAlpha: 0, x: -40, duration: 0.5, ease: "power2.out" }, 0.7);
    tl.from("#doc-org", { autoAlpha: 0, duration: 0.4 }, 1.0);
    ${cls.map((_, i) => `tl.to("#clause-${i}", { x: 0, autoAlpha: 1, duration: 0.45, ease: "power2.out" }, ${1.3 + i * 0.5});`).join("\n    ")}

    const sealStart = ${(1.3 + cls.length * 0.5 + 0.3).toFixed(2)};
    tl.to("#seal", { autoAlpha: 1, duration: 0.05 }, sealStart);
    tl.to("#seal", { scale: 1, rotation: 0, duration: 0.3, ease: "back.out(2.6)", transformOrigin: "50% 50%" }, sealStart);
    tl.fromTo("#sigt", { autoAlpha: 0, x: 40 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: "power2.out" }, sealStart + 0.35);
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-agreement] wrote ${out}`);
console.log(`[military-agreement] next: npx hyperframes lint && validate && render -o ../../renders/agreement.mp4`);