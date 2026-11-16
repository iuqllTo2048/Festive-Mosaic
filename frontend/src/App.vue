<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { request, uploadPdf, type ChunkPage, type Document, type Health, type SeedPaper, type SeedResult } from './api/client'
import { useTheme } from './theme'

const { theme, toggleTheme } = useTheme()

const documents = ref<Document[]>([])
const papers = ref<SeedPaper[]>([])
const health = ref<Health | null>(null)
const selectedId = ref('')
const selected = computed(() => documents.value.find((document) => document.id === selectedId.value))
const page = ref(1)
const offset = ref(0)
const chunks = ref<ChunkPage | null>(null)
const loading = ref(true)
const chunksLoading = ref(false)
const error = ref('')
const chunkError = ref('')
const notice = ref('')
const seeding = ref('')
const seedResults = ref<SeedResult[]>([])
const dialog = ref<HTMLDialogElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const uploadFile = ref<File | null>(null)
const uploadError = ref('')
const uploading = ref(false)
const progress = ref(0)
const maxUpload = computed(() => health.value?.max_upload_mb ?? 20)
let chunkController: AbortController | undefined

async function refresh(preferredId = selectedId.value) {
  loading.value = true
  error.value = ''
  try {
    const [status, items, manifest] = await Promise.all([
      request<Health>('/api/health'), request<Document[]>('/api/documents'), request<SeedPaper[]>('/api/papers'),
    ])
    health.value = status
    documents.value = items
    papers.value = manifest
    selectedId.value = items.some((item) => item.id === preferredId) ? preferredId : (items[0]?.id ?? '')
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '加载失败，请重试。'
    health.value = null
  } finally {
    loading.value = false
  }
}

async function loadChunks() {
  chunkController?.abort()
  chunks.value = null
  chunkError.value = ''
  if (!selectedId.value) { chunksLoading.value = false; return }
  const controller = new AbortController()
  chunkController = controller
  chunksLoading.value = true
  const timer = window.setTimeout(() => controller.abort(), 30_000)
  try {
    chunks.value = await request<ChunkPage>(
      `/api/documents/${selectedId.value}/chunks?page=${page.value}&offset=${offset.value}&limit=20`,
      { signal: controller.signal },
    )
  } catch (cause) {
    if (chunkController !== controller) return
    chunkError.value = cause instanceof Error && cause.name !== 'AbortError' ? cause.message : '读取超时，请重试。'
  } finally {
    window.clearTimeout(timer)
    if (chunkController === controller) chunksLoading.value = false
  }
}

watch(selectedId, () => { page.value = 1; offset.value = 0 })
watch([selectedId, page, offset], loadChunks)

function openUpload() {
  uploadFile.value = null
  uploadError.value = ''
  progress.value = 0
  dialog.value?.showModal()
  nextTick(() => fileInput.value?.focus())
}

function chooseFile(event: Event) {
  uploadFile.value = (event.target as HTMLInputElement).files?.[0] ?? null
  uploadError.value = ''
}

async function upload() {
  const file = uploadFile.value
  if (!file) { uploadError.value = '请先选择 PDF 文件。'; return }
  if (!file.name.toLowerCase().endsWith('.pdf')) { uploadError.value = '仅支持 .pdf 文件。'; return }
  if (!file.size) { uploadError.value = '文件为空，请重新选择 PDF。'; return }
  if (file.size > maxUpload.value * 1024 * 1024) { uploadError.value = `文件超过 ${maxUpload.value} MB 限制。`; return }
  uploading.value = true
  uploadError.value = ''
  progress.value = 0
  notice.value = ''
  try {
    const result = await uploadPdf(file, (value) => { progress.value = value })
    notice.value = result.duplicate ? '该 PDF 已导入，已定位到已有文档。' : `已解析 ${result.document.page_count} 页，保存 ${result.document.chunk_count} 个文本片段。`
    dialog.value?.close()
    await refresh(result.document.id)
    await loadChunks()
  } catch (cause) {
    uploadError.value = cause instanceof Error ? cause.message : '上传失败，请重试。'
  } finally { uploading.value = false }
}

async function seed(paperId: string) {
  seeding.value = paperId
  seedResults.value = []
  notice.value = ''
  error.value = ''
  try {
    seedResults.value = await request<SeedResult[]>('/api/documents/seed', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ paper_ids: [paperId] }),
    })
    const imported = seedResults.value.find((result) => result.document)
    await refresh(imported?.document?.id)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '导入失败，请从官方页面下载后上传。'
  } finally { seeding.value = '' }
}

function movePage(event: Event) {
  page.value = Number((event.target as HTMLSelectElement).value)
  offset.value = 0
}

onMounted(() => refresh())
</script>

