// _military-shared/composition.mjs — shared HyperFrames composition builder
// for the military-* asset skills. Renders a standalone 1920x1080 deterministic
// composition (gsap paused timeline) as HTML. NOT a skill — a shared library.
//
// Determinism contract (from hyperframes-core): no Date.now / Math.random /
// network / repeat:-1; single paused timeline registered on window.__timelines.
// A seeded PRNG (mulberry32) is provided for scatter/particle placement.

/* Deterministic PRNG seedable per asset so renders are reproducible. */
export function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Assemble a full standalone HyperFrames index.html.
 *
 * @param {object} o
 * @param {string} o.title            <title>
 * @param {number} o.duration         root data-duration (seconds)
 * @param {string} [o.css]            <style> body
 * @param {string[]} [o.libs]         extra <script src> tags (gsap auto-added)
 * @param {string} o.bodyInner        HTML placed inside the #root clip section
 * @param {string} o.script           inline <script> (builds timeline, registers window.__timelines["main"])
 * @param {string} [o.bg="#05070d"]   root background color
 * @returns {string}
 */
export function composition({
  title,
  duration,
  css = "",
  libs = [],
  bodyInner = "",
  script,
  bg = "#05070d",
}) {
  const gsapTag = `<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>`;
  return `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>${title}</title>
    ${gsapTag}
    ${libs.map((l) => `<script src="${l}"></script>`).join("\n    ")}
    <style>
      @font-face{font-family:"Microsoft YaHei";src:local('Microsoft YaHei');font-display:swap}
      @font-face{font-family:"PingFang SC";src:local('PingFang SC');font-display:swap}
      body{margin:0;background:${bg};color:#fff;font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif;overflow:hidden}
      #root{position:relative;width:1920px;height:1080px;overflow:hidden;background:${bg}}
      .clip{position:absolute;inset:0;overflow:hidden}
      bar{display:block}
      ${css}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="${duration}">
      <section id="scene" class="clip" data-start="0" data-duration="${duration}" data-track-index="1">
        ${bodyInner}
      </section>
    </div>
    <script>
      window.__timelines = window.__timelines || {};
      ${script}
    </script>
  </body>
</html>
`;
}

/** Write a file (helper so every skill generator behaves the same). */
export function writeText(fs, filePath, data) {
  fs.mkdirSync(filePath.dirname, { recursive: true });
  fs.writeFileSync(filePath, data, "utf8");
}