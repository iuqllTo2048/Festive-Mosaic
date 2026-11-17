# Festive Mosaic P01｜五节画卷首页验收

日期：2026-11-18。代码基线：`f639a7ebeb83813bb4652458f7ef33d0ce0ee8c9`。

依据用户提供的 `photoResource/FestiveMosaic_P01_Codex_Package/docs/CODEX_PROMPT_P01_HOMEPAGE.md` 与 `ASSET_MANIFEST.md` 实施。仅首页、首页导航与必要跳转调整；不开发P02，不修改科研项目，不连接后端。

## 实际使用的素材

9张PNG均从素材包原样复制到 `design/prototype/public/p01/`，逐个SHA256比对一致，共23,054,425字节。部署清单见[manifest.json](../design/prototype/public/p01/manifest.json)。源ZIP和photoResource原目录不提交。

| 素材 | 用途 |
| --- | --- |
| `art/01_home_default_panorama.png` | 默认五节融合画卷，1586×992 |
| `art/02_hover_spring_festival_fullscreen.png` | 春节展开图，1672×941 |
| `art/03_hover_qingming_fullscreen.png` | 清明展开图，同上 |
| `art/04_hover_duanwu_fullscreen.png` | 端午展开图，同上 |
| `art/05_hover_qixi_fullscreen.png` | 七夕展开图，同上 |
| `art/06_hover_mid_autumn_fullscreen.png` | 中秋展开图，同上 |
| `ui_assets/07_center_flower_click_hint.png` | 花饰悬停提示，2172×724，原文保留 |
| `ui_assets/08_navigation_bar.png` | 原图导航基底，1589×162 |
| `ui_assets/09_festival_dropdown.png` | 原图节日菜单，385×504 |

没有重新绘制导航、下载配图或生成替代艺术。品牌、菜单、档案、关于入口使用原图及其上的原生按钮；花饰提示仍是用户原图。默认画卷内原有顶部导航行通过SVG的y=85显示取景裁去，避免与独立导航重叠，源文件不改。可访问标题与按钮名称由Vue提供。

## 组件与动效

| 文件 | 职责 |
| --- | --- |
| `src/P01Home.vue` | 首页组装；画卷与菜单统一调用goToFestival |
| `src/TopNavBar.vue` | 原图导航、菜单热区、Hover/点击、方向键/Home/End/Escape |
| `src/FestivalPanorama.vue` | SVG分区、花饰提示、资源准备、遮罩与RAF生命周期 |
| `src/p01-scenes.ts` | 5个节日key、已有festival_id、素材、固定曲线热区与展开原点 |
| `src/p01-animation.ts` | 独立时钟状态机与边界几何，无动效依赖 |
| `src/p01.css` | 首页与手机布局，作用域限定p01 |
| `src/p01-animation.test.mjs` | 7项动画/中断/路由测试 |
| `qa/p01-motion-check.ts`、`p01-motion-check.html` | 独立本地常规动画验收入口，不进入生产构建 |
| `src/App.vue` | 接入首页、首页隐藏旧顶栏/页脚、修正未开放专题跳转 |
| `src/main.js`、`tsconfig.json`、`package.json` | 样式、类型检查范围与测试接入 |

五条曲线按默认融合图手工标定，热区始终不随展开图变化。每条原曲线采样112点，从对应分区向外框扩张，并加入幅度受限的边界摆动；SVG遮罩展示真实展开图。描边沿同一路径移动，最后10%进度淡出，回卷时恢复。不是A图全屏淡入B图；图片内容本身没有进行形变。

状态为 `idle → expanding → expanded → collapsing → idle`。展开时长常量严格为2000ms；中途离开按当前进度原轨迹回卷，快速移入只保留最新目标。回卷到0时实际发布默认帧，下一次RAF才启动新节日。空闲不持续调度；卸载取消RAF，清理媒体偏好、resize、visibility与图片回调。

浏览器实际事件记录：春节展开从278.2ms到2281.0ms，约2002.8ms；回卷2353.2ms到4355.9ms，随后4360.2ms才展开中秋，中秋于6360.2ms完成，间隔2000.0ms。2000ms是逻辑时长，实际呈现受刷新帧和调度影响，不能承诺每台设备物理显示恰好在同一毫秒。

## 路由与保留功能

画面和菜单都映射到已有hash路由：

| 画卷key | 路由 | 当前状态 |
| --- | --- | --- |
| spring | `/#/festivals/chunjie` | 春节篇尚未开放 |
| qingming | `/#/festivals/qingming` | 清明篇尚未开放 |
| duanwu | `/#/festivals/duanwu` | 保留的端午功能入口，未新设计P02 |
| qixi | `/#/festivals/qixi` | 七夕篇尚未开放 |
| mid-autumn | `/#/festivals/zhongqiu` | 中秋篇尚未开放 |

首次测试发现旧openFestival函数追加/unavailable，导致解析丢失节日名称；已改为直接进入既有专题路径，由原parseRoute决定开放状态。五组画面/菜单目标及正确状态重测全部一致。不改变任何节日的发布状态。

