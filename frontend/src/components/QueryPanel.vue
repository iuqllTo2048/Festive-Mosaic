<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { request, type Citation, type QueryResult } from '../api/client'
import AuditSummary from './AuditSummary.vue'

defineProps<{ documentCount: number; selectedId: string; configured: boolean; model: string }>()
const emit = defineEmits<{ source: [citation: Citation] }>()
const question = ref('')
const currentOnly = ref(false)
const audited = ref(true)
const repair = ref(true)
const busy = ref(false)
const restoring = ref(false)
const error = ref('')
const result = ref<QueryResult | null>(null)

async function ask(selectedId: string) {
  if (!question.value.trim()) { error.value = '请输入研究问题。'; return }
  busy.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await request<QueryResult>('/api/query', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question.value.trim(), document_ids: currentOnly.value ? [selectedId] : null,
        mode: audited.value ? 'audited' : 'basic', enable_repair: repair.value }),
    })
    const url = new URL(window.location.href)
    url.searchParams.set('run', result.value.run_id)
    try { window.history.replaceState(null, '', url) } catch { /* Answer remains available without URL persistence. */ }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '本次未能生成回答，请重试。'
  } finally { busy.value = false }
}

onMounted(async () => {
  const runId = new URLSearchParams(window.location.search).get('run')
  if (!runId) return
  if (!/^[0-9a-f-]{36}$/i.test(runId)) { error.value = '问答记录编号不正确。'; return }
  busy.value = true
  restoring.value = true
  try {
    result.value = await request<QueryResult>(`/api/runs/${runId}`)
    question.value = result.value.question
    audited.value = result.value.mode === 'audited'
  } catch (cause) { error.value = cause instanceof Error ? cause.message : '读取问答记录失败。' }
  finally { busy.value = false; restoring.value = false }
})

function openSource(id: string) {
  const citation = result.value?.citations.find((item) => item.id === id)
  if (citation) emit('source', citation)
}
</script>

<template>
  <section class="query-panel" aria-labelledby="query-heading">
    <div class="section-heading"><h2 id="query-heading">向论文提问</h2><span class="muted">{{ configured ? `DeepSeek · ${model}` : '尚未配置 DeepSeek API Key' }}</span></div>
    <p class="muted query-description">基于本地语料检索。提问会将问题与每轮至多 8 个匹配片段发送到 DeepSeek；审计模式可能多次请求模型。</p>
    <form @submit.prevent="ask(selectedId)">
      <label class="sr-only" for="research-question">研究问题</label>
      <textarea id="research-question" v-model="question" :disabled="busy" maxlength="2000" rows="2" placeholder="例如：KG2RAG 在 HotpotQA 上评估了哪些内容？请给出原文引用。"></textarea>
      <div class="query-controls"><label><input v-model="currentOnly" type="checkbox" :disabled="busy || !selectedId" /> 仅检索当前选中的论文</label><button class="primary" :disabled="busy || !documentCount" type="submit">{{ busy ? restoring ? '正在读取记录…' : '检索与生成中…' : '检索并回答' }}</button></div>
      <div class="query-options"><label><input v-model="audited" type="checkbox" :disabled="busy" /> 拆解证据需求并审计</label><label v-if="audited"><input v-model="repair" type="checkbox" :disabled="busy" /> 允许一次定向补检</label><span v-else class="muted">基础问答只做一次词面检索，英文论文建议保留英文术语。</span></div>
    </form>
    <p v-if="!documentCount" class="muted">先添加至少一篇文本型 PDF。</p>
    <p v-if="busy" class="message" role="status">{{ restoring ? '正在读取已保存的问答记录，不会再次请求 DeepSeek。' : audited ? '正在规划需求、检索与审计。完成后显示真实轨迹；定向补检最多一轮。' : '正在检索原文并请求 DeepSeek，完成后核对引文位置。' }}</p>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>
    <section v-if="result" class="query-answer" aria-label="问答结果" aria-live="polite">
      <div class="section-heading"><h3>{{ result.status === 'answered' ? '基于原文的回答' : '当前证据不足' }}</h3><span class="muted">检索 {{ result.stats.retrieved_chunks }} 个片段 · {{ (result.stats.duration_ms / 1000).toFixed(1) }} 秒</span></div>
      <p class="muted submitted-question">本次问题：{{ result.question }}</p>
      <p v-for="(paragraph, index) in result.paragraphs" :key="index" class="answer-paragraph">{{ paragraph.text }} <button v-for="id in paragraph.citation_ids" :key="id" class="citation-button" :aria-label="`查看引用 ${id} 原文`" @click="openSource(id)">[{{ id }}]</button></p>
      <p v-if="!result.paragraphs.length" class="answer-paragraph">{{ result.answer }}</p>
      <AuditSummary :result="result" @source="emit('source', $event)" />
      <div v-if="result.insufficient.length" class="message warning"><strong>证据限制</strong><ul><li v-for="item in result.insufficient" :key="item">{{ item }}</li></ul></div>
      <details v-if="result.citations.length" open><summary>引用来源 · {{ result.citations.length }} 条</summary><ol class="citation-list"><li v-for="citation in result.citations" :key="citation.id"><div><strong>[{{ citation.id }}] {{ citation.document_title }}</strong><span class="muted"> · PDF 第 {{ citation.page }} 页</span></div><blockquote>{{ citation.quote }}</blockquote><div class="citation-actions"><button @click="emit('source', citation)">定位原文片段</button><a :href="citation.pdf_url" target="_blank" rel="noopener noreferrer">打开 PDF 对应页 ↗</a></div></li></ol></details>
      <p class="muted audit-note">已核对引用文字确实存在于来源片段中；这不等于已经验证科学结论。模型仍可能误读语境，请复核原文。</p>
      <details><summary>问答记录标识</summary><code>{{ result.run_id }}</code></details>
    </section>
  </section>
</template>
