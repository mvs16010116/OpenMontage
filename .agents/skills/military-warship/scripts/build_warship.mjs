// build_warship.mjs — military-warship asset generator.
// Writes a deterministic HyperFrames composition (vector warship + sea + radar
// sweep + stat cards) to ./projects/<project>/hyperframes/index.html.
//
//   node build_warship.mjs --project demo --name "驱逐舰" --hull "173 号" \
//     --stats "满载排水量:7500吨" "航速:32节" "舰员:280人" --duration 8
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import process from "node:process";
import { mkdirSync, writeFileSync } from "node:fs";
import { composition, mulberry32 } from "../../_military-shared/composition.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));

function arg(name, dflt) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : dflt;
}
function stats() {
  const out = [];
  const i = process.argv.indexOf("--stats");
  if (i < 0) return out;
  for (let j = i + 1; j < process.argv.length; j++) {
    if (process.argv[j].startsWith("--")) break;
    const [label, value] = process.argv[j].split(":");
    if (label) out.push({ label, value: value || "" });
  }
  return out;
}

const project = arg("project", "demo") || "demo";
const name = arg("name", "远洋驱逐舰");
const hull = arg("hull", "173 号");
const duration = Number(arg("duration", "8"));
const accent = arg("accent", "#38bdf8");
const palette = arg("palette", "dark");
const FG = palette === "bright" ? "#0b1220" : "#c7d4ff";
const BG = palette === "bright" ? "#dbe7ff" : "#05070d";
const rng = mulberry32(20260813);

// --- sea wave layer helper (deterministic per-frame via proxy tween offset) ---
function waveLayer(id, baseY, amp, freq, phase, alpha) {
  const pts = [];
  for (let x = 0; x <= 1920; x += 24) pts.push(`${x},${baseY + Math.sin(x * freq * 0.0016 + phase) * amp}`);
  return {
    id,
    path: `M0,${baseY} L${pts.map((p) => p.split(",")[0] + " " + p.split(",")[1]).join(" L")} L1920,1080 L0,1080 Z`,
    baseY,
    amp,
    phase,
    alpha,
  };
}
const waves = [
  waveLayer("wave-a", 780, 26, 1.0, 0.0, 0.35),
  waveLayer("wave-b", 800, 34, 1.4, 2.1, 0.3),
  waveLayer("wave-c", 830, 40, 1.8, 4.2, 0.25),
];

// --- destroyer silhouette (simple but readable line-art) ---
const ship = `
  <path d="M320,760 L520,790 L980,808 L1460,782 L1640,760 Z" fill="${FG}" opacity="0.9"/>
  <path d="M760,720 L880,700 L980,700 L1100,720 Z" fill="${FG}" opacity="0.95"/>
  <path d="M980,700 L1040,640 L1160,680 Z" fill="${FG}" opacity="0.9"/>
  <path d="M1040,640 L1080,560 L1160,600 L1160,680 Z" fill="${FG}" opacity="0.95"/>
  <path d="M1080,560 L1110,470 L1180,540 Z" fill="${accent}" opacity="0.9"/>
  <rect x="1150" y="420" width="10" height="90" fill="${accent}"/>
  <rect x="1136" y="400" width="38" height="8" fill="${accent}"/>
  <circle cx="1155" cy="404" r="6" fill="${accent}"/>
  <path d="M560,730 L720,700 L760,700 L760,720 Z" fill="${FG}" opacity="0.9"/>
  <rect x="520" y="600" width="40" height="120" fill="${FG}" opacity="0.9"/>
  <circle cx="540" cy="596" r="26" fill="none" stroke="${accent}" stroke-width="4"/>
`;

const statData = stats();
const statBoxes = statData
  .map((s, i) => {
    const x = 150 + i * 560;
    return `
  <div id="stat-${i}" class="stat" style="left:${x}px;top:900px">
    <div class="stat-label">${s.label}</div>
    <div class="stat-value" data-target="${parseFloat(s.value) || 0}" data-suffix="${s.value.replace(/[0-9.+\-]/g, "").trim()}">0</div>
  </div>`;
  })
  .join("");

