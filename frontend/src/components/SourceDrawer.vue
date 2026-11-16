<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { request, type Chunk, type ChunkPage, type Document } from '../api/client'

const props = defineProps<{ documents: Document[] }>()
const dialog = ref<HTMLDialogElement | null>(null)
const documentId = ref('')
const document = computed(() => props.documents.find((item) => item.id === documentId.value))
const page = ref(1)
const offset = ref(0)
const chunks = ref<ChunkPage | null>(null)
const focused = ref<Chunk | null>(null)
const quote = ref('')
const busy = ref(false)
const error = ref('')
let generation = 0

async function loadPage() {
  const current = ++generation
  focused.value = null
  quote.value = ''
  busy.value = true
  error.value = ''
  try {
    const result = await request<ChunkPage>(`/api/documents/${documentId.value}/chunks?page=${page.value}&offset=${offset.value}&limit=20`)
    if (current === generation) chunks.value = result
  } catch (cause) { if (current === generation) error.value = cause instanceof Error ? cause.message : '读取原文失败。' }
  finally { if (current === generation) busy.value = false }
}

async function open(id: string, chunkId?: string, sourceQuote = '', sourcePage = 1) {
  const current = ++generation
  documentId.value = id
  page.value = sourcePage
  offset.value = 0
  focused.value = null
  chunks.value = null
  quote.value = sourceQuote
  error.value = ''
  busy.value = false
  await nextTick()
  if (!dialog.value?.open) dialog.value?.showModal()
  if (!document.value) { error.value = '原文文档不在当前语料中，请刷新语料列表。'; return }
  if (!chunkId) { await loadPage(); return }
  busy.value = true
  try {
    const chunk = await request<Chunk>(`/api/chunks/${encodeURIComponent(chunkId)}`)
    if (chunk.document_id !== id) throw new Error('来源片段与文档不一致。')
    if (current === generation) { focused.value = chunk; page.value = chunk.page_number }
  } catch (cause) { if (current === generation) error.value = cause instanceof Error ? cause.message : '读取引用片段失败。' }
  finally { if (current === generation) busy.value = false }
}

function changePage(event: Event) { page.value = Number((event.target as HTMLSelectElement).value); offset.value = 0; void loadPage() }
function close() { generation++; busy.value = false; dialog.value?.close() }
defineExpose({ open })
</script>

<template>
  <dialog ref="dialog" class="source-drawer" aria-labelledby="source-title" @cancel="generation++; busy = false">
    <div class="drawer-heading"><div><p class="eyebrow">SOURCE / 原文核对</p><h2 id="source-title">{{ document?.title ?? '来源不可用' }}</h2></div><button autofocus type="button" @click="close">关闭来源</button></div>
    <div class="source-body">
      <template v-if="document">
        <p class="muted">{{ document.original_filename }} · {{ document.page_count }} 页 · {{ document.authors.join(', ') || '作者信息未提供' }}<template v-if="document.year"> · {{ document.year }}</template></p>
        <a v-if="document.source_url" :href="document.source_url" target="_blank" rel="noopener noreferrer">官方文献页面 ↗</a>
        <p v-for="warning in document.warnings" :key="warning" class="message warning">{{ warning }}</p>
        <div class="source-toolbar"><label for="source-page">实际页码</label><select id="source-page" :value="page" @change="changePage"><option v-for="number in document.page_count" :key="number" :value="number">第 {{ number }} 页</option></select><a class="button-link" :href="`${document.pdf_url}#page=${page}`" target="_blank" rel="noopener noreferrer">打开 PDF 对应页 ↗</a><a :href="document.pdf_url" :download="document.original_filename">下载 PDF</a></div>
      </template>
      <p v-if="busy" class="message" role="status">正在读取真实原文…</p>
      <p v-if="error" class="message error" role="alert">{{ error }} <button class="text-button" @click="loadPage">重试</button></p>
      <template v-else-if="!busy">
        <article v-if="focused" class="source-fragment"><p class="fragment-meta">引用定位 · PDF 第 {{ focused.page_number }} 页 · 片段 {{ focused.order + 1 }}</p><blockquote v-if="quote" class="source-quote">{{ quote }}</blockquote><p class="source-text">{{ focused.text }}</p><details><summary>片段标识与字符范围</summary><code>{{ focused.id }}<br />{{ focused.char_start }}–{{ focused.char_end }}</code></details><button class="text-button" @click="loadPage">查看本页其他片段</button></article>
        <template v-else-if="chunks"><p v-if="!chunks.total" class="message warning">本页未提取到文本，可能为空白或扫描图片。暂不支持 OCR，请查看原 PDF。</p><article v-for="chunk in chunks.items" :key="chunk.id" class="source-fragment"><p class="fragment-meta">PDF 第 {{ chunk.page_number }} 页 · 片段 {{ chunk.order + 1 }}</p><p class="source-text">{{ chunk.text }}</p><details><summary>片段标识</summary><code>{{ chunk.id }}</code></details></article><nav v-if="chunks.total > chunks.limit" class="pagination" aria-label="原文片段翻页"><button :disabled="offset === 0" @click="offset = Math.max(0, offset - 20); loadPage()">上一批</button><span>{{ offset + 1 }}–{{ Math.min(offset + 20, chunks.total) }} / {{ chunks.total }}</span><button :disabled="offset + 20 >= chunks.total" @click="offset += 20; loadPage()">下一批</button></nav></template>
      </template>
      <p class="source-footnote muted">页码按 PDF 实际页面计算，可能与印刷页码不同。文本解析可能影响公式和分栏，请以原 PDF 为核对依据。</p>
    </div>
  </dialog>
</template>