观察档案与关于入口保留；端午进入本地导览后，实际提交样例得到5条摘编、0模型调用，并能打开S01资料链接。原图谱/列表、对照与本地档案逻辑保留，未重新验收全部旧工作台细节。

## 浏览器验收与截图

正式页面：`http://127.0.0.1:5175/`。实际运行Chromium内嵌浏览器；1440×900、1024×768、390×844均无横向溢出。1024采用完整画卷取景，保留右侧七夕展签；手机保留整幅比例、同一导航图的局部取景，以及等价文字节日入口，不要求触屏复刻Hover。未进行真机触摸测试。

本次浏览器系统偏好为减少动态效果。正式页面遵循该偏好，瞬时显示目标图。完整常规动画通过独立开发入口 `/p01-motion-check.html` 实际指针交互验收，截图右下明确带“动效验收 · 常规动画”。该入口没有改变系统设置，不在dist中，正式首页没有测试开关。

| 场景 | 实际截图 |
| --- | --- |
| 正式默认首页 | [1440](../design/screenshots/p01/default-1440.jpg)、[1024](../design/screenshots/p01/default-1024.jpg)、[390](../design/screenshots/p01/default-390.jpg) |
| 实际花饰Hover | [中心提示](../design/screenshots/p01/center-hint-1440.jpg) |
| 实际菜单Hover与手机点击 | [桌面目录](../design/screenshots/p01/dropdown-1440.jpg)、[手机目录](../design/screenshots/p01/dropdown-390.jpg) |
| 春节展开过程（开发验收页） | [约25%](../design/screenshots/p01/spring-25.jpg)、[约50%](../design/screenshots/p01/spring-50.jpg)、[100%](../design/screenshots/p01/spring-100.jpg) |
| 春节回卷与切换 | [回卷中](../design/screenshots/p01/spring-collapse.jpg)、[切换中秋](../design/screenshots/p01/spring-to-mid-autumn.jpg)、[中秋完成](../design/screenshots/p01/mid-autumn-100.jpg) |
| 其他画卷完成态 | [端午](../design/screenshots/p01/duanwu-100.jpg)、[清明](../design/screenshots/p01/qingming-100.jpg)、[七夕](../design/screenshots/p01/qixi-100.jpg) |
| 点击后目标 | [画面进端午](../design/screenshots/p01/click-art-duanwu.jpg)、[菜单进端午](../design/screenshots/p01/click-menu-duanwu.jpg)、[春节未开放](../design/screenshots/p01/unopened-spring.jpg) |

进度截图是实时截屏，非冻结时间或合成：25%帧采集前后进度25.40%–28.32%，50%帧50.20%–53.32%。全屏截图额外等待绘制稳定。浏览器多次改变同一标签尺寸时曾出现导出裁切，最终1440采用独立标签重新截图，主要三尺寸截图像素均与要求一致。

[browser-checks.json](../design/screenshots/p01/browser-checks.json)保存22项浏览器观察，含早期跳转/视口问题与重测标记，不混计为自动化测试数。实际检查还包括五节分区、目录Hover、花饰Hover、两秒完整动效、键盘方向键/End/Escape、手机目录及文字等价入口。最终控制台error/warn为空。

## 工程验证

环境：Windows PowerShell、Node22.23.2、npm10.9.8，复用frontend/node_modules，没有安装依赖。工作目录 `E:\VerifiAtlas\design\prototype`。

- `node --experimental-strip-types --disable-warning=ExperimentalWarning --test src/p01-animation.test.mjs`：7通过。
- `npm.cmd test`：最终19通过、0失败、0跳过。
- `npm.cmd run typecheck`：通过，含新首页组件与开发验收入口。
- `npm.cmd run build`：通过，36模块；CSS40.89kB、主JS133.05kB；Three.js573.11kB，既有>500kB告警保留。
- 检查dist：含9张原PNG与主入口；不含动效验收HTML/测试标识。
- 科研backend/frontend/eval/samples及文化内容、模型演示逻辑、Three.js组件、范围适配、原路由与节日发布配置相对基线无改动。

测试与截图不证明文化关系已经经过人工语义认证；本轮没有调用模型或线上RAG。

## 仍需用户审核的视觉问题

1. 默认图与五张全屏图是不同构图，无法仅靠遮罩让所有房屋、人物、水纹逐像素吻合。前12%进度只在已遮罩分区内做局部接合渐显，之后依靠边界铺开，仍可见对象变化。完全无缝需要配套分层或对齐的源美术，本轮没有重画素材。
2. 活动边界是曲线几何与窄描边近似，不是独立飘带图层或布料模拟；原图自带的飘带纹理仍属于图片内容。
3. 原PNG总约23MB，浏览器会准备5张展开图以避免首次Hover空白；弱网、低内存和真实手机性能尚未测。可以后续经确认制作压缩交付版本，本轮保持原文件。
4. 手机原画内文字随画卷缩小，等价文字列表和菜单承担可读入口。导航的原图文字不能像原生字体单独调整，已补键盘和可访问名称，未宣称完整无障碍审核通过。

完成后统一提交推送至festive-mosaic，不推送科研origin。P01结束，不进入P02。
