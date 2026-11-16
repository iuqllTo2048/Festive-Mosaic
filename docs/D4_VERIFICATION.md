# D4 科研证据工作台验证记录

日期：2026-11-16。范围仅 D4，后端协议和检索算法不变；D5 未开始。

## 实现与文件

- `frontend/src/App.vue`、`workspace.css`：三栏布局、明暗主题、响应式抽屉、上传浮层、空态与错误态。移除旧 `style.css`、`QueryPanel.vue`、`AuditSummary.vue`。
- `components/EvidenceGraph.vue`：按需加载 3d-force-graph 1.80.2、Three.js 0.187.0、three-spritetext 1.10.0；真实 API 图、状态形状与标签、来源链聚焦、视角重置、资源释放、初始化失败转列表。
- `components/AuditPanel.vue`、`SourceDrawer.vue`、`QueryComposer.vue`、`TracePlayer.vue`：需求/回答/来源、真实片段和页码、提问设置、完成后的执行事件回放。
- `graph-model.ts` 与 4 项测试：事件可见性、支持链边界、渲染数据副本、120 节点上限且无悬空边。
- `package.json`、`package-lock.json`、`tsconfig.json`、`main.ts`：固定运行依赖、Node 测试和新样式入口。MIT 归属保存在根目录 `THIRD_PARTY_NOTICES.md`。

## 实际执行命令

PowerShell，已有依赖缓存，没有新增模型调用：

```powershell
Set-Location E:\VerifiAtlas\frontend
npm.cmd run typecheck
npm.cmd test
npm.cmd run build

Set-Location E:\VerifiAtlas\backend
uv run --locked pytest
uv run --locked python scripts/verify_d3_live.py --run-id 0f41fa68-de2f-4c67-9a80-d13521a6665b
```

结果：类型检查通过；前端 4/4 测试通过；后端 60 项通过；生产构建成功。最后一次前端检查在标签材质修正后执行。构建输出位于 `E:\VerifiAtlas\frontend\dist\`（Git 忽略）。入口 JS 112.13 kB；按需加载 Three 743.01 kB、force graph 908.02 kB，gzip 分别 187.78/255.38 kB；Vite 的 500 kB 提示保留，未将阈值调高来隐藏提示。

保存记录的 GET 复核通过：25 节点、47 条边；支持 1/2，补检 1 次，原执行请求 4 次、耗时 5328 ms，停止原因为 `repair_exhausted`。这些是 D3 原执行统计，不能当成 D4 新执行或图谱加载耗时。D4 未调用 DeepSeek；未改变历史问答。

## 浏览器实测

通过桌面应用内浏览器操作实际运行的 Vue/FastAPI，加载上述保存记录；没有注入假 API 响应或随机节点。

| 检查 | 实际观察 |
| --- | --- |
| WebGL | 实际显示 25 节点 / 47 关系，论文、片段、术语与需求可区分；重置视角可恢复全图 |
| 来源链 | 数据集需求聚焦 5 节点 / 4 关系；能耗缺口仅自身 1 节点 / 0 关系，不借术语共现虚构支持 |
| 节点/引用 | 直接点击 3D 论文节点打开真实原文；引用及列表片段均定位 KG2RAG 的 PDF 第 5 页、片段 28 |
| 原文抽屉 | 切换至实际第 7 页显示该页真实片段；PDF 链接带 `#page=7`；900 高视口中对话框高度 899，无底部截断；Esc 关闭 |
| 回放 | 起点 0 节点 / 0 边；规划事件后 2 个待核查需求；支持状态、有效引用和最终答案不会提前显示；回到结果恢复完整图 |
| 等价列表 | 关闭 3D 后 canvas 为 0，仍有 25 个节点、47 条关系和对应出处入口 |
| 主题 | 深浅主题均显示界面和图谱；修正 Sprite 材质叠染后文字背景不再染成节点色 |
| 1440×900 | 三栏，文档宽 1440，canvas 1，无横向溢出 |
| 1024×768 | 审计改抽屉，文档宽 1024；打开后焦点移至收起按钮，Esc 后回到“审计与来源” |
| 390×844 | 默认等价列表，canvas 0，文档宽 390；语料抽屉可打开上传浮层 |
| 320×720 | 文档宽 320；关闭浮层与语料栏后焦点回到“语料” |
| 键盘 | 按钮与页码控件可聚焦；回放滑杆 Home/方向键定位；Esc 关闭来源/抽屉或清除聚焦 |
| 空态/错误 | 无 run 时图为空，播放禁用；不存在的 UUID 显示“问答记录不存在。”；未选文件提交显示“请先选择 PDF。” |
| 控制台 | 最后验收时段没有 warn/error；开发中移除旧组件造成的临时 HMR 错误已在刷新后消失 |

CSS 正文、次要文字、链接、支持、缺口、错误色，对深浅两套 bg/surface/surface-raised 的 36 对组合进行 sRGB 相对亮度计算：暗色最低 **5.93:1**，浅色最低 **5.22:1**。见 `artifacts/d4/contrast-check.json`。这是文字 token 验证，不是整个 WebGL 场景或完整无障碍认证；3D 弱化后的节点可通过清晰的等价列表操作。

## 证据与限制

- 截图绝对目录：`E:\VerifiAtlas\artifacts\d4\`。最终桌面图为 `workspace-dark-1440.jpg`、`workspace-light-1440.jpg`；响应式图为 `workspace-1024.jpg`、`workspace-mobile.jpg`。其他截图记录交互检查过程，`before.jpg` 为重构前对照。
- 浏览器运行环境的 `prefers-reduced-motion` 为 true，实际验证手动逐步回放。非减少动态效果分支的 750ms 自动播放与过渡未另行实测。
- WebGL 初始化失败/上下文丢失的降级代码已实现，但未人为制造 GPU 故障；实测的是主动关闭 3D 的等价列表。
- 原文抽屉的实际页码、完整片段和 PDF URL 已核对；系统 PDF 阅读器显示及自动跳页仍未视觉复核，下载按钮也未实际下载验证。
- D4 验证上传浮层与未选文件提示，完整真实上传/去重沿用 D1–D3 记录及本轮后端回归，不宣称本轮重复做过真实上传。
- 图谱固定分区、距离和物理布局仅帮助阅读，不是科学相似度、因果或证据强度；术语仅是共现。supported 是模型判断结合来源检查，不代表科学事实认证。
- 大图上限测试为合成数据；没有做大规模性能基准。五题真实对照、无 key 全流程与最终演示属于 D5。

## 最少复核步骤

当前两个开发服务已运行，直接打开：

[保存的真实 D3 记录](http://127.0.0.1:5173/?run=0f41fa68-de2f-4c67-9a80-d13521a6665b)

点击两个需求比较来源链，点击引用核对第 5 页，切换明暗和列表，拖动回放滑杆检查事件。无需重新调用模型或重新导入 PDF；如果服务已停止，使用 README 的两个 PowerShell 启动命令。

阶段状态：D4 已完成；本地统一提交 `feat(d4): build evidence research workspace`，不自动推送。建议下一轮 D5：只修错，执行真实五题对照并整理演示交付；等待用户明确批准。
