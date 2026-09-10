# 005-02 — gsap 引用恢复 CDN 并加本地文件兜底

**What to build:** hyperframes 场景渲染时 gsap 一定能加载到：构建出的 `index.html` 引用 CDN 版 gsap（3.14.2，72779B，与 vendor 同哈希），同时把 `_military-shared/vendor/gsap.min.js` 拷贝到项目 `hyperframes/` 同目录作为离线兜底，渲染不再因 `Cannot read properties of null (reading 'timeline')` 失败。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] `composition.mjs` 的 gsap 标签恢复为 `https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js`
- [ ] photo-carousel builder 写 index.html 后把 vendor/gsap.min.js（72779B）拷入 `hyperframes/` 同目录；md5 与 vendor 一致
- [ ] `node build_photo_carousel.mjs --no-carousel` 后 `hyperframes/index.html` 含 CDN URL，`hyperframes/gsap.min.js` 存在
- [ ] 单场景 `npx hyperframes lint && validate` 通过