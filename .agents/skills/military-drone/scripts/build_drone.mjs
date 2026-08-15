// build_drone.mjs — military-drone asset generator.
// Deterministic HyperFrames composition: quadcopter line-art + rotor spin +
// mission path trace + optional swarm + HUD readouts.
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import process from "node:process";
import { composition, mulberry32 } from "../../_military-shared/composition.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : d; };
const project = arg("project", "demo");
const name = arg("name", "察打一体无人机");
const mode = arg("mode", "flight");
const alt = arg("alt", "5500m");
const speed = arg("speed", "180km/h");
const accent = arg("accent", "#22d3ee");
const formation = Number(arg("formation", "1"));
const duration = Number(arg("duration", "8"));
const rgba = (hex, a) => { const n = parseInt(hex.slice(1), 16); return `rgba(${n>>16&255},${n>>8&255},${n&255},${a})`; };
const rng = mulberry32(4221);
const FG = "#d6e4ff", BG = "#060a14";
const rope = (d) => `M${d[0][0]*1920},${d[0][1]*1080} L${d[1][0]*1920},${d[1][1]*1080} L${d[2][0]*1920},${d[2][1]*1080}`;

// waypoints normalized 0-1
const wpRaw = (arg("path") || "0.25,0.70 0.45,0.42 0.65,0.55 0.82,0.30")
  .trim().split(/\s+/).map((p) => p.split(",").map(Number));
const P = wpRaw.map(([x, y]) => [x * 1920, y * 1080]);
const dHash = Math.floor(rng() * 1e9).toString(16);

// keep wingmen within bounds deterministically
const wing = [];
for (let i = 1; i < formation; i++) wing.push({ dx: (i % 2 ? 1 : -1) * (90 + (i * 37) % 120), dy: 70 + (i * 53) % 160 });

const droneSvg = (id, cls) => `
  <g id="${id}" class="${cls}">
    <path d="M-70,0 A70,70 0 1 1 70,0 A70,70 0 1 1 -70,0" fill="none" stroke="${accent}" stroke-width="2" stroke-dasharray="16 10" opacity="0.9"/>
    <path d="M-25,-25 L-95,-55 M25,-25 L95,-55 M-25,25 L-95,55 M25,25 L95,55" stroke="${FG}" stroke-width="7" stroke-linecap="round"/>
    <circle cx="-95" cy="-55" r="26" fill="none" stroke="${FG}" stroke-width="5"/>
    <circle cx="95" cy="-55" r="26" fill="none" stroke="${FG}" stroke-width="5"/>
    <circle cx="-95" cy="55" r="26" fill="none" stroke="${FG}" stroke-width="5"/>
    <circle cx="95" cy="55" r="26" fill="none" stroke="${FG}" stroke-width="5"/>
    <rect x="-28" y="-16" width="56" height="32" rx="10" fill="${FG}"/>
    <circle cx="14" cy="0" r="7" fill="${accent}"/>
  </g>`;

// waypoint markers
const marker = (i, [x, y]) => `<circle cx="${x}" cy="${y}" r="9" fill="none" stroke="${accent}" stroke-width="3"/><text x="${x+16}" y="${y-14}" font-size="30" fill="${FG}">${i+1}</text>`;

const wingSvgs = wing.map((w, i) => droneSvg(`wing-${i}`, "wing")).join("");
const markers = P.map((p, i) => marker(i, p)).join("");

