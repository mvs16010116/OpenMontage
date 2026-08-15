// build_insignia.mjs — military-insignia asset generator.
// Emblem reveal (star/shield/flag/wreath) + shine sweep + name plate.
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import process from "node:process";
import { composition } from "../../_military-shared/composition.mjs";

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : d; };
const project = arg("project", "demo");
const title = arg("title", "陆军徽标");
const sub = arg("sub", "忠诚 · 无畏");
const kind = arg("kind", "star");
const accent = arg("accent", "#facc15");
const duration = Number(arg("duration", "7"));
const BG = "#070b12", FG = "#fff3d6";

const star = `
  <path d="M0,-150 L35,-48 L148,-48 L56,20 L88,130 L0,66 L-88,130 L-56,20 L-148,-48 L-35,-48 Z" fill="${accent}" stroke="${FG}" stroke-width="3"/>
  <circle cx="0" cy="0" r="150" fill="none" stroke="${accent}" stroke-width="2" opacity="0.5"/>
  <path d="M-70,-40 C-20,-120 20,-120 70,-40 C20,10 -20,10 -70,-40 Z" fill="rgba(255,243,214,.14)"/>`;
const shield = `
  <path d="M0,-140 L110,-110 L110,20 C110,80 66,120 0,140 C-66,120 -110,80 -110,20 L-110,-110 Z" fill="${accent}" stroke="${FG}" stroke-width="3"/>
  <path d="M0,-90 L55,10 L0,34 L-55,10 Z" fill="${FG}" opacity=".85"/>`;
const wreath = `
  <ellipse cx="-70" cy="0" rx="40" ry="120" fill="none" stroke="${accent}" stroke-width="8"/>
  <ellipse cx="70" cy="0" rx="40" ry="120" fill="none" stroke="${accent}" stroke-width="8"/>
  <path d="M0,-100 L30,-40 L0,10 L-30,-40 Z" fill="${accent}"/>
  <circle cx="0" cy="10" r="46" fill="none" stroke="${accent}" stroke-width="4"/>`;

const emblem = { star, shield, wreath }[kind] || star;
const flagHTML = `
  <g id="pole"><rect x="-6" y="-150" width="12" height="300" rx="4" fill="${FG}"/></g>
  <path id="flagcloth" d="M12,-120 L320,-152 L320,-44 L12,-16 Z" fill="${accent}"/>
  <circle id="flagstar" cx="80" cy="-84" r="34" fill="${FG}"/>`;

const emblemSVG = kind === "flag"
  ? `<svg id="flag" viewBox="-80 -165 420 340" preserveAspectRatio="xMidYMid meet">${flagHTML}</svg>`
  : `<svg id="emblem" viewBox="-170 -170 340 340" preserveAspectRatio="xMidYMid meet">${emblem}</svg>`;

const html = composition({
  title: `military-insignia :: ${title}`,
  duration,
  bg: BG,
  css: `
    #emblem,#flag{position:absolute;left:50%;top:46%;width:520px;height:520px;margin-left:-260px;margin-top:-260px}
    #shine{position:absolute;left:10%;top:-20%;height:140%;width:240px;background:linear-gradient(90deg,rgba(255,255,255,0),rgba(255,255,255,.16),rgba(255,255,255,0));transform:rotate(20deg);display:block}
    #plate{position:absolute;left:0;right:0;bottom:150px;text-align:center}
    #plate-title{font-size:54px;font-weight:700;letter-spacing:10px;color:${FG}}
    #plate-sub{font-size:28px;color:${accent};letter-spacing:6px;margin-top:12px}
  `,
  bodyInner: `
    ${emblemSVG}
    <div id="plate"><div id="plate-title">${title}</div><div id="plate-sub">${sub}</div></div>
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    gsap.set("#shine", { xPercent: -180 });
    ${kind === "flag" ? `
    // waving flag: deterministic path distortion via proxy onUpdate
    {
      const path = document.getElementById("flagcloth");
      const p = { t: 0 };
      const wave = (t) => {
        const f = 0.05 + 0.02 * Math.sin(t * Math.PI);
        path.setAttribute("d", "M12,-120 L320," + (-152 + f * 140) + " L320," + (-44 - f * 120) + " L12,-16 Z");
      };
      tl.to(p, { t: 1, duration: ${Math.min(5, duration - 1.2)}, ease: "none", onUpdate() { wave(p.t); } }, 0.6);
    }
    tl.fromTo("#flag", { scale: 0.6, opacity: 0 }, { scale: 1, opacity: 1, transformOrigin: "50% 50%", duration: 0.7, ease: "back.out(1.5)" }, 0.3);` : `
    tl.fromTo("#emblem", { scale: 0.5, opacity: 0, rotation: -12 }, { scale: 1, opacity: 1, rotation: 0, transformOrigin: "50% 50%", duration: 0.8, ease: "back.out(1.6)" }, 0.3);`}
    // shine sweep (one finite pass)
    tl.to("#shine", { xPercent: 180, duration: 1.3, ease: "power2.inOut" }, 1.2);
    tl.to("#shine", { opacity: 0, duration: 0.2 }, 2.4);
    tl.from("#plate-title", { y: 30, opacity: 0, duration: 0.6, ease: "power3.out" }, 1.6);
    tl.from("#plate-sub", { opacity: 0, duration: 0.5 }, 2.0);
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-insignia] wrote ${out}`);
console.log(`[military-insignia] next: npx hyperframes lint && validate && render -o ../../renders/insignia.mp4`);