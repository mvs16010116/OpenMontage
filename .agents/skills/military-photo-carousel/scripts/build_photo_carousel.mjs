// build_photo_carousel.mjs — military-photo-carousel asset generator.
// Landscape 1920x1080. Keyword-relevant Pexels photo carousel as background
// (crossfade + Ken Burns) with dark gradient mask and title-card foreground.
//
// Deterministic HyperFrames composition:
//   --project=<name>          project dir name under projects/
//   --title=<headline>        big headline text (Chinese)
//   --keyword=<tag>           keyword tag under headline (optional)
//   --number=<val>:<label>    count-up number + label (optional)
//   --lower=<lower third>     lower-third text (optional)
//   --images=<a.jpg;b.jpg;c.jpg>  carousel image paths (relative to project or
//                                 absolute). Semicolon separated.
//   --duration=<sec>          scene duration
//   --accent=<hex>            accent color, default #fbbf24
//   --no-carousel             skip images -> pure dark card (section fallback)
//
// Reads images listed in --images; each becomes a background <img> stacked in
// z-order. Crossfade 0.6s between neighbours, Ken Burns scale 1->1.08 with
// alternating origin. Foreground reuses title-card style.
import { dirname, join, resolve, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync, copyFileSync, existsSync } from "node:fs";
import process from "node:process";
import { composition } from "../../_military-shared/composition.mjs";

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i >= 0 && process.argv[i + 1] !== undefined ? process.argv[i + 1] : d; };
const project = arg("project", "demo");
const title = arg("title", "新时代军事战略方针");
const keyword = arg("keyword", "");
const lower = arg("lower", "");
const accent = arg("accent", "#fbbf24");
const duration = Number(arg("duration", "6"));
const imagesRaw = arg("images", "");
const noCarousel = process.argv.indexOf("--no-carousel") >= 0;
const BG = "#070b12", FG = "#fff3d6";
const numArg = arg("number", "");
const [numTarget, numLabel] = numArg.split(":");
const hasNum = numArg !== "";