const html = composition({
  title: `military-drone :: ${name}`,
  duration,
  bg: BG,
  css: `
    svg#stage{position:absolute;inset:0;width:100%;height:100%}
    #hud{position:absolute;left:48px;top:40px;font-size:28px;color:${FG};letter-spacing:2px}
    #hud b{color:${accent}}
    #name-tag{position:absolute;left:48px;bottom:44px;font-size:30px;color:${FG};opacity:.85;letter-spacing:3px}
    .dot{position:absolute;width:9px;height:9px;background:${accent};border-radius:50%}
    #d1{left:262px;top:96px}#d2{left:354px;top:96px}#d3{left:446px;top:96px}
  `,
  bodyInner: `
    <svg id="stage" viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice">
      <path id="trace" d="${rope([P[0], P[1], P[2]])} L${P[3][0]},${P[3][1]}" fill="none" stroke="${rgba(accent,0.35)}" stroke-width="4" stroke-dasharray="20 12"/>
      ${markers}
      ${droneSvg("lead", "drone")}
      ${wingSvgs}
    </svg>
    <div id="name-tag">${name} · ${mode === "swarm" ? `×${formation} 编队` : "单机侦察"}</div>
    <div id="hud">高度 <b>${alt}</b>　速度 <b>${speed}</b></div>
    <div class="dot" id="d1"></div><div class="dot" id="d2"></div><div class="dot" id="d3"></div>
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    const stage = document.getElementById("stage");
    gsap.set(".dot", { opacity: 0 });

    // path draw-on
    const trace = document.getElementById("trace");
    const len = trace.getTotalLength();
    trace.style.strokeDasharray = len + " " + len;
    trace.style.strokeDashoffset = len;
    tl.to(trace, { strokeDashoffset: 0, duration: 2.2, ease: "power2.inOut" }, 0.4);

    // lead drone follows the polyline: animate along path via GSAP MotionPath-style manual placement
    // (deterministic: proxy tween drives x/y along precomputed waypoint segments)
    const lead = document.getElementById("lead");
    const seg = (i) => { const a = P[i % P.length], b = P[(i + 1) % P.length]; return { ax: a[0], ay: a[1], bx: b[0], by: b[1] }; };
    const segs = P.map((_, i) => seg(i));
    const proxy = { s: 0 };
    const place = (el, s) => {
      const f = s * segs.length; const i = Math.min(Math.floor(f), segs.length - 1);
      const t = f - i; const g = segs[i]; const ex = g.ax + (g.bx - g.ax) * t, ey = g.ay + (g.by - g.ay) * t;
      el.setAttribute("transform", "translate(" + ex + " " + ey + ") rotate(12)");
    };
    gsap.set(["#wing-0"], { opacity: 0 });
    tl.to(proxy, {
      s: 1, duration: 5.2, ease: "none",
      onUpdate() { place(lead, proxy.s); },
    }, 0.4);
    tl.fromTo("#lead", { opacity: 1 }, { opacity: 1, duration: 0.1 }, 0.4);

    // wingmen: same path, deterministic offsets (lead already placed; wingmen lag via timeline dup tween)
    ${wing.map((w, i) => `
    {
      const el = document.getElementById("wing-${i}");
      const wp = { s: 0.18 };
      tl.to(wp, {
        s: 1, duration: 5.2, ease: "none",
        onUpdate() { place(el, Math.min(1, wp.s)); },
      }, 0.4 + ${i * 0.12});
    }`).join("\n    ")}

    // rotor spin for lead + wingmen (finite repeats, then stop)
    tl.fromTo("#lead circle", { rotation: 0 }, { rotation: 360, duration: 0.4, ease: "none", repeat: Math.max(0, Math.floor(6.2 / 0.4)) }, 0.4);

    // HUD dots
    tl.to(".dot", { opacity: 0.9, duration: 0.001 }, 0);
    tl.to("#d1", { opacity: 0, duration: 0.1 }, 2.2);
    tl.to("#d2", { opacity: 0, duration: 0.1 }, 3.6);
    tl.to("#d3", { opacity: 0, duration: 0.1 }, 5.0);
    tl.from("#name-tag", { y: 50, opacity: 0, duration: 0.6, ease: "power3.out" }, 0.2);
    window.__timelines["main"] = tl;
  `,
});

const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-drone] wrote ${out}`);
console.log(`[military-drone] next: npx hyperframes lint && validate && render -o ../../renders/drone.mp4`);