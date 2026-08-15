// build_satellite.mjs — military-satellite asset generator.
// Earth disc + inclined orbit ellipse + orbiting satellite + sensor footprint.
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import process from "node:process";
import { composition } from "../../_military-shared/composition.mjs";

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : d; };
const project = arg("project", "demo");
const title = arg("title", "侦察卫星组网");
const sat = arg("sat", "高分光学");
const orbit = arg("orbit", "太阳同步");
const tilt = Number(arg("tilt", "24"));
const alt = arg("alt", "600km");
const accent = arg("accent", "#38bdf8");
const duration = Number(arg("duration", "8"));
const BG = "#04070f", FG = "#cfe4ff";

const EX = 1330, EY = 560, ERX = 320, ERY = 320; // Earth center/radius
const ORX = 520, ORY = 210, OCX = EX, OCY = EY; // orbit ellipse radii + center

const html = composition({
  title: `military-satellite :: ${title}`,
  duration,
  bg: BG,
  css: `
    svg#stage{position:absolute;inset:0;width:100%;height:100%}
    #title{position:absolute;left:60px;top:40px;font-size:56px;font-weight:700;letter-spacing:6px}
    #readout{position:absolute;left:60px;top:150px;font-size:28px;color:${FG};letter-spacing:2px;line-height:1.9}
    #readout b{color:${accent}}
  `,
  bodyInner: `
    <svg id="stage" viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice">
      <defs>
        <radialGradient id="earthg" cx="0.4" cy="0.35" r="1">
          <stop offset="0%" stop-color="#2b6ff0"/><stop offset="70%" stop-color="#123a9c"/><stop offset="100%" stop-color="#081c4d"/>
        </radialGradient>
      </defs>
      <circle id="earth" cx="${EX}" cy="${EY}" r="${ERX}" fill="url(#earthg)"/>
      <ellipse id="globe-grid" cx="${EX}" cy="${EY}" rx="${ERX}" ry="${ERY}" fill="none" stroke="${FG}" stroke-width="1.4" opacity="0.4"/>
      <ellipse id="meridians" cx="${EX}" cy="${EY}" rx="${ERX}" ry="${ERY}" fill="none" stroke="${FG}" stroke-width="1" opacity="0.15" stroke-dasharray="4 22"/>
      <g id="orbit-g" transform="rotate(${tilt} ${OCX} ${OCY})">
        <ellipse id="orbit" cx="${OCX}" cy="${OCY}" rx="${ORX}" ry="${ORY}" fill="none" stroke="${accent}" stroke-width="2.4" stroke-dasharray="12 10" opacity="0.6"/>
        <line id="apse-line" x1="${OCX - ORX}" y1="${OCY}" x2="${OCX + ORX}" y2="${OCY}" stroke="${FG}" stroke-width="1" opacity="0.2"/>
      </g>
      <g id="sat">
        <path d="M-30,-14 L-12,-8 L0,-30 L12,-8 L30,-14 L30,14 L-30,14 Z" fill="${FG}" opacity=".95"/>
        <rect x="-8" y="-2" width="16" height="10" rx="2" fill="${accent}"/>
      </g>
      <path id="sensor" d="M0,0 L-70,60 L70,60 Z" fill="${accent}" opacity="0.12"/>
      <ellipse id="footprint" cx="0" cy="60" rx="70" ry="26" fill="${accent}" opacity="0.25"/>
    </svg>
    <div id="title">${title}</div>
    <div id="readout"><b>${sat}</b><br/>轨道：${orbit} · 高度 ${alt}<br/>倾角 ${tilt}°</div>
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    const oc = document.getElementById("orbit-g");
    const sat = document.getElementById("sat");
    const sensor = document.getElementById("sensor");
    const foot = document.getElementById("footprint");
    // attach sensor+footprint to sat group
    sat.appendChild(sensor);
    sat.appendChild(foot);
    sensor.setAttribute("transform", "translate(0 14)");
    foot.setAttribute("transform", "translate(0 78)");
    gsap.set("#title", { opacity: 0, y: -30 });
    tl.to("#title", { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, 0.2);
    tl.from("#readout", { opacity: 0, duration: 0.5 }, 0.8);
    // orbit ellipse draw-on
    {
      const el = document.getElementById("orbit");
      const len = el.getTotalLength ? el.getTotalLength() : 3000;
      el.style.strokeDasharray = "12 10";
      el.style.strokeDashoffset = 0;
    }
    // satellite travels the ellipse in local space (group is rotated by tilt)
    {
      const ORX = ${ORX}, ORY = ${ORY};
      const period = 6.2;
      const p = { t: 0 };
      const place = (t) => {
        const ang = t * Math.PI * 2;
        const x = Math.cos(ang) * ORX, y = Math.sin(ang) * ORY;
        sat.setAttribute("transform", "translate(" + x.toFixed(1) + " " + y.toFixed(1) + ") rotate(" + (ang * 180 / Math.PI) + ")");
      };
      tl.fromTo("#sat", { opacity: 1 }, { opacity: 1, duration: 0.05 }, 0.6);
      tl.to(p, { t: 1, duration: period, ease: "none", onUpdate() { place(p.t); } }, 0.6);
    }
    // orbit pulse
    tl.fromTo("#orbit", { opacity: 0.6 }, { opacity: 1, duration: 0.8, yoyo: true, repeat: 2 }, 0.6);
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-satellite] wrote ${out}`);
console.log(`[military-satellite] next: npx hyperframes lint && validate && render -o ../../renders/satellite.mp4`);