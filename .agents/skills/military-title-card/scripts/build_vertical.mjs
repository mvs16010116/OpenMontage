// build_vertical.mjs (reconstructed) — vertical title-card asset generator.
// Reproduces the delivered 1080x1920 vertical layout (from committed index.html
// for scene_section_02_1) for every military-title-card scene, with the
// breathing textShadow glow on #kwtag REMOVED (bug fix for comma-tag overlap).
// Usage: node build_vertical.mjs --scene <scene_id>
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";
import process from "node:process";

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : d; };
const sceneId = arg("scene", "scene_section_02_1");

// per-scene config: title, tag (comma -> separate .t items), duration (actual baked), img
const SCENES = {
  "scene_opener":                { title: "说出来你敢信？",              tag: "以军目标已换芯",      dur: 3.0,    img: "scene_opener" },
  "scene_section_01_1":          { title: "侯哥军情 · 目标已换芯",      tag: "侯哥军情,目标已换芯", dur: 2.0,    img: "scene_section_01_1" },
  "scene_section_01_2":          { title: "说出来你敢信？核心目标已换",  tag: "核心目标,已换芯",     dur: 12.7,   img: "scene_section_01_2" },
  "scene_section_02_1":          { title: "「摧毁哈马斯」＝幌子",         tag: "核心,目标已换芯",      dur: 10.467, img: "scene_section_02_1" },
  "scene_section_02_2":          { title: "目标收缩 · 人头清账",        tag: "目标收缩,人头清账",   dur: 12.9,   img: "scene_section_02_2" },
  "scene_section_02_3":          { title: "零弹性 · 半分折中空间都没有", tag: "零弹性,折中空间",     dur: 2.7,    img: "scene_section_02_3" },
  "scene_section_chapter_1":     { title: "第一部分 · 目标换芯",        tag: "章节",               dur: 2.5,    img: "scene_section_chapter_1" },
  "scene_section_03_1":          { title: "政治焦虑 · 无弹性答卷",      tag: "政治焦虑,无弹性答卷", dur: 7.4,    img: "scene_section_03_1" },
  "scene_section_04_2":          { title: "情报响应 · 前所未有",        tag: "情报响应,前所未有",   dur: 5.333,  img: "scene_section_04_2" },
  "scene_section_04_3":          { title: "潜台词 · 更值得咂摸",        tag: "潜台词,值得咂摸",     dur: 2.7,    img: "scene_section_04_3" },
  "scene_section_chapter_2":     { title: "第二部分 · 代价与潜台词",    tag: "章节",               dur: 2.5,    img: "scene_section_chapter_2" },
  "scene_section_05_1":          { title: "第一 · 国际窗口留不了多久",  tag: "国际窗口,留不了多久", dur: 7.1,    img: "scene_section_05_1" },
  "scene_section_06_1":          { title: "第二 · 单一任务优先级",      tag: "单一任务,优先级",     dur: 10.467, img: "scene_section_06_1" },
  "scene_section_06_2":          { title: "其他方向 · 全部让路",        tag: "其他方向,全部让路",   dur: 7.333,  img: "scene_section_06_2" },
  "scene_section_chapter_3":     { title: "第三部分 · 历史先例与收尾",  tag: "章节",               dur: 2.5,    img: "scene_section_chapter_3" },
  "scene_section_07_2":          { title: "泥潭 · 看不到头",            tag: "泥潭,看不到头",       dur: 2.8,    img: "scene_section_07_2" },
  "scene_section_08_1":          { title: "问题：私人恩怨式清算？",      tag: "私人恩怨,清算",       dur: 8.9,    img: "scene_section_08_1" },
  "scene_section_08_2":          { title: "没边界的任务 · 如何收尾",    tag: "没边界,如何收尾",     dur: 4.467,  img: "scene_section_08_2" },
  "scene_section_08_3":          { title: "评论区聊聊你的判断",          tag: "评论区,聊聊判断",     dur: 3.133,  img: "scene_section_08_3" },
};
const cfg = SCENES[sceneId];
if (!cfg) { console.error(`[build_vertical] unknown scene: ${sceneId}`); process.exit(1); }

