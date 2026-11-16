<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { request, uploadPdf, type Citation, type Document, type Health, type QueryResult, type SeedPaper, type SeedResult } from './api/client'
import { useTheme } from './theme'
import { graphFrame, evidencePath, nodeNames, edgeNames } from './graph-model'
import QueryComposer, { type ResearchOptions } from './components/QueryComposer.vue'
import EvidenceGraph from './components/EvidenceGraph.vue'
import AuditPanel from './components/AuditPanel.vue'
import SourceDrawer from './components/SourceDrawer.vue'
import TracePlayer from './components/TracePlayer.vue'

const { theme, toggleTheme } = useTheme()
const documents = ref<Document[]>([])
const papers = ref<SeedPaper[]>([])
const selectedDocumentId = ref('')
const health = ref<Health | null>(null)
const loading = ref(true)
const error = ref('')
const notice = ref('')
const seeding = ref('')
const question = ref('')
const result = ref<QueryResult | null>(null)
const busy = ref(false)
const restoring = ref(false)
const runError = ref('')
const selectedNodeId = ref<string | null>(null)
const cursor = ref(0)
const playing = ref(false)
const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
const narrow = window.matchMedia('(max-width: 999px)')
const auditBreakpoint = window.matchMedia('(max-width: 1279px)')
const reducedMotion = ref(motion.matches)
const viewMode = ref<'3d' | 'list'>(new URLSearchParams(location.search).get('view') === 'list' || narrow.matches ? 'list' : '3d')
const graphFailure = ref('')
const libraryOpen = ref(false)
const auditOpen = ref(false)
const sourceDrawer = ref<InstanceType<typeof SourceDrawer> | null>(null)
const graphComponent = ref<InstanceType<typeof EvidenceGraph> | null>(null)
const composer = ref<InstanceType<typeof QueryComposer> | null>(null)
const events = computed(() => result.value?.trace ?? [])
const playback = computed(() => !!result.value && cursor.value < events.value.length)
const graph = computed(() => graphFrame(result.value, playback.value ? cursor.value : null))
const path = computed(() => evidencePath(graph.value, selectedNodeId.value))
const selectedNode = computed(() => graph.value.nodes.find((node) => node.id === selectedNodeId.value))
const dialog = ref<HTMLDialogElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const uploadFile = ref<File | null>(null)
const uploadError = ref('')
const uploading = ref(false)
const progress = ref(0)
let timer = 0

