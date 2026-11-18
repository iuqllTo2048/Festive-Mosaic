# P01 首页飘带动效返修

日期：2026-11-18。返修基线：`a3ea1dc44b112c985a2d0b052c5b73f450a6fe4f`。范围仅P01首页；未设计P02、未改端午工作台、未改科研生产代码或素材原图。

## 问题与修正

用户看到直接覆盖的原因已实际检查：当前内嵌浏览器的 `prefers-reduced-motion: reduce` 为true，旧首页调用瞬时切换分支。此前只在独立验收页检查常规动画，无法保证用户直接打开正式首页即可体验。原边界也只有11/5px两层描边，达不到有体积的飘带观感。

本次正式首页新增“播放飘带动效 / 暂停飘带动效”。首次遵循系统设置，用户主动选择保存于本机 `festive-mosaic:p01-motion`，刷新和重新进入仍有效，不修改系统设置。关闭时完整保留静态融合画卷；Hover不再瞬时替换整张图，点击进入专题保持可用。当前体验标签已通过真实控件开启动态。

展开边界现在是约14–66个原图坐标单位宽的实心飘带，随画卷向外弧形铺开：节日配色、暗面折转、双侧金边、褶线和轻微投影共同呈现层次。曲线前沿采用包围画面的弧形目标，避免展开中途变成矩形画框。风动、宽度和明暗都仅由展开进度决定，中途离开时能准确反向回卷。最终离开画面前淡去。保留原2000ms状态机、默认帧后才展开下一节日和原固定热区。

素材自身没有独立飘带图层，本次使用SVG带状曲面补充动态边界；没有提取并扭曲原图中的每一条纹样，也不是物理布料模拟。原五张全屏图与默认图的构图差异仍存在，前12%进度在选中区域内接合渐显，不能宣称逐像素无缝。

## 改动文件

| 文件 | 原因 |
| --- | --- |
| `design/prototype/src/FestivalPanorama.vue` | 正式动效控制、保存选择、静态模式、实心飘带与节日色彩 |
| `design/prototype/src/p01-animation.ts` | 弧形展开前沿、可逆风动、变宽曲面与折面几何、动态偏好解析 |
| `design/prototype/src/p01-animation.test.mjs` | 补充偏好覆盖、飘带几何有限性与反向一致性验证 |
| `design/prototype/src/p01.css` | 动效控制排版；展开时避免固定热区的焦点描边叠在新画面上 |
| `README.md`、`design/prototype/README.md`、`docs/P01_HOMEPAGE_REVIEW.md`、`02_BUILD_PLAYBOOK.md` | 当前使用方式与真实返修记录，原验收保留为历史 |
| `design/screenshots/p01-ribbon-fix/` | 本次真实浏览器截图序列及原始观察 |

## 实际验证

环境：Windows、PowerShell，复用Node22及现有frontend/node_modules。正式开发服务 `http://127.0.0.1:5175/`，没有安装依赖、没有模型调用。动画截图来自正式首页，不是独立motion-check页。

| 检查 | 实际结果 |
| --- | --- |
| 动态控制 | 用实际控件开启；系统减少动态仍为true，页面动态分支为false（不减少）。刷新保留主动选择 |
| 关闭动态 | 实际点击暂停后idle、active为空；再次键盘聚焦春节也保留静态画卷 |
| 正式页展开 | 键盘聚焦春节，采集6张实时截图；DOM采样进度依次为0.0021、0.1834、0.3604、0.5333、0.7250、0.9041 |
| 切换与回卷 | 改聚焦中秋后观察到active=spring、desired=mid-autumn、collapsing、progress=0.8204；随后idle/active为空/progress=0；之后观察到中秋expanded/progress=1 |
| 1440×900 | 正式页采集飘带过程；截图可直接检查画卷与移动边界 |
| 1024×768、390×844 | DOM确认指定视口、无横向溢出；手机仍有5个等价节日按钮。只算布局检查，未宣称真机视觉通过 |
| 控制台 | 本次最终error/warn为空 |

截图：[展开中段](../design/screenshots/p01-ribbon-fix/spring-frame-3.jpg)、[后段](../design/screenshots/p01-ribbon-fix/spring-frame-4.jpg)、[回卷采集](../design/screenshots/p01-ribbon-fix/spring-collapse.jpg)。完整6帧和[原始观察](../design/screenshots/p01-ribbon-fix/browser-checks.json)一起保存。DOM与合成器有帧延迟，所以不把任何一张截图标作精确25%/50%；没有冻结动画或合成截图。

鼠标自动化本轮未通过：内嵌浏览器AX拖动能改变CSS Hover，但没有触发应用的进入事件；没有注入事件冒充鼠标操作。改用computer-use尝试真实窗口，`get_window_state`两次超时，按规则停止重试。上述动态流程是键盘聚焦同一状态机的验证；实际鼠标悬停手感仍需用户确认。移动端导出的旧合成器画面带黑色空段，独立标签捕获也失败，未纳入有效截图，不标记手机视觉复核通过。

## 工程回归

工作目录：`E:\VerifiAtlas\design\prototype`。

- `node --experimental-strip-types --disable-warning=ExperimentalWarning --test src/p01-animation.test.mjs`：9通过、0失败（新增几何完成后又由全量测试覆盖）。
- `npm.cmd test`：21通过、0失败、0跳过。
- `npm.cmd run typecheck`：通过。
- `npm.cmd run build`：通过，36模块；CSS41.36kB、主JS136.27kB、Three.js573.11kB。既有500kB分块提示保留。
- `git diff --check`：通过。未改9张原图、文化内容、图谱组件、后端和科研原前端。用户photoResource不纳入提交。

完成后单独一次修复提交并推送文化远程，不改写上次提交。停止在P01，下一步由用户实际体验决定。