const dur = cfg.dur.toFixed(3);
const chars = cfg.title.split("");
const wordHTML = chars.map((ch, i) => `<span class="w" id="w-${i}">${ch === " " ? "&nbsp;" : ch === "·" ? "·" : ch}</span>`).join("");
const wList = JSON.stringify(chars.map((_, i) => "#w-" + i));
const tagParts = cfg.tag.split(",");
const tagHTML = tagParts.map((t) => `<span class="t">${t}</span>`).join(",");

const html = `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>${sceneId} :: gaza</title>
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
      #headline{position:absolute;left:60px;right:60px;top:30%;text-align:center;font-size:85.71428571428571px;font-weight:700;letter-spacing:4px;color:#fff3d6;line-height:1.5;will-change:transform;text-shadow:none}
      #sweep{position:absolute;left:-200px;top:28%;width:200px;height:137.14285714285714px;background:linear-gradient(90deg,transparent,#fbbf2433,transparent);opacity:0;will-change:transform;pointer-events:none}
      #kwbar{position:absolute;left:50%;top:56%;width:420px;height:10px;margin-left:-210px;background:#fbbf24;transform-origin:left}
      #kwtag{position:absolute;left:60px;right:60px;top:60%;text-align:center;font-size:40px;font-weight:600;color:#fbbf24;letter-spacing:6px;text-shadow:none}
      .t{margin:0 14px}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-width="1080" data-height="1920" data-duration="${dur}">
      <section id="scene" class="clip" data-start="0" data-duration="${dur}" data-track-index="1">
        <img id="bgimg" src="assets/images/${cfg.img}.jpg" alt="" />
        <div id="shade"></div>
        <div id="headline">${wordHTML}</div>
        <div id="sweep"></div>
        <div id="kwbar"></div>
        <div id="kwtag">${tagHTML}</div>
      </section>
    </div>
    <script>
      window.__timelines = window.__timelines || {};
      const tl = gsap.timeline({ paused: true });
      gsap.set("#bgimg",{scale:1.0});
      tl.to("#bgimg",{scale:1.08,duration:${dur},ease:"none"},0);
      gsap.set(${wList}, {y:-90,opacity:0,scale:0.92,filter:"blur(4px)"});
      tl.to(${wList}, {y:0,opacity:1,scale:1,filter:"blur(0px)",duration:0.8,ease:"back.out(2.2)",stagger:0.05}, 0.3);
      gsap.set("#sweep",{opacity:0.5});
      tl.fromTo("#sweep",{x:-200,opacity:0.5},{x:1280,opacity:0,duration:0.8,ease:"power2.inOut"}, 1.10);
      tl.fromTo("#kwbar",{scaleX:0},{scaleX:1,duration:0.8,ease:"power2.inOut"}, 1.00);
      gsap.set("#kwtag",{y:20,opacity:0});
      tl.to("#kwtag",{y:0,opacity:1,letterSpacing:"6px",duration:0.6,ease:"back.out(1.4)"}, 1.50);
      tl.to("#headline",{y:-6,duration:3.92,ease:"sine.inOut",delay:2.60});
      tl.to("#headline",{y:6,duration:3.92,ease:"sine.inOut"});
      tl.to("#headline",{textShadow:"0 0 18px #fbbf24",duration:1.1,ease:"sine.inOut",yoyo:true,repeat:8}, 0.90);
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
`;

const out = join(process.cwd(), "projects", process.env.PROJECT || "junzheng-gaza-pursuit", "hyperframes", "index.html");
mkdirSync(join(out, ".."), { recursive: true });
writeFileSync(out, html, "utf8");
console.log(`[build_vertical] wrote ${out} (${sceneId}, ${dur}s)`);