async function refresh(preferredId = selectedDocumentId.value) {
  loading.value = true; error.value = ''
  try {
    const [status, items, manifest] = await Promise.all([request<Health>('/api/health'), request<Document[]>('/api/documents'), request<SeedPaper[]>('/api/papers')])
    health.value = status; documents.value = items; papers.value = manifest
    selectedDocumentId.value = items.some((item) => item.id === preferredId) ? preferredId : items[0]?.id ?? ''
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '读取语料失败。'; health.value = null }
  finally { loading.value = false }
}
function pause() { window.clearInterval(timer); playing.value = false }
function seek(value: number) { pause(); cursor.value = Math.max(0, Math.min(events.value.length,value)); selectedNodeId.value = null }
function finalResult() { seek(events.value.length) }
function play() {
  if (playing.value) { pause(); return }
  if (!events.value.length) return
  selectedNodeId.value = null
  if (cursor.value >= events.value.length) cursor.value = 0
  if (reducedMotion.value) { cursor.value = Math.min(cursor.value + 1, events.value.length); return }
  playing.value = true
  timer = window.setInterval(() => { cursor.value++; if (cursor.value >= events.value.length) pause() },750)
}
function acceptResult(value: QueryResult) { pause(); result.value = value; cursor.value = value.trace?.length ?? 0; selectedNodeId.value = null }
async function ask(options: ResearchOptions) {
  if (busy.value) return
  if (!question.value.trim()) { runError.value = '请输入研究问题。'; return }
  pause(); busy.value = true; runError.value = ''; result.value = null; selectedNodeId.value = null
  try {
    const value = await request<QueryResult>('/api/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:question.value.trim(),document_ids:options.onlyCurrent?[selectedDocumentId.value]:null,mode:options.audited?'audited':'basic',enable_repair:options.repair})})
    acceptResult(value)
    const url = new URL(location.href); url.searchParams.set('run',value.run_id)
    try { history.replaceState(null,'',url) } catch { /* Optional URL persistence. */ }
  } catch (cause) { runError.value = cause instanceof Error ? cause.message : '本次检索未完成，请重试。' }
  finally { busy.value = false }
}
async function restore() {
  const runId = new URLSearchParams(location.search).get('run')
  if (!runId) return
  if (!/^[0-9a-f-]{36}$/i.test(runId)) { runError.value = '问答记录编号不正确。'; return }
  busy.value = true; restoring.value = true
  try { const value = await request<QueryResult>(`/api/runs/${runId}`); question.value = value.question; acceptResult(value); await nextTick(); composer.value?.setMode(value.mode ?? 'basic') }
  catch (cause) { runError.value = cause instanceof Error ? cause.message : '读取记录失败。' }
  finally { busy.value = false; restoring.value = false }
}
function openDocument(id: string) { pause(); selectedDocumentId.value = id; libraryOpen.value = false; void sourceDrawer.value?.open(id) }
function openCitation(citation: Citation) { pause(); selectedDocumentId.value = citation.document_id; void sourceDrawer.value?.open(citation.document_id,citation.chunk_id,citation.quote,citation.page) }
function openNode(id: string) {
  const node = graph.value.nodes.find((item) => item.id === id)
  if (!node) return
  pause()
  if (node.type === 'paper') { selectedDocumentId.value = node.source_ref?.document_id ?? node.id; void sourceDrawer.value?.open(selectedDocumentId.value); return }
  const source = node.source_ref
  if (source?.document_id && source.chunk_id) { selectedDocumentId.value = source.document_id; void sourceDrawer.value?.open(source.document_id,source.chunk_id,source.term ?? '',source.page ?? 1) }
}
function selectNode(id: string) { selectedNodeId.value = id; const node = graph.value.nodes.find((item) => item.id === id); if (node?.type === 'chunk' || node?.type === 'paper') openNode(id); else auditOpen.value = true }
function chooseView(mode: '3d'|'list') { viewMode.value = mode; if (mode === '3d') graphFailure.value = '' }
function unavailable(message: string) { graphFailure.value = message; viewMode.value = 'list' }
function escape(event: KeyboardEvent) { if (event.key === 'Escape' && !document.querySelector('dialog[open]')) { selectedNodeId.value = null; auditOpen.value = false; libraryOpen.value = false } }
function motionChanged(event: MediaQueryListEvent) { reducedMotion.value = event.matches; if (event.matches) pause() }
function narrowChanged(event: MediaQueryListEvent) { if (event.matches) { viewMode.value = 'list'; libraryOpen.value = false } }
function auditBreakpointChanged() { auditOpen.value = false }
function visibilityChanged() { if (document.hidden) pause() }
function openUpload() { uploadFile.value = null; uploadError.value = ''; progress.value = 0; dialog.value?.showModal(); void nextTick(()=> fileInput.value?.focus()) }
function chooseFile(event: Event) { uploadFile.value = (event.target as HTMLInputElement).files?.[0] ?? null; uploadError.value = '' }
async function upload() {
  const file = uploadFile.value; const maximum = health.value?.max_upload_mb ?? 20
  if (!file) { uploadError.value = '请先选择 PDF。'; return }
  if (!file.name.toLowerCase().endsWith('.pdf')) { uploadError.value = '仅支持 .pdf 文件。'; return }
  if (!file.size) { uploadError.value = '文件为空，请重新选择 PDF。'; return }
  if (file.size > maximum * 1024 * 1024) { uploadError.value = `文件超过 ${maximum} MB 限制。`; return }
  uploading.value = true; uploadError.value = ''; progress.value = 0
  try { const value = await uploadPdf(file,(percent)=>{progress.value=percent}); notice.value = value.duplicate ? '该 PDF 已导入，已定位到已有论文。' : `已解析 ${value.document.page_count} 页，保存 ${value.document.chunk_count} 个片段。`; dialog.value?.close(); await refresh(value.document.id) }
  catch (cause) { uploadError.value = cause instanceof Error ? cause.message : '上传失败。' }
  finally { uploading.value = false }
}
async function seed(paper: SeedPaper) {
  seeding.value = paper.id; error.value = ''; notice.value = ''
  try {
    const values = await request<SeedResult[]>('/api/documents/seed',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paper_ids:[paper.id]})}); const value=values[0]
    if (value?.status==='failed') { error.value=value.error?.message ?? '导入失败，请从官方来源手动下载后上传。'; return }
    notice.value=value?.status==='duplicate'?'论文已存在。':'论文已导入。'; await refresh(value?.document?.id)
  } catch (cause) { error.value=cause instanceof Error?cause.message:'导入失败。' }
  finally { seeding.value='' }
}
watch(auditOpen,async(open,previous)=>{ if (!auditBreakpoint.matches) return; await nextTick(); document.querySelector<HTMLButtonElement>(open?'.audit-shell .audit-close':previous?'.audit-toggle':'[data-no-target]')?.focus() })
watch(libraryOpen,async(open,previous)=>{ if (!narrow.matches) return; await nextTick(); document.querySelector<HTMLButtonElement>(open?'.library .upload-trigger':previous?'.library-toggle':'[data-no-target]')?.focus() })
onMounted(()=>{ void refresh(); void restore(); window.addEventListener('keydown',escape); motion.addEventListener('change',motionChanged); narrow.addEventListener('change',narrowChanged); auditBreakpoint.addEventListener('change',auditBreakpointChanged); document.addEventListener('visibilitychange',visibilityChanged) })
onBeforeUnmount(()=>{ pause(); window.removeEventListener('keydown',escape); motion.removeEventListener('change',motionChanged); narrow.removeEventListener('change',narrowChanged); auditBreakpoint.removeEventListener('change',auditBreakpointChanged); document.removeEventListener('visibilitychange',visibilityChanged) })
</script>