const html = composition({
  title: `military-warship :: ${name}`,
  duration,
  bg: BG,
  css: `
    .clip{display:block}
    #title-card{position:absolute;left:60px;top:48px}
    #ship-name{font-size:72px;font-weight:700;letter-spacing:6px}
    #hull-no{font-size:30px;color:${accent};margin-top:8px;letter-spacing:3px}
    #watermark{position:absolute;left:60px;bottom:40px;font-size:20px;color:#ffffff;opacity:1;text-shadow:0 0 6px rgba(0,0,0,0.8)}
    .stat{position:absolute;width:480px;text-align:left}
    .stat-label{font-size:26px;color:${FG};opacity:.7;letter-spacing:2px}
    .stat-value{font-size:54px;font-weight:700;color:#e9f6ff;margin-top:4px}
    svg{position:absolute;inset:0;width:100%;height:100%}
  `,
  bodyInner: `
    <svg id="sea-svg" viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice" data-layout-allow-overflow>
      ${waves.map((w) => `<path id="${w.id}" d="${w.path}" fill="${accent}" opacity="${w.alpha}"/>`).join("\n      ")}
    </svg>
    <svg id="ship-svg" viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid meet" data-layout-allow-overflow>
      ${ship}
    </svg>
    <div id="title-card">
      <div id="ship-name">${name}</div>
      <div id="hull-no">${hull}</div>
    </div>
    ${statBoxes}
    <div id="watermark">OpenMontage · 军事素材 · military-warship</div>
  `,
  script: `
    const tl = gsap.timeline({ paused: true });

    // radar sweep (finite, half-turn each loop of the clip)
    const sweep = document.createElementNS("http://www.w3.org/2000/svg", "path");
    sweep.setAttribute("d", "M540,596 L620,460 L650,620 Z");
    sweep.setAttribute("fill", "${accent}");
    sweep.setAttribute("opacity", "0.25");
    document.querySelector("#ship-svg").appendChild(sweep);
    tl.fromTo(sweep, { rotation: -60, svgOrigin: "540 596" }, { rotation: 260, duration: ${Math.min(6, duration - 1)} }, 0.6);

    // title + hull reveal
    tl.from("#ship-name", { y: 60, opacity: 0, duration: 0.7, ease: "power3.out" }, 0.4);
    tl.from("#hull-no", { x: -30, opacity: 0, duration: 0.6, ease: "power3.out" }, 0.9);
    tl.to("#watermark", { opacity: 1, duration: 0.5 }, 1.2);

    // sea bob + ship float: gentle deterministic motion (allowlist y/rotation, finite)
    tl.to("#sea-svg", { y: 18, duration: 1.8, yoyo: true, repeat: 3, ease: "sine.inOut" }, 0.4);
    tl.to("#ship-svg", { y: -8, rotation: 0.6, duration: 1.6, yoyo: true, repeat: 3, ease: "sine.inOut" }, 0.6);

    // stat count-up via proxy tween onUpdate
    ${statData
      .map((s, i) => {
        const val = Number.parseFloat(s.value) || 0;
        return `
    {
      const el = document.querySelector("#stat-${i} .stat-value");
      const proxy = { v: 0 };
      tl.to(proxy, {
        v: ${val}, duration: 1.2, ease: "power2.out",
        onUpdate() { el.textContent = Math.round(proxy.v); },
      }, 2.2 + ${i * 0.25});
    }`;
      })
      .join("\n    ")}
    tl.to("#ship-name", { duration: 0.4 }, ${Math.max(3.4, 2.2 + statData.length * 0.25).toFixed(2)});
    window.__timelines["main"] = tl;
  `,
});

// write output relative to cwd (like bake-basemap.mjs)
const out = join(process.cwd(), "projects", project, "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[military-warship] wrote ${out}`);
console.log(`[military-warship] next: cd projects/${project}/hyperframes && npx hyperframes lint`);
console.log(`  npx hyperframes validate && npx hyperframes render . --skill=military-warship -o ../../renders/warship.mp4`);