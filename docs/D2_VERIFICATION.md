# D2 验证记录

日期：2026-11-16（Asia/Shanghai）。本阶段仅实现真实检索与可核对问答。

## 实现范围

- BM25Plus 词面检索，轻量英文/中文字符分词，最多 8 个来源片段；按全部语料或文档 ID 筛选，不执行向量检索、跨语言翻译、补检或图扩展。
- OpenAI 兼容 SDK 调用 DeepSeek；读取既有环境变量，密钥使用 SecretStr 封装，未显示或写入仓库。模型与地址可配置，已核对官方接口和 JSON Output 文档。
- 结构化输出校验，空白、截断或无效 JSON 最多重新请求一次；SDK 自带重试关闭。鉴权、限流、网络、超时、额度及上游错误均有可读提示，不返回 mock 回答。
- 每段必须有可核对的 chunk ID 与原文引句；后端仅接受本轮检索片段，允许空白规范化。失效段落被移除；编号、文档和页码由后端分配。检查不代表语义上的充分支持或科学事实验证。
- SQLite 增量建立 query_runs 表，保存问答和引用映射，不修改或删除 D1 语料。GET run 与 GET chunk 支持重启后的来源查询。
- 前端加入最简提问、全部/当前论文范围、加载/错误/不足状态、引用按钮及完整片段定位，沿用已有明暗主题。

## 实际执行

- `uv sync --no-python-downloads --link-mode=copy`：成功，新增 rank-bm25、OpenAI SDK 及所需依赖，沿用已有 Python 3.12 与缓存。
- 最小测试：`python -m pytest tests/test_query.py -k 'known_phrase or citation_mapping or no_evidence or invalid_source'`，6 项通过。
- 后端完整 `python -m pytest`：44 项通过（D1 27 项 + D2 17 项）；继承的 Starlette/httpx 弃用提示 1 条，未影响测试。
- 导出 OpenAPI、`npm.cmd run generate:api`、`npm.cmd run typecheck`、`npm.cmd run build`：均通过。
- 浏览器实际使用环境变量中的密钥向 DeepSeek 提交 E1：返回 2 条引用，模型请求 1 次，后端记录 2453 ms。没有为验证脚本重复生成回答。
- `python scripts/verify_d2_live.py --run-id dd848940-8bba-4f3b-9208-98738ea36bf9`：通过，核对 HotpotQA 回答、全部引句、文档/页码/片段映射与保存记录。报告为 `artifacts/d2/live-check.json`。
- 真实空检索 E5：insufficient、0 引用、0 检索片段、0 LLM 请求。
- 浏览器点击 E1 的引用 1、2：分别定位到实际 PDF 第 2、7 页的完整来源片段，文档均为官方 KG²RAG。
- 通过 `?run=<ID>` 打开已保存回答，成功恢复题目、回答和引用，不重复请求 LLM；提问成功后的页面 URL 记录 run ID，刷新后可恢复同一记录。
- 明暗主题均检查；1440×900、1024×768、390×844 下无横向溢出，问答结果和限制可读；浏览器控制台未发现 error / warn。
- 界面截图：`artifacts/d2/answer-light-1440.jpg`、`answer-dark-1440.jpg`、`answer-1024.jpg`、`answer-mobile.jpg`，引用定位截图 `source-location.jpg`。

## 未验证与限制

- 只有一条真实带答案问答和一条真实空词面检索，不构成检索或问答准确率评测；其余标注问题明确列为待执行。
- 鉴权失败、限流、额度、超时及坏 JSON 使用隔离测试与 HTTP Mock 验证，未实际耗尽账户额度、制造真实上游故障或更改用户密钥。
- BM25 无语义向量、自动翻译和重排；中文问题对英文论文可能召回不足。输入中保留英文术语可帮助词面匹配，仍不能保证召回充分。
- 原生 PDF 阅读器的显示/跳页沿用 D1 未核对项；本轮验证的是应用内完整片段定位和 PDF 页码链接，未重试被安全机制停止的系统 Edge 操作。
- 本轮没有实现 D3 的 Requirement、一次补检、支持关系审计和 graph/trace，也没有 D4 的 3D 工作台。

## 参考

- https://api-docs.deepseek.com/quick_start/
- https://api-docs.deepseek.com/guides/json_mode/
- https://api-docs.deepseek.com/api/create-chat-completion/
- https://github.com/dorianbrown/rank_bm25