<template>
  <header class="app-header">
    <a class="brand" href="/" aria-label="VerifiAtlas 工作台"><span class="brand-mark" aria-hidden="true">V<span>A</span></span><strong>VerifiAtlas</strong></a>
    <span class="header-label">科研证据工作台</span>
    <span class="connection" :class="{ connected: health }"><span aria-hidden="true">●</span> {{ health ? '本地服务已连接' : loading ? '连接中' : '本地服务未连接' }}</span>
    <button class="theme-toggle" type="button" :aria-label="theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'" @click="toggleTheme"><span aria-hidden="true">{{ theme === 'dark' ? '☼' : '☾' }}</span><span>{{ theme === 'dark' ? '浅色' : '深色' }}</span></button>
  </header>

  <main>
    <section class="page-heading">
      <div><p class="eyebrow">项目语料 / DOCUMENTS</p><h1>从可核对的原文开始</h1><p class="muted">添加文本型 PDF，按实际页码检查解析结果。</p></div>
      <button class="primary" @click="openUpload">＋ 上传论文</button>
    </section>

    <p v-if="error" class="message error" role="alert">{{ error }} <button class="text-button" @click="refresh()">重新连接</button></p>
    <p v-if="notice" class="message success" role="status">{{ notice }}</p>

    <div class="document-layout">
      <aside class="library" aria-label="项目语料">
        <div class="section-heading"><h2>已导入论文 <span class="count">{{ documents.length }}</span></h2><button class="text-button" :disabled="loading" @click="refresh()">刷新</button></div>
        <p v-if="loading && !documents.length" class="empty-small" role="status">正在读取本地语料…</p>
        <p v-else-if="!documents.length" class="empty-small">{{ error ? '语料暂不可读取，请检查服务连接。' : '尚未添加论文。上传 PDF，或从下方官方来源导入。' }}</p>
        <ul v-else class="document-list">
          <li v-for="document in documents" :key="document.id">
            <button class="document-item" :class="{ selected: selectedId === document.id }" :aria-current="selectedId === document.id ? 'true' : undefined" @click="selectedId = document.id">
              <span class="file-symbol" aria-hidden="true">PDF</span>
              <span><strong>{{ document.title }}</strong><span class="document-meta">{{ document.page_count }} 页 · {{ document.chunk_count }} 个片段</span><span class="status-label" :class="{ warning: document.warnings.length }">{{ document.warnings.length ? '△ 部分页无文本' : '✓ 文本已解析' }}</span></span>
            </button>
          </li>
        </ul>
        <div class="library-note"><strong>原文保存在本机</strong><p>页码按 PDF 实际页面计算，可能与论文印刷页码不同。当前阶段支持文本解析与来源检查。</p></div>
      </aside>

      <section class="reader" aria-label="原文片段" :aria-busy="chunksLoading">
        <template v-if="selected">
          <div class="reader-heading"><p class="eyebrow">原文检查 / SOURCE TEXT</p><h2>{{ selected.title }}</h2><p class="muted filename">{{ selected.original_filename }} · {{ selected.page_count }} 页 · {{ selected.chunk_count }} 个片段</p>
            <p v-if="selected.authors.length" class="muted">{{ selected.authors.join(', ') }}<template v-if="selected.year"> · {{ selected.year }}</template></p>
            <a v-if="selected.source_url" :href="selected.source_url" target="_blank" rel="noopener noreferrer">官方文献页面 ↗</a>
          </div>
          <div v-if="selected.warnings.length" class="message warning"><strong>△ 解析提醒</strong><ul><li v-for="warning in selected.warnings" :key="warning">{{ warning }}</li></ul></div>
          <div class="page-toolbar"><label for="page-number">实际页码 <select id="page-number" :value="page" @change="movePage"><option v-for="number in selected.page_count" :key="number" :value="number">第 {{ number }} 页</option></select></label><a class="button-link" :href="`${selected.pdf_url}#page=${page}`" target="_blank" rel="noopener noreferrer">打开 PDF · 第 {{ page }} 页 ↗</a></div>
          <p v-if="chunksLoading" class="empty-small" role="status">正在读取原文片段…</p>
          <p v-else-if="chunkError" class="message error" role="alert">{{ chunkError }} <button class="text-button" @click="loadChunks">重试</button></p>
          <template v-else-if="chunks">
            <p class="fragment-summary">第 {{ page }} 页 · {{ chunks.total }} 个文本片段<span v-if="chunks.total > 1"> · 长文本按 800 字符分块，相邻片段重叠 100 字符</span></p>
            <p v-if="!chunks.total" class="empty-small">本页未提取到文本。可能为空白或扫描图片；暂不支持 OCR，可打开原 PDF 检查。</p>
            <article v-for="chunk in chunks.items" :key="chunk.id" class="fragment"><div class="fragment-meta"><strong>片段 {{ chunk.order + 1 }}</strong><span>第 {{ chunk.page_number }} 页 · 字符 {{ chunk.char_start }}–{{ chunk.char_end }}</span></div><p class="source-text">{{ chunk.text }}</p><details><summary>片段标识</summary><code>{{ chunk.id }}</code></details></article>
            <nav v-if="chunks.total > chunks.limit" class="pagination" aria-label="片段翻页"><button :disabled="offset === 0" @click="offset = Math.max(0, offset - 20)">上一批</button><span>{{ offset + 1 }}–{{ Math.min(offset + chunks.limit, chunks.total) }} / {{ chunks.total }}</span><button :disabled="offset + chunks.limit >= chunks.total" @click="offset += 20">下一批</button></nav>
          </template>
        </template>
        <div v-else class="reader-empty"><span class="empty-document" aria-hidden="true">¶</span><h2>{{ error ? '等待连接本地语料' : '先添加一篇论文' }}</h2><p>{{ error ? '恢复服务连接后，可继续查看已保存的文档。' : '导入后，这里会按页呈现真实文本片段，并提供对应 PDF 来源。' }}</p><button @click="openUpload">选择 PDF 文件</button><span class="muted">仅支持文本型 PDF · 暂不支持 OCR</span></div>
      </section>
    </div>

    <section class="seed-section" aria-labelledby="seed-heading"><div class="section-heading"><div><h2 id="seed-heading">从真实论文开始</h2><p class="muted">官方来源清单 · 点击后才会下载并解析，文件仅保存在本机。</p></div></div>
      <p v-if="!papers.length" class="empty-small">{{ loading ? '正在读取官方来源清单…' : '连接本地服务后显示官方来源清单。' }}</p>
      <ul class="seed-list"><li v-for="paper in papers" :key="paper.id"><div><span class="paper-key">{{ paper.id === 'kg2rag' ? 'KG²RAG' : paper.id === 'lightrag' ? 'LightRAG' : 'PaperQA2' }} / {{ paper.year }}</span><h3>{{ paper.title }}</h3><p class="muted">{{ paper.authors[0] }} 等 · {{ paper.import_note }}</p></div><div class="seed-actions"><a :href="paper.source_url" target="_blank" rel="noopener noreferrer">官方页面 ↗</a><button :disabled="!!seeding || uploading || !health" @click="seed(paper.id)">{{ seeding === paper.id ? '正在下载并解析…' : '导入论文' }}</button></div></li></ul>
      <div v-for="result in seedResults" :key="result.paper_id" class="message" :class="result.status === 'failed' ? 'error' : 'success'" :role="result.status === 'failed' ? 'alert' : 'status'">{{ result.status === 'failed' ? result.error?.message : result.status === 'duplicate' ? '该论文已存在，已定位到已有文档。' : `已导入 ${result.document?.title}，共 ${result.document?.page_count} 页。` }} <a v-if="result.status === 'failed'" :href="result.manual_url" target="_blank" rel="noopener noreferrer">打开官方页面下载后上传 ↗</a></div>
    </section>
    <footer>VerifiAtlas · D1 语料与原文检查 <span>当前阶段尚未提供检索、AI 问答或证据图谱。</span></footer>
  </main>

  <dialog ref="dialog" aria-labelledby="upload-heading" @cancel="uploading && $event.preventDefault()">
    <form @submit.prevent="upload"><div class="section-heading"><h2 id="upload-heading">上传论文</h2><button type="button" :disabled="uploading" aria-label="关闭上传窗口" @click="dialog?.close()">关闭</button></div><p class="muted">选择文本型 PDF，系统将按实际页码解析并保存原文片段。</p><label class="file-picker" for="pdf-file">PDF 文件<input id="pdf-file" ref="fileInput" type="file" accept=".pdf,application/pdf" :disabled="uploading" @change="chooseFile" /></label><p class="muted">每个文件最多 {{ maxUpload }} MB / {{ health?.max_pdf_pages ?? 200 }} 页。加密文件和扫描件暂不支持。</p><p v-if="uploadError" class="message error" role="alert">{{ uploadError }}</p><div v-if="uploading" class="upload-progress" role="status"><progress :value="progress" max="100" aria-label="文件上传进度"></progress><p>{{ progress < 100 ? `正在上传 ${progress}%` : '文件上传完成，服务正在解析页面并保存…' }}</p></div><div class="dialog-actions"><button type="button" :disabled="uploading" @click="dialog?.close()">取消</button><button class="primary" :disabled="uploading || !!seeding" type="submit">{{ uploading ? '正在处理…' : '上传并解析' }}</button></div></form>
  </dialog>
</template>