<template>
  <header class="app-header">
    <button class="library-toggle text-button" @click="libraryOpen=!libraryOpen">语料</button><a class="brand" href="/" aria-label="VerifiAtlas 工作台"><span class="brand-mark" aria-hidden="true">V<span>A</span></span><strong>VerifiAtlas</strong></a><span class="header-label">科研证据工作台</span><span class="connection" :class="{connected:health}"><span aria-hidden="true">●</span> {{ health?'本地服务已连接':loading?'连接中':'本地服务未连接' }}</span><button class="theme-toggle" :aria-label="theme==='dark'?'切换到浅色模式':'切换到深色模式'" @click="toggleTheme">{{ theme==='dark'?'☼ 浅色':'☾ 深色' }}</button><button class="audit-toggle" @click="auditOpen=!auditOpen">审计与来源</button>
  </header>
  <main class="workbench">
    <button v-if="libraryOpen" class="panel-scrim library-scrim" aria-label="收起语料栏" @click="libraryOpen=false"></button>
    <aside class="library" :class="{open:libraryOpen}" aria-label="项目语料">
      <div class="panel-heading"><div><p class="eyebrow">PROJECT CORPUS</p><h2>项目语料 <span class="count">{{ documents.length }}</span></h2></div><button class="text-button" :disabled="loading" @click="refresh()">刷新</button></div>
      <div class="library-actions"><button class="upload-trigger" @click="openUpload">＋ 上传论文</button><p>文本型 PDF · 原文保存在本机</p></div>
      <p v-if="error" class="message error" role="alert">{{ error }} <button class="text-button" @click="refresh()">重新连接</button></p><p v-if="notice" class="message success" role="status">{{ notice }}</p><p v-if="loading && !documents.length" class="panel-empty" role="status">读取本地语料…</p><p v-else-if="!documents.length" class="panel-empty">{{ error?'暂时无法读取语料。':'尚未添加论文。上传 PDF，或导入下方官方来源。' }}</p>
      <ul class="document-list"><li v-for="(item,index) in documents" :key="item.id"><button :class="{selected:selectedDocumentId===item.id}" @click="openDocument(item.id)"><span class="document-number">{{ String(index+1).padStart(2,'0') }}</span><span><strong>{{ item.title }}</strong><small>{{ item.year ?? '本机导入' }} · {{ item.page_count }} 页 · {{ item.chunk_count }} 片段</small><span class="status-label" :class="item.warnings.length?'insufficient':'supported'">{{ item.warnings.length?'△ 部分页无文本':'✓ 文本已解析' }}</span></span></button></li></ul>
      <div class="seed-library"><details><summary>导入官方论文 <span>3 篇来源</span></summary><article v-for="paper in papers" :key="paper.id"><h3>{{ paper.title }}</h3><div><a :href="paper.source_url" target="_blank" rel="noopener noreferrer">官方页面 ↗</a><button :disabled="!!seeding || !health || uploading" @click="seed(paper)">{{ seeding===paper.id?'导入中…':'导入' }}</button></div></article></details><p>来源页、实际页码与原文一起保留。未找到的证据不会补成结论。</p></div><footer class="library-footer">VERIFIATLAS <span>D4 · 交互工作台</span></footer>
    </aside>
    <section class="evidence-space" aria-label="研究工作区">
      <QueryComposer ref="composer" v-model="question" :busy="busy" :restoring="restoring" :document-count="documents.length" :selected-id="selectedDocumentId" :configured="health?.llm_configured ?? false" :model="health?.llm_model ?? ''" @submit="ask" />
      <p v-if="runError" class="message error workspace-message" role="alert">{{ runError }}</p><p v-if="busy" class="message workspace-message" role="status">{{ restoring?'读取已保存记录，不会再次调用模型。':'正在检索与审计；完成后呈现真实图谱和轨迹。' }}</p>
      <p v-if="result && question.trim() !== result.question" class="message workspace-message">图谱仍是上一条已完成问题的结果；开始检索后才会更新。</p>
      <div class="graph-workspace">
        <div class="graph-toolbar"><div><p class="eyebrow">EVIDENCE SPACE</p><h2>{{ viewMode==='3d'?'三维证据空间':'证据来源列表' }} <span v-if="result" class="graph-count">{{ graph.nodes.length }} 节点 · {{ graph.edges.length }} 关系</span></h2></div><div class="graph-controls"><div class="view-switch" role="group" aria-label="证据视图"><button :aria-pressed="viewMode==='3d'" @click="chooseView('3d')">3D</button><button :aria-pressed="viewMode==='list'" @click="chooseView('list')">列表</button></div><button v-if="viewMode==='3d'" class="text-button" @click="graphComponent?.reset()">重置视角</button></div></div>
        <div class="graph-legend" aria-label="图谱图例"><span><i class="legend-paper"></i>论文</span><span><i class="legend-chunk"></i>原文片段</span><span><i class="legend-concept"></i>术语</span><span><i class="legend-requirement supported"></i>有引用支持</span><span><i class="legend-requirement gap"></i>证据缺口</span></div>
        <p v-if="graph.truncated" class="graph-notice">仅显示部分节点（{{ graph.nodes.length }} / {{ graph.total }}）。</p><p v-if="graphFailure" class="message warning graph-notice" role="status">{{ graphFailure }}</p><div v-if="selectedNode" class="focus-bar"><span>来源链聚焦 · {{ selectedNode.label }} · {{ path.nodes.size }} 节点 / {{ path.edges.size }} 关系</span><button class="text-button" @click="selectedNodeId=null">清除 · Esc</button></div>
        <div class="graph-stage">
          <div v-if="!graph.nodes.length" class="graph-empty"><span class="empty-symbol" aria-hidden="true">◇</span><h2>{{ busy?'等待实际执行结果':playback?'回放起点':result?'这条记录没有图关系':'先添加论文，提出研究问题' }}</h2><p>{{ playback?'事件回放尚未产生节点。':result?'基础问答可在审计栏查看回答与引用，开启需求审计后可生成来源图。':'检索到的片段将连接到真实论文与证据需求，未解决的问题会保留为缺口。' }}</p><button v-if="!documents.length" @click="openUpload">上传第一篇论文</button><button v-else-if="result && !graph.nodes.length && !playback" @click="auditOpen=true">查看回答与来源</button></div>
          <EvidenceGraph v-else-if="viewMode==='3d'" ref="graphComponent" :data="graph" :selected-id="selectedNodeId" :theme="theme" :reduced-motion="reducedMotion" @select="selectNode" @clear="selectedNodeId=null" @unavailable="unavailable" />
          <div v-else class="graph-list" aria-label="图谱等价证据列表"><section v-for="type in (['requirement','paper','chunk','concept'] as const)" :key="type"><h3>{{ nodeNames[type] }} <span>{{ graph.nodes.filter(node=>node.type===type).length }}</span></h3><button v-for="node in graph.nodes.filter(node=>node.type===type)" :key="node.id" class="graph-list-node" :class="{selected:selectedNodeId===node.id,dim:path.nodes.size && !path.nodes.has(node.id)}" @click="selectNode(node.id)"><span class="node-type-mark" :class="[node.type,node.status]">{{ node.type==='requirement'?(node.status==='supported'?'✓':node.status==='insufficient'?'△':'○'):node.type==='paper'?'●':node.type==='chunk'?'▪':'·' }}</span><span>{{ node.label }}<small v-if="node.type==='requirement'">{{ node.status==='supported'?'有引用支持':node.status==='insufficient'?'证据不足':'待核查' }}</small><small v-else-if="node.source_ref?.page">PDF 第 {{ node.source_ref.page }} 页</small></span></button></section><details class="relation-list"><summary>关系明细 · {{ graph.edges.length }} 条</summary><ul><li v-for="edge in graph.edges" :key="edge.id"><span>{{ graph.nodes.find(node=>node.id===edge.source)?.label }} <b>{{ edgeNames[edge.type] }}</b> {{ graph.nodes.find(node=>node.id===edge.target)?.label }}</span><button v-if="edge.provenance.chunk_id && edge.provenance.document_id" class="text-button" @click="sourceDrawer?.open(edge.provenance.document_id,edge.provenance.chunk_id)">查看出处 ↗</button></li></ul></details></div>
        </div>
        <div class="graph-footnote"><span>{{ playback?'执行回放 · 图谱状态来自当前事件':result?`执行完成 · 后端耗时 ${(result.stats.duration_ms/1000).toFixed(1)} 秒`:'等待研究问题' }}</span><span>{{ viewMode==='3d'?'拖动旋转 · 滚轮缩放 · 点击查来源':'同一批真实节点与关系' }}</span></div>
      </div>
      <TracePlayer :events="events" :cursor="cursor" :playing="playing" :reduced-motion="reducedMotion" @seek="seek" @play="play" @final="finalResult" />
    </section>
    <button v-if="auditOpen" class="panel-scrim audit-scrim" aria-label="收起审计栏" @click="auditOpen=false"></button><div class="audit-shell" :class="{open:auditOpen}"><AuditPanel :result="result" :graph="graph" :selected-id="selectedNodeId" :playback="playback" @select="selectNode" @source="openCitation" @open-node="openNode" @close="auditOpen=false" /></div>
  </main>
  <SourceDrawer ref="sourceDrawer" :documents="documents" />
  <dialog ref="dialog" class="upload-dialog" aria-labelledby="upload-title" @cancel="uploading && $event.preventDefault()"><form @submit.prevent="upload"><div class="dialog-heading"><h2 id="upload-title">上传论文</h2><button type="button" :disabled="uploading" @click="dialog?.close()">关闭</button></div><p class="muted">逐页解析文本型 PDF，保留实际页码与来源。</p><label class="file-picker" for="pdf-file">PDF 文件<input id="pdf-file" ref="fileInput" type="file" accept=".pdf,application/pdf" :disabled="uploading" @change="chooseFile" /></label><p class="muted">每个文件最多 {{ health?.max_upload_mb ?? 20 }} MB / {{ health?.max_pdf_pages ?? 200 }} 页。暂不支持扫描件 OCR。</p><p v-if="uploadError" class="message error" role="alert">{{ uploadError }}</p><div v-if="uploading" class="upload-progress" role="status"><progress :value="progress" max="100" aria-label="文件上传进度"></progress><p>{{ progress<100?`正在上传 ${progress}%`:'文件上传完成，正在解析页面并保存…' }}</p></div><div class="dialog-actions"><button type="button" :disabled="uploading" @click="dialog?.close()">取消</button><button class="primary" type="submit" :disabled="uploading || !!seeding">{{ uploading?'处理中…':'上传并解析' }}</button></div></form></dialog>
</template>
