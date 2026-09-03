// build_data_viz_vertical.mjs — vertical (1080x1920) photo-bg data-viz generator.
// Preserves the delivered vertical photo-background look (like build_vertical.mjs),
// and fixes the timeline keyword labels:
//   - timeline point "2023-10-07:袭击" parses date="2023-10-07" label="袭击"
//     (the landscape build_data_viz.mjs turns the date into "0 年" via +t||0 — bug)
//   - each timeline label is rendered as a CENTERED chip with an amber #fbbf24
//     background + dark text (user request), instead of raw inline text that overlapped.
// Usage: node build_data_viz_vertical.mjs --scene <id>
import { join } from "node:path";
import { mkdirSync, writeFileSync } from "node:fs";
import process from "node:process";

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : d; };
const sceneId = arg("scene", "scene_section_01_3");

// per-scene config: title, type, timeline/bars points, kpi, duration, img
const SCENES = {
  "scene_section_01_3": {
    title: "报复优先级 · 彻底钉死",
    type: "timeline",
    timeline: [["2023-10-07", "袭击"], ["2026-08", "目标换芯"]],
    kpi: "快3年",
    dur: 11.333,
    img: "scene_section_01_3",
  },
  "scene_section_05_2": {
    title: "临界点前 · 落地承诺",
    type: "timeline",
    timeline: [["外部压力0临界", "窗口"], ["承诺落地", "必须"]],
    kpi: "时间压力",
    dur: 5.8,
    img: "scene_section_05_2",
  },
  "scene_section_07_1": {
    title: "历史先例：复仇式清算",
    type: "timeline",
    timeline: [["上世纪末", "复仇优先"], ["如今", "核心承诺"]],
    kpi: "似曾相识",
    dur: 6.5,
    img: "scene_section_07_1",
  },
};
const cfg = SCENES[sceneId];
if (!cfg) { console.error(`[data-viz-vertical] unknown scene: ${sceneId}`); process.exit(1); }

const dur = cfg.dur.toFixed(3);
const ACCENT = "#fbbf24";
const CHIP_TEXT = "#070b12"; // dark text on amber chip

// vertical center animation origin (video is 1920 tall; chips sit around y~46-56%)
const ROW_OFFSETS = ["calc(50% - 150px)", "calc(50% + 45px)"]; // 2 timeline rows, centered
const tlRowHTML = (cfg.type === "timeline")
  ? cfg.timeline.map((e, i) => `
      <div class="chiprow" id="trow-${i}" style="top:${ROW_OFFSETS[i % ROW_OFFSETS.length]}">
        <span class="chip" id="chip-${i}"><span class="cd">${e[0]}</span><span class="cv">${e[1]}</span></span>
      </div>`).join("\n    ")
  : "";

const html = `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>military-data-viz :: ${sceneId}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      @font-face{font-family:"Microsoft YaHei";src:local('Microsoft YaHei');font-display:swap}
      @font-face{font-family:"PingFang SC";src:local('PingFang SC');font-display:swap}
      body{margin:0;background:#05070d;color:#fff;font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif;overflow:hidden}
      #root{position:relative;width:1080px;height:1920px;overflow:hidden;background:#05070d}
      .clip{position:absolute;inset:0;overflow:hidden}
      #bgimg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;will-change:transform}
      #shade{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(5,7,13,.18) 0%,rgba(5,7,13,.4) 40%,rgba(5,7,13,.82) 82%,rgba(5,7,13,.94) 100%)}
      bar{display:block}
      #title{position:absolute;left:60px;right:60px;top:9%;text-align:center;font-size:64px;font-weight:700;letter-spacing:5px;color:#fff3d6;line-height:1.4}
      #rail{position:absolute;left:50%;top:20%;bottom:26%;border-left:4px dashed rgba(255,255,255,.25)}
      #kpi{position:absolute;left:0;right:0;bottom:7%;text-align:center;font-size:40px;color:${ACCENT};letter-spacing:3px;font-weight:700}
      .chiprow{position:absolute;left:0;right:0;display:flex;justify-content:center;opacity:0}
      .chip{display:inline-flex;align-items:center;background:${ACCENT};color:${CHIP_TEXT};border-radius:14px;padding:18px 30px;font-size:42px;font-weight:700;letter-spacing:1px;box-shadow:0 6px 18px rgba(0,0,0,.45)}
      .cd{margin-right:16px}
      .cv{font-weight:700}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-width="1080" data-height="1920" data-duration="${dur}">
      <section id="scene" class="clip" data-start="0" data-duration="${dur}" data-track-index="1">
        <img id="bgimg" src="assets/images/${cfg.img}.jpg" alt="" />
        <div id="shade"></div>
        <div id="title">${cfg.title}</div>
        ${cfg.type === "timeline" ? `<div id="rail"></div>` : ""}
        ${tlRowHTML}
        ${cfg.kpi ? `<div id="kpi">${cfg.kpi}</div>` : ""}
      </section>
    </div>
    <script>
      window.__timelines = window.__timelines || {};
      const tl = gsap.timeline({ paused: true });
      gsap.set("#bgimg",{scale:1.0});
      tl.to("#bgimg",{scale:1.08,duration:${dur},ease:"none"},0);
      tl.from("#title", { y: -40, opacity: 0, duration: 0.6, ease: "power3.out" }, 0.2);
      ${cfg.type === "timeline" ? cfg.timeline.map((_, i) => `tl.fromTo("#trow-${i}",{opacity:0,y:24,scale:0.9},{opacity:1,y:0,scale:1,duration:0.45,ease:"back.out(1.6)"},${0.9 + i * 0.55});`).join("\n      ") : ""}
      ${cfg.kpi ? `tl.from("#kpi", { opacity: 0, y: 20, duration: 0.5 }, ${0.9 + cfg.timeline.length * 0.55});` : ""}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
`;

const out = join(process.cwd(), "projects", "junzheng-gaza-pursuit", "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[data-viz-vertical] wrote ${out} (${sceneId}, ${dur}s)`);
