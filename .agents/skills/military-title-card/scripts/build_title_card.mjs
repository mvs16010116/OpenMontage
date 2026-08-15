// build_title_card.mjs — military-title-card asset generator.
// Headline + keyword highlight + optional count-up number + lower-third.
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import process from "node:process";
import { composition } from "../../_military-shared/composition.mjs";

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : d; };
const project = arg("project", "demo");
const title = arg("title", "新时代军事战略方针");
const keyword = arg("keyword", "");
const lower = arg("lower", "");
const accent = arg("accent", "#fbbf24");
const duration = Number(arg("duration", "6"));
const BG = "#070b12", FG = "#fff3d6";
const numArg = arg("number", "");
const [numTarget, numLabel] = numArg.split(":");
const hasNum = numArg !== "";

// split title into words (each a block-level span so transforms work)
const words = title.split(/(?<=[^\s])/).join("").match(/[\s\S]*/)[0].split("");
const wordHTML = title
  .split("")
  .map((ch, i) => `<span class="w" id="w-${i}">${ch === " " ? "&nbsp;" : ch}</span>`)
  .join("");

const html = composition({
  title: `military-title-card :: ${title}`,
  duration,
  bg: BG,
  css: `
    #headline{position:absolute;left:0;right:0;top:34%;text-align:center;font-size:96px;font-weight:700;letter-spacing:14px;color:${FG}}
    .w{display:inline-block}
    #kwbar{position:absolute;left:50%;top:${keyword ? "64%" : "52%"};width:520px;height:10px;margin-left:-260px;background:${accent};transform-origin:left;display:block}
    #kwtag{position:absolute;left:0;right:0;top:${hasNum ? "70%" : "58%"};text-align:center;font-size:42px;color:${accent};letter-spacing:8px;opacity:0}
    #numwrap{position:absolute;left:0;right:0;top:76%;text-align:center;opacity:0}
    #numval{display:inline-block;font-size:120px;font-weight:700;color:${FG}}
    #numlabel{display:inline-block;font-size:36px;color:${accent};margin-left:18px;letter-spacing:3px}
    #lower-third{position:absolute;left:60px;bottom:56px;font-size:28px;color:${FG};opacity:.85;letter-spacing:3px;opacity:0}
  `,
  bodyInner: `
    <div id="headline">${wordHTML}</div>
    ${keyword ? `<div id="kwbar"></div><div id="kwtag">${keyword}</div>` : ""}
    ${hasNum ? `<div id="numwrap"><span id="numval" data-t="${Number(numTarget) || 0}">0</span><span id="numlabel">${numLabel || ""}</span></div>` : ""}
    ${lower ? `<div id="lower-third">${lower}</div>` : ""}
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    gsap.set(${JSON.stringify(title.split("").map((_, i) => "#w-" + i))}, { y: 60, opacity: 0 });
    tl.to(${JSON.stringify(title.split("").map((_, i) => "#w-" + i))}, {
      y: 0, opacity: 1, duration: 0.6, ease: "power3.out", stagger: 0.04,
    }, 0.3);
    ${keyword ? `
    tl.fromTo("#kwbar", { scaleX: 0 }, { scaleX: 1, duration: 0.7, ease: "power2.inOut" }, 1.2);
    tl.to("#kwtag", { opacity: 1, duration: 0.5 }, 1.6);` : ""}
    ${hasNum ? `
    tl.to("#numwrap", { opacity: 1, duration: 0.3 }, 2.0);
    {
      const el = document.getElementById("numval");
      const p = { v: 0 };
      tl.to(p, { v: ${Number(numTarget) || 0}, duration: 1.4, ease: "power2.out", onUpdate() { el.textContent = Math.round(p.v); } }, 2.1);
    }` : ""}
    ${lower ? `tl.to("#lower-third", { opacity: 0.85, duration: 0.5 }, 1.0);` : ""}
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-title-card] wrote ${out}`);
console.log(`[military-title-card] next: npx hyperframes lint && validate && render -o ../../renders/title_card.mp4`);