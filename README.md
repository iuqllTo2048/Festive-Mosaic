# VerifiAtlas——面向科研知识探索的智能交互可视化系统

科研证据工作台。当前只实现 **D1：工程与 PDF 数据闭环**：导入真实 PDF，按实际页码检查文本片段并打开原文件。后续开发严格按 [阶段计划](02_BUILD_PLAYBOOK.md#5-五个开发阶段每次只执行一个阶段完成后提交一次) 推进，每阶段完成后只提交一次。

界面品牌简称 VerifiAtlas；GitHub 仓库名保留 verifyAtlas。

## 当前能力

- 上传文本型 PDF，按实际页面解析、分块（800 字符、100 字符重叠），保留稳定文档/片段 ID、页码和字符范围。
- SQLite 持久化，原 PDF 保存在本机；SHA256 去重，重启后数据保留。
- 语料列表、逐页原文检查、片段分页、打开 PDF 对应页。
- 顶栏可切换浅色/深色主题，首次打开跟随系统；手动选择保存在当前浏览器，刷新后保留。禁用本地存储时仍可切换，但无法跨刷新保存。
- 3 篇官方论文来源清单，可分别一键导入；下载失败会报告原因并提供官方页面及手动上传入口。
- 空文件、错误格式、损坏 PDF、加密文件、过大文件和无可提取文本文件有明确错误。混合文档中没有文本的页面保留实际页码并显示警告；页面解析异常时整份导入失败。

**尚未实现**：BM25、DeepSeek、AI 问答、证据审计、补检、概念扩展、3D 图谱。D1 不需要 API Key。

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

上传只发送给本机后端。浏览器 PDF 阅读器通常支持 `#page=N`；若阅读器未自动定位，请手动输入该页码。文字提取可能受到字体编码、分栏和数学公式影响，原 PDF 始终是核对依据。

## 配置与本地数据

默认可直接运行。需要调整限制时，将 `backend/.env.example` 复制为 `backend/.env`：

```powershell
Set-Location E:\VerifiAtlas\backend
Copy-Item .env.example .env
```

| 设置 | 默认值 | 说明 |
| --- | --- | --- |
| `DATA_DIR` | `./data` | 相对路径固定相对于 `backend/`，不受启动目录影响 |
| `MAX_UPLOAD_MB` | `20` | PDF 文件大小上限 |
| `MAX_PDF_PAGES` | `200` | 实际页数上限 |
| `SEED_TIMEOUT_SECONDS` | `30` | 官方来源连接与读取超时 |

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

实际验证记录见 [D1 验证记录](docs/D1_VERIFICATION.md)。自动测试里的合成 PDF 仅用于测试，不是预置论文。

## 论文与技术来源

元数据清单为 [samples/papers.json](samples/papers.json)，本地导入不代表获得 PDF 再分发许可，仓库不包含论文原文件。

- [KG²RAG，NAACL 2025 官方页面](https://aclanthology.org/2025.naacl-long.449/)
- [LightRAG，arXiv v3](https://arxiv.org/abs/2410.05779v3)（2024 年首发，2025 年修订）
- [PaperQA2，arXiv v2](https://arxiv.org/abs/2409.13740v2)
- [Vue](https://vuejs.org/)、[Vite](https://vite.dev/)、[FastAPI](https://fastapi.tiangolo.com/)、[pypdf](https://pypdf.readthedocs.io/)

当前只导入这些论文作为可核对语料，没有集成或复现 KG²RAG、LightRAG 或 PaperQA2 的算法实现。
