# 同节异俗 · 独立设计原型

静态 DEMO，Vue3 + Three.js，复用原仓库前端工具链。没有后端连接、DeepSeek调用、真实RAG运行或新增大型依赖。请从HTTP服务打开，不直接双击index.html。

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
npm.cmd run build
```

构建输出 `design/prototype/dist/`（Git忽略）。可以把此目录交给静态HTTP服务；本轮没有配置线上托管。Three.js为延迟载入的独立分块，构建仍可能提示大于500kB；未以提高告警阈值掩盖。

## 演示路径

1. 首页选择“都与舟有关，仪式就相同吗？”。
2. 探索三地；三维、列表、层次聚焦与复位均可操作。
3. 打开异俗对照镜，默认苏州/汨罗。实践维度共享竞渡，双方出处分别可读。
4. 主题B改为西塞，阅读独立记录；当前摘编无共同细项不表示当地没有。
5. 点击关系查看三步剖面，保存关系后进入观察档案，写下问题并刷新，验证本地恢复。
6. 探索列表中的候选问题没有可支持其传承链的来源，只提供背景阅读入口。

手机默认列表；三维不可用时自动切换同源列表。仅本地档案持久化，浏览过程与相机不完整恢复。存储键为 `festive-mosaic-demo-v1`；清理该站点数据会清除草稿。未提供账号、导出与云同步。

正式资料与状态边界见 [研究札记](../00_RESEARCH.md)，实际检查见 [REVIEW_FOR_CHAT.md](../REVIEW_FOR_CHAT.md)。
