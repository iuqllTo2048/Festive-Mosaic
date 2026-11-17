# 同节异俗 · 独立设计原型

静态 DEMO，Vue3 + Three.js，复用原仓库前端工具链。没有后端连接、DeepSeek调用、真实RAG运行或新增大型依赖。请从HTTP服务打开，不直接双击index.html。

2026-11-17当前版本已集成六张新艺术素材和可操作文化导览演示。最新截图、Agent/图谱/来源联动、真实能力及限制见 [AGENT_GRAPH_UI_REVIEW.md](../../docs/AGENT_GRAPH_UI_REVIEW.md)。多节日架构沿用 [平台架构报告](../../docs/PLATFORM_ARCHITECTURE_REVIEW.md)；目前仅端午开放。

## 启动

已有 `frontend/node_modules` 时，在仓库根目录执行：

```powershell
cd design/prototype
npm.cmd run dev
```

打开 <http://127.0.0.1:5175/>。使用独立端口，原应用5173不受影响。停止时在启动终端按Ctrl+C。

新克隆若没有依赖，先在根目录执行以下一次性安装，使用现有锁文件：

```powershell
cd frontend
npm.cmd ci
cd ../design/prototype
npm.cmd run dev
```

工具链沿用前端的Node要求（^20.19.0或>=22.12.0）；本轮实际Node22.23.2。没有独立node_modules或第二份依赖锁。

## 检查与构建

```powershell
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
```

构建输出 `design/prototype/dist/`（Git忽略）。可以把此目录交给静态HTTP服务；本轮没有配置线上托管。Three.js为延迟载入的独立分块，构建仍可能提示大于500kB；未以提高告警阈值掩盖。

## 演示路径

1. 平台首页选择端午，进入专题，再选择“都与舟有关，仪式就相同吗？”。
2. 探索三地；三维、列表、层次聚焦与复位均可操作。
3. 打开异俗对照镜，默认苏州/汨罗。实践维度共享竞渡，双方出处分别可读。
4. 主题B改为西塞，阅读独立记录；当前摘编无共同细项不表示当地没有。
5. 点击关系查看三步剖面，保存关系后进入观察档案，写下问题并刷新，验证本地恢复。
6. 探索列表中的候选问题没有可支持其传承链的来源，只提供背景阅读入口。

## 文化导览与图谱联动

从门户或端午篇进入“AI文化导览”，输入“苏州和汨罗的端午习俗有什么不同？”，提交后实际筛出5条本地摘编。点击回答中的来源按钮聚焦图谱，再打开关联资料；“对照这两个地方”沿用当前任务。更换对照地方会同步任务，返回导览后保留更新的问题。

这是演示模式，执行记录展示真实本地筛选与字段检查；没有调用模型、在线RAG或语义核验。超范围问题保留资料缺口。导览任务仅在当前页面会话保存，刷新会重置；原观察档案继续本地持久化。手机默认同源列表，页面保留三维入口。

手机默认列表；三维不可用时自动切换同源列表。仅本地档案持久化，浏览过程与相机不完整恢复。存储键为 `festive-mosaic-demo-v1`；清理该站点数据会清除草稿。未提供账号、导出与云同步。

## 节日配置与链接

配置位于 `src/festivals.ts`，专题发布状态独立于文化关系的核验状态。`festival-content.ts`为现有资料附加festival_id、cultural_topic_id，过滤资料范围；原内容与Three.js组件不重写。当前只有端午内容适配器，未来正式专题需要接入自己的资料与视觉，不通过切换status冒充完成。

静态部署采用hash路由，无需服务器重写：`/#/`、`/#/festivals/duanwu`、`/#/festivals/duanwu/explore`、`/#/festivals/duanwu/compare`、`/#/archive`。旧`#home`仍是端午首页，`#explore/#compare/#archive`继续可用；浏览器前进后退同步页面。不提供无hash的`/festivals/...`深链接。

测试配置与路由使用Node的内置TypeScript类型擦除，测试命令需Node22.18+（本轮22.23.2）；不新增测试框架。类型检查覆盖新增TS配置、作用域适配器及两个首页组件，旧JS工作台没有声称完成全量严格类型迁移。

正式资料与状态边界见 [研究札记](../00_RESEARCH.md)，实际检查见 [REVIEW_FOR_CHAT.md](../REVIEW_FOR_CHAT.md)。
