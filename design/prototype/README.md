# 同节异俗｜可复用交互原型

平台首页现为P01五节画卷，原生Vue交互叠加用户提供的9张PNG。详情、截图和限制见[P01验收](../../docs/P01_HOMEPAGE_REVIEW.md)。端午仍用RebuildEntry.vue保留功能入口，没有新开发P02。

常规动画开发验收地址为 /p01-motion-check.html，仅由Vite开发服务提供，不进入生产构建。它明确标记测试模式；正式首页遵循系统减少动态效果偏好。

Vue3 + TypeScript + Three.js，复用原项目前端依赖与锁文件。没有文化 Agent 后端、DeepSeek调用、在线RAG或语义核验；导览仍为本地演示。

## 启动与验证

在仓库的 design/prototype 目录执行：

~~~powershell
npm.cmd run dev
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
~~~

开发地址 <http://127.0.0.1:5175/>，Ctrl+C 停止。构建目录为 design/prototype/dist/，不提交。新克隆先到 frontend 执行 npm.cmd ci；沿用现有锁文件，不建立第二套依赖。测试需 Node22.18+，本轮为22.23.2。

## 保留的模块

| 文件 | 职责 |
| --- | --- |
| src/P01Home.vue、TopNavBar.vue、FestivalPanorama.vue | 五节画卷、原图导航与分区交互 |
| src/p01-animation.ts、p01-scenes.ts、p01.css | 两秒状态机、固定热区、素材映射与响应式 |
| src/RebuildEntry.vue、rebuild.css | 保留的端午临时入口，没有重做专题页 |
| src/App.vue | 路由、共享任务、筛选、对照、来源抽屉与档案状态 |
| src/AgentPanel.vue、cultural-guide.ts | 可输入问题的本地导览演示，不请求模型 |
| src/StrataScene.vue | 实际Three.js节点/关系、聚焦、来源联动和回退事件 |
| src/content.mjs | 端午文化对象、摘编、来源和对照规则 |
| src/festivals.ts、festival-content.ts | 多节日发布/能力配置与文化资料范围 |
| src/navigation.ts | 新旧hash路由兼容 |
| src/style.css、workbench.css | 保留的基础与工作台样式，可供后续独立重构 |

专题原有 visual_asset 字段保留，当前值均为null，没有失效图片路径。只有端午开放，其余五节日只显示状态。

## 现有功能入口

- /#/：P01五节画卷首页。
- /#/festivals/duanwu：端午资料与问题入口。
- /#/festivals/duanwu/explore：本地导览、图谱与同源列表。
- /#/festivals/duanwu/compare：两地习俗对照与资料回读。
- /#/archive：本地观察档案。

旧 #home/#explore/#compare/#archive 继续可用。观察档案存储键 festive-mosaic-demo-v1 未改，不清除用户草稿。任务和相机状态不会完整跨刷新恢复，尚无账号、云同步或导出。手机默认列表，三维不可用时切换到同源列表。

旧素材和展示恢复方法、真实验证记录见[重构基线](../../docs/FRONTEND_REBUILD_BASELINE.md)。
