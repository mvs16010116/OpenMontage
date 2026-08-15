// build_missile.mjs — military-missile asset generator.
// Launch profile by type + ballistic arc + traveling missile marker + impact.
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import process from "node:process";
import { composition } from "../../_military-shared/composition.mjs";

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : d; };
const project = arg("project", "demo");
const title = arg("title", "弹道导弹试射");
const range = arg("range", "2400km");
const apogee = arg("apogee", "800km");
const type = arg("type", "icbm");
const accent = arg("accent", "#fbbf24");
const duration = Number(arg("duration", "8"));
const BG = "#0a0712", FG = "#ffe9c7";

// control points by type
const C = {
  icbm: { s: [250, 900], c1: [420, 420], c2: [1280, 140], e: [1600, 760], launcher: [210, 830] },
  sam: { s: [360, 900], c1: [820, 520], c2: [1080, 300], e: [1500, 700], launcher: [300, 830] },
  rocket: { s: [900, 900], c1: [900, 380], c2: [900, 160], e: [900, 40], launcher: [860, 830] },
}[type] || {};

const guide = `M${C.s[0]},${C.s[1]} C${C.c1[0]},${C.c1[1]} ${C.c2[0]},${C.c2[1]} ${C.e[0]},${C.e[1]}`;

const phases = type === "rocket"
  ? [{ t: 0.3, l: "点火升空" }, { t: 0.6, l: "三级分离" }]
  : [{ t: 0.15, l: "点火" }, { t: 0.42, l: "助推" }, { t: 0.7, l: "中段飞行" }, { t: 0.9, l: "末段" }];

const phaseHTML = phases.map((p, i) => `<div id="phase-${i}" class="phase">${p.l}</div>`).join("");

const html = composition({
  title: `military-missile :: ${title}`,
  duration,
  bg: BG,
  css: `
    svg#stage{position:absolute;inset:0;width:100%;height:100%}
    #title{position:absolute;left:60px;top:40px;font-size:56px;font-weight:700;letter-spacing:6px}
    #range-card{position:absolute;left:120px;bottom:90px;font-size:38px;color:${accent};letter-spacing:2px}
    #apogee-tag{position:absolute;left:120px;bottom:150px;font-size:26px;color:${FG};opacity:.7}
    .phase{position:absolute;right:90px;bottom:110px;font-size:30px;color:${FG};letter-spacing:2px;opacity:0}
    .phase:nth-child(n+2){bottom:${150}px}
  `,
  bodyInner: `
    <svg id="stage" viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice">
      <path id="guide" d="${guide}" fill="none" stroke="${accent}" stroke-width="3" stroke-dasharray="8 10" opacity=".55"/>
      <g id="launcher" transform="translate(${C.launcher[0]},${C.launcher[1]})">
        <rect x="-26" y="-60" width="52" height="110" rx="6" fill="${FG}" opacity=".9"/>
        <path d="M-14,-60 L14,-60 L8,-120 L-8,-120 Z" fill="${FG}" opacity=".9"/>
      </g>
      <g id="rocket" transform="translate(${C.s[0]},${C.s[1]})" opacity="0">
        <rect x="-12" y="-34" width="24" height="56" rx="4" fill="${accent}"/>
        <path d="M0,-46 L9,-30 L-9,-30 Z" fill="${accent}"/>
        <path d="M-10,22 L-20,46 L20,46 L10,22 Z" fill="#fff2d0"/>
      </g>
      <circle id="flash" cx="${C.e[0]}" cy="${C.e[1]}" r="20" fill="none" stroke="${accent}" stroke-width="6" opacity="0"/>
    </svg>
    <div id="title">${title}</div>
    <div id="range-card">射程 ${range}</div>
    <div id="apogee-tag">最大高度 ${apogee}</div>
    ${phaseHTML}
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    gsap.set("#title", { opacity: 0, y: -30 });
    tl.to("#title", { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 0.2);
    tl.from("#launcher", { scale: 0, opacity: 0, transformOrigin: "50% 100%", duration: 0.5, ease: "back.out(1.5)" }, 0.5);
    tl.from("#apogee-tag", { opacity: 0, duration: 0.4 }, 0.9);
    // guide draw-on
    {
      const g = document.getElementById("guide");
      const L = g.getTotalLength();
      g.style.strokeDasharray = L + " " + L;
      g.style.strokeDashoffset = L;
      tl.to(g, { strokeDashoffset: 0, duration: 1.6, ease: "power2.inOut" }, 0.6);
    }
    // rocket travels the bezier
    {
      const S = [${C.s[0]},${C.s[1]}], C1 = [${C.c1[0]},${C.c1[1]}], C2 = [${C.c2[0]},${C.c2[1]}], E = [${C.e[0]},${C.e[1]}];
      const rk = document.getElementById("rocket");
      const p = { t: 0 };
      const place = (t) => {
        const mt = 1 - t;
        const x = (mt*mt*mt)*S[0] + 3*(mt*mt*t)*C1[0] + 3*(mt*t*t)*C2[0] + (t*t*t)*E[0];
        const y = (mt*mt*mt)*S[1] + 3*(mt*mt*t)*C1[1] + 3*(mt*t*t)*C2[1] + (t*t*t)*E[1];
        const ang = Math.atan2(y - (S[1] + (E[1] - S[1]) * t), x - (S[0] + (E[0] - S[0]) * t));
        rk.setAttribute("transform", "translate(" + x.toFixed(1) + " " + y.toFixed(1) + ") rotate(" + (ang * 180 / Math.PI) + ")");
      };
      tl.fromTo("#rocket", { opacity: 1 }, { opacity: 1, duration: 0.05 }, 0.7);
      tl.to(p, { t: 1, duration: 4.4, ease: "power1.inOut", onUpdate() { place(p.t); } }, 0.7);
    }
    // phase labels
    ${phases.map((p, i) => `tl.to("#phase-${i}", { opacity: 1, duration: 0.3 }, ${p.t * 5.1}); tl.to("#phase-${i}", { opacity: 0, duration: 0.3 }, ${p.t * 5.1 + 0.9});`).join("\n    ")}
    // impact flash + range card
    tl.fromTo("#flash", { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1.8, transformOrigin: "50% 50%", duration: 0.5, ease: "power2.out" }, 5.3);
    tl.to("#flash", { opacity: 0, duration: 0.4 }, 5.8);
    tl.from("#range-card", { opacity: 0, y: 24, duration: 0.5 }, 5.4);
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-missile] wrote ${out}`);
console.log(`[military-missile] next: npx hyperframes lint && validate && render -o ../../renders/missile.mp4`);