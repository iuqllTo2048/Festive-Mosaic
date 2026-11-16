# VerifiAtlas——面向科研知识探索的智能交互可视化系统

科研证据工作台。当前完成至 **D2：真实检索与可核对问答**：导入真实 PDF，通过 BM25 检索并调用 DeepSeek，逐条核对引用文字与来源页码。后续开发严格按 [阶段计划](02_BUILD_PLAYBOOK.md#5-五个开发阶段每次只执行一个阶段完成后提交一次) 推进，每阶段完成后只提交一次。

界面品牌简称 VerifiAtlas；GitHub 仓库名保留 verifyAtlas。

## 当前能力

- 上传文本型 PDF，按实际页面解析、分块（800 字符、100 字符重叠），保留稳定文档/片段 ID、页码和字符范围。
- SQLite 持久化，原 PDF 保存在本机；SHA256 去重，重启后数据保留。
- 语料列表、逐页原文检查、片段分页、打开 PDF 对应页。
- 顶栏可切换浅色/深色主题，首次打开跟随系统；手动选择保存在当前浏览器，刷新后保留。禁用本地存储时仍可切换，但无法跨刷新保存。
- 3 篇官方论文来源清单，可分别一键导入；下载失败会报告原因并提供官方页面及手动上传入口。
- 空文件、错误格式、损坏 PDF、加密文件、过大文件和无可提取文本文件有明确错误。混合文档中没有文本的页面保留实际页码并显示警告；页面解析异常时整份导入失败。
- 基于已导入片段的 BM25Plus 词面检索；可以检索全部语料或当前论文，每次最多 8 个片段。
- DeepSeek 结构化回答，每段必须有本轮检索片段中的有效原文引句；引用的文档、页码、片段 ID 和 PDF 地址由后端确定。不能核对的段落被移除，无证据时明确报告不足。
- 点击回答中的引用定位到完整原文片段；问答及引用映射保存到本机 SQLite，提供稳定的 run ID。
- 问答成功后 URL 带有 `?run=<ID>`，刷新可恢复该记录，不重复请求 LLM；记录仅在这台机器的本地服务中有效。

**尚未实现**：Requirement 证据审计、定向补检、概念扩展、3D 图谱。引文存在性检查不代表结论在语义上正确，也不证明科学事实；请核对上下文。BM25 没有语义向量或自动跨语言翻译，英文论文建议保留英文术语。

## 环境与首次安装（Windows PowerShell）

需要 Python **3.12**、[uv](https://docs.astral.sh/uv/getting-started/installation/) 和 Node.js **22.12+**（当前验证为 22.23.2；Node 24 LTS 也可）。项目不要求全局安装前端构建工具，也不需要激活虚拟环境。

```powershell
Set-Location E:\VerifiAtlas\backend
uv sync --locked --python 3.12

Set-Location E:\VerifiAtlas\frontend
npm.cmd ci --no-audit --no-fund
```

后端依赖锁定在 `backend/uv.lock`，前端依赖锁定在 `frontend/package-lock.json`。前端项目级 `.npmrc` 使用官方 npm 源，避免镜像版本不同步；不修改系统 npm 设置。

## 启动（两个 PowerShell 窗口）

窗口 1：

```powershell
Set-Location E:\VerifiAtlas\backend
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
```

窗口 2：

```powershell
Set-Location E:\VerifiAtlas\frontend
npm.cmd run dev
```

打开 [本地工作台](http://127.0.0.1:5173/)。健康检查为 [GET /api/health](http://127.0.0.1:8000/api/health)，交互 API 文档为 [OpenAPI /docs](http://127.0.0.1:8000/docs)。两个窗口按 `Ctrl+C` 停止。

前端通过 Vite 代理访问后端，不需要配置 CORS。默认仅监听本机环回地址；本项目当前没有登录或访问控制，不用于公开网络。请只启动一个后端进程，勿使用多个 worker。

## 最短人工验收

1. 在页面下方选择一篇论文，点击“导入论文”；也可以从官方页面下载后，点击“上传论文”选择 PDF。
2. 左侧选择文档，右侧切换“实际页码”，检查该页原文片段，再点“打开 PDF · 第 N 页”与实际 PDF 页面核对。这里的页码是 PDF 页面序号，不是论文印刷页码。
3. 再次上传同一 PDF，应提示文档已存在，文档数量保持不变。
4. 上传空文件、改名为 `.pdf` 的其他格式、损坏文件或没有可提取文本的文件，确认提示清楚且没有假成功记录。
5. 选择 KG²RAG 并勾选“仅检索当前选中的论文”，输入 `Which benchmark dataset and its variants were used to evaluate KG2RAG? Answer only from the paper and give source quotes.`。回答应能找到 HotpotQA 的来源；点击引用，核对片段和实际页码。某一名称若未检索到，不应补写成已知事实。

上传只发送给本机后端。浏览器 PDF 阅读器通常支持 `#page=N`；若阅读器未自动定位，请手动输入该页码。文字提取可能受到字体编码、分栏和数学公式影响，原 PDF 始终是核对依据。

## 配置与本地数据

默认可直接运行。需要调整限制时，将 `backend/.env.example` 复制为 `backend/.env`：

```powershell
Set-Location E:\VerifiAtlas\backend
Copy-Item .env.example .env
```

D2 的问答需要 `DEEPSEEK_API_KEY`。已有同名环境变量时直接读取，无需复制密钥到文件；环境变量优先于 `.env`。若尚未配置，可自行在本机 `backend/.env` 中填写，勿将真实密钥发到聊天、提交 Git 或放入前端。配置改变后重启后端；健康检查的 `llm_configured` 只说明是否配置，不证明密钥、额度或网络可用。

点击“检索并回答”会把问题与检索到的片段发送到配置的 DeepSeek 服务，消耗账户 API 调用额度；原始 PDF 不会整份上传。无匹配片段时不请求 LLM。后端不记录密钥或上游错误原文；结构化输出失败最多重新请求一次，网络、鉴权和服务错误不会自动重试。问答记录可能包含你的问题及语料引用，均保存在被 Git 忽略的本地数据目录。

| 设置 | 默认值 | 说明 |
| --- | --- | --- |
| `DATA_DIR` | `./data` | 相对路径固定相对于 `backend/`，不受启动目录影响 |
| `MAX_UPLOAD_MB` | `20` | PDF 文件大小上限 |
| `MAX_PDF_PAGES` | `200` | 实际页数上限 |
| `SEED_TIMEOUT_SECONDS` | `30` | 官方来源连接与读取超时 |
| `DEEPSEEK_API_KEY` | 空 | 后端私密配置；已有环境变量可直接使用 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容接口地址 |
| `DEEPSEEK_MODEL` | `deepseek-flash` | 可按账户可用模型覆盖 |
| `LLM_TIMEOUT_SECONDS` | `40` | 每次模型请求超时，上限 50 秒 |
| `LLM_MAX_TOKENS` | `1800` | 单次输出 token 上限 |

SQLite 在 `E:\VerifiAtlas\backend\data\evidence.sqlite3`，原 PDF 在 `E:\VerifiAtlas\backend\data\pdfs\`。文件名由服务端 SHA256 生成，上传文件名不能决定磁盘路径。导入失败会撤回数据库事务并清理对应临时文件。启动失败时检查数据目录是否可写以及 8000/5173 端口是否被占用。

`backend/data/`、虚拟环境、`node_modules/`、构建产物和 `.env` 均不纳入 Git。不要提交真实密钥或用户 PDF。官方来源下载记录原始 PDF URL、来源页面和 UTC 获取时间；普通手动上传保留原文件名和导入时间，不推测作者、年份或来源 URL。

## API 与协议生成

Pydantic / FastAPI OpenAPI 是协议源。前端 `src/api/schema.ts` 由导出的 OpenAPI 自动生成，勿手工修改。

| 接口 | 说明 |
| --- | --- |
| `GET /api/health` | 健康状态、阶段与上传限制 |
| `GET /api/documents` | 已成功导入的文档（有警告时含警告详情） |
| `POST /api/documents/upload` | multipart 字段 `file`；返回文档和 `duplicate` |
| `GET /api/documents/{id}/chunks` | 可选 `page`、`offset`、`limit`；上限 100，按稳定顺序返回 |
| `GET /api/documents/{id}/pdf` | 从数据库已登记文档安全读取原 PDF |
| `GET /api/papers` | 仅返回官方来源元数据，不代表已导入 |
| `POST /api/documents/seed` | JSON `{"paper_ids":["kg2rag"]}`，可选 `kg2rag` / `lightrag` / `paperqa2` |
| `POST /api/query` | JSON `{"question":"...","document_ids":null,"top_k":6}`；返回回答、引用、限制与统计 |
| `GET /api/chunks/{chunk_id}` | 查询引用的完整原文片段，用于精确定位 |
| `GET /api/runs/{run_id}` | 读取已保存的问答及 citation → document/chunk/page/quote 映射 |

单个上传错误以非 2xx 状态和 `{"error":{"code":"...","message":"..."}}` 返回。种子导入支持逐项成功或失败，因此 HTTP 200 仍需检查每项 `status` 和 `error`；失败项不生成文档。

修改协议后：

```powershell
Set-Location E:\VerifiAtlas\backend
uv run --locked python -m app.export_openapi
Set-Location E:\VerifiAtlas\frontend
npm.cmd run generate:api
```

## 验证

先运行最小相关测试，再执行完整检查：

```powershell
Set-Location E:\VerifiAtlas\backend
uv run --locked pytest tests/test_ingest.py -k "ingest_pages or duplicate_upload"
uv run --locked pytest

Set-Location E:\VerifiAtlas\frontend
npm.cmd run typecheck
npm.cmd run build
```

真实语料检查（需后端运行，会将官方论文下载到本机）：

```powershell
Set-Location E:\VerifiAtlas\backend
uv run --locked python scripts/verify_d1_live.py --import-seeds
```

脚本检查原 PDF SHA256、实际页数、每个片段的页码/字符范围和真实 PDF 重传去重；不调用 LLM，不把论文原文写入验证报告。结果默认保存到 `E:\VerifiAtlas\artifacts\d1\live-check.json`。不加 `--import-seeds` 可仅核对当前已导入文档。

真实问答 smoke test（后端运行、已导入官方 KG²RAG，默认会实际请求 DeepSeek）：

```powershell
Set-Location E:\VerifiAtlas\backend
uv run --locked python scripts/verify_d2_live.py
```

结果保存到 `E:\VerifiAtlas\artifacts\d2\live-check.json`。已有浏览器问答 run ID 时，可加 `--run-id <ID>` 复核记录，不再次调用 LLM。

实际验证记录见 [D1 验证记录](docs/D1_VERIFICATION.md)、[D2 验证记录](docs/D2_VERIFICATION.md)。自动测试里的合成 PDF 及 LLM Stub 仅用于测试；不使用真实密钥，不调用付费接口。至少 5 个标注问题见 [evaluation_questions.md](samples/evaluation_questions.md)，尚未执行的问题有明确标记。

## 论文与技术来源

元数据清单为 [samples/papers.json](samples/papers.json)，本地导入不代表获得 PDF 再分发许可，仓库不包含论文原文件。

- [KG²RAG，NAACL 2025 官方页面](https://aclanthology.org/2025.naacl-long.449/)
- [LightRAG，arXiv v3](https://arxiv.org/abs/2410.05779v3)（2024 年首发，2025 年修订）
- [PaperQA2，arXiv v2](https://arxiv.org/abs/2409.13740v2)
- [Vue](https://vuejs.org/)、[Vite](https://vite.dev/)、[FastAPI](https://fastapi.tiangolo.com/)、[pypdf](https://pypdf.readthedocs.io/)

当前只导入这些论文作为可核对语料，没有集成或复现 KG²RAG、LightRAG 或 PaperQA2 的算法实现。