// hex accent (e.g. #fbbf24) -> rgba() string at given alpha, for chip glow params
const accentRgba = (alpha) => {
  const hex = accent.replace("#", "");
  const n = parseInt(hex, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
};

// image paths: semicolon separated. Local images are copied under
// hyperframes/assets/images/<slug>/ so the renderer (root=hyperframes/) resolves
// the relative src reliably. Bare http URLs pass through unchanged.
const projectRoot = resolve(process.cwd(), "projects", project);
const hfAssetsDir = resolve(projectRoot, "hyperframes", "assets", "images");
const slug = arg("slug", basename(project));
const imagePaths = noCarousel || imagesRaw === ""
  ? []
  : imagesRaw.split(";").map((p) => p.trim()).filter(Boolean).map((p) => {
      if (p.startsWith("http")) return p;
      const srcPath = resolve(process.cwd(), "projects", project, p);
      const destName = `${basename(p)}`;
      const dest = join(hfAssetsDir, slug, destName);
      if (existsSync(srcPath)) {
        mkdirSync(dirname(dest), { recursive: true });
        copyFileSync(srcPath, dest);
      }
      return `assets/images/${slug}/${destName}`;
    });

const wordHTML = title
  .split("")
  .map((ch, i) => `<span class="w" id="w-${i}">${ch === " " ? "&nbsp;" : ch}</span>`)
  .join("");

const bgHTML = imagePaths.length
  ? imagePaths.map((p, i) => `
    <img id="bg-${i}" class="bgimg" src="${p}" alt="carousel" />`).join("")
  : "";

// crossfade plan: N images -> N-1 overlaps; lay by time per duration
const imgCount = imagePaths.length > 0 ? imagePaths.length : 1;
const perImgDur = imgCount > 1 ? duration / imgCount : duration;
const crossfade = 0.6;

const html = composition({
  title: `military-photo-carousel :: ${title}`,
  duration,
  bg: BG,
  css: `
    .bgimg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;will-change:transform,opacity}
    #mask{position:absolute;inset:0;background:linear-gradient(180deg, rgba(7,11,18,.55) 0%, rgba(7,11,18,.25) 38%, rgba(7,11,18,.42) 62%, rgba(7,11,18,.82) 100%)}
    #vignette{position:absolute;inset:0;box-shadow:inset 0 0 240px 90px rgba(0,0,0,.55)}
    #headline{position:absolute;left:0;right:0;top:33%;text-align:center;font-size:92px;font-weight:700;letter-spacing:14px;color:${FG};text-shadow:0 2px 18px rgba(0,0,0,.75)}
    .w{display:inline-block}
    #kwbar{position:absolute;left:50%;top:${keyword ? "63%" : "52%"};width:520px;height:10px;margin-left:-260px;background:${accent};transform-origin:left;display:block}
    #kwtag{position:absolute;left:50%;transform:translateX(-50%);top:${hasNum ? "70%" : "57%"};text-align:center;font-size:42px;color:${accent};letter-spacing:8px;opacity:0;text-shadow:0 2px 10px rgba(0,0,0,.8);display:inline-block;padding:14px 44px 18px;border-radius:999px;background:rgba(7,11,18,.62);box-shadow:0 0 18px ${accentRgba(0.2)};will-change:background-color,box-shadow}
    #numwrap{position:absolute;left:0;right:0;top:76%;text-align:center;opacity:0}
    #numval{display:inline-block;font-size:120px;font-weight:700;color:${FG};text-shadow:0 2px 16px rgba(0,0,0,.8)}
    #numlabel{display:inline-block;font-size:36px;color:${accent};margin-left:18px;letter-spacing:3px}
    #lower-third{position:absolute;left:60px;bottom:56px;font-size:28px;color:${FG};opacity:.85;letter-spacing:3px;opacity:0;text-shadow:0 1px 8px rgba(0,0,0,.7)}
  `,
  bodyInner: `
    ${bgHTML}
    <div id="mask"></div>
    <div id="vignette"></div>
    <div id="headline">${wordHTML}</div>
    ${keyword ? `<div id="kwbar"></div><div id="kwtag">${keyword}</div>` : ""}
    ${hasNum ? `<div id="numwrap"><span id="numval" data-t="${Number(numTarget) || 0}">0</span><span id="numlabel">${numLabel || ""}</span></div>` : ""}
    ${lower ? `<div id="lower-third">${lower}</div>` : ""}
  `,
  script: `
    const tl = gsap.timeline({ paused: true });
    ${imagePaths.length ? `
    // carousel background: fade-in first image; each transition = crossfade
    tl.to("#bg-0", { opacity: 1, duration: 0.5, ease: "power1.out" }, 0);
    ${imagePaths.map((_, i) => i === 0 ? "" : `
    tl.to("#bg-${i}", { opacity: 1, duration: ${crossfade}, ease: "power1.inOut" }, ${(perImgDur * i) - crossfade / 2 || (perImgDur * i)});
    tl.to("#bg-${i - 1}", { opacity: 0, duration: ${crossfade}, ease: "power1.inOut" }, ${(perImgDur * i) + crossfade / 2});`).join("\n    ")}
    // Ken Burns on each visible img (alternate push toward / pull away)
    ${imagePaths.map((_, i) => {
      const origin = i % 2 === 0 ? "50% 30%" : "50% 70%";
      return `tl.fromTo("#bg-${i}", { scale: 1, transformOrigin: "${origin}" }, { scale: 1.08, duration: ${perImgDur + 0.4}, ease: "none" }, ${i * perImgDur});`;
    }).join("\n    ")}
    `.trim() : `
    // no-carousel: static dark card
    `.trim()}
    gsap.set(${JSON.stringify(title.split("").map((_, i) => "#w-" + i))}, { y: 60, opacity: 0 });
    tl.to(${JSON.stringify(title.split("").map((_, i) => "#w-" + i))}, {
      y: 0, opacity: 1, duration: 0.6, ease: "power3.out", stagger: 0.04,
    }, 0.3);
    ${keyword ? `
    tl.fromTo("#kwbar", { scaleX: 0 }, { scaleX: 1, duration: 0.7, ease: "power2.inOut" }, 1.2);
    tl.to("#kwtag", { opacity: 1, duration: 0.5 }, 1.6);
    // breathing glow on the chip background/outline only (no text glow -> keeps
    // multi-segment keywords from visually merging). Determinstic: pinned to the
    // main paused timeline, sine yoyo repeat, seek-safe.
    tl.fromTo("#kwtag",
      { backgroundColor: "rgba(7,11,18,.5)", boxShadow: "0 0 18px ${accentRgba(0.2)}" },
      { backgroundColor: "rgba(7,11,18,.72)", boxShadow: "0 0 44px ${accentRgba(0.45)}",
        duration: 2.6, ease: "sine.inOut", yoyo: true, repeat: -1 }, 2.2);` : ""}
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
console.log(`[military-photo-carousel] wrote ${out}`);
console.log(`[military-photo-carousel] images=${imagePaths.length} next: npx hyperframes lint && validate && render -o ../../renders/photo_carousel.mp4`);