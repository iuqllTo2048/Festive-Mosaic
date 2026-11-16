<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Citation, QueryResult } from '../api/client'
import type { GraphView } from '../graph-model'
import { nodeNames } from '../graph-model'

const props = defineProps<{ result: QueryResult | null; graph: GraphView; selectedId: string | null; playback: boolean }>()
const emit = defineEmits<{ select: [id: string]; source: [citation: Citation]; openNode: [id: string]; close: [] }>()
const tab = ref<'requirements' | 'answer' | 'sources'>('requirements')
const selected = computed(() => props.graph.nodes.find((node) => node.id === props.selectedId))
const requirements = computed(() => (props.result?.requirements ?? []).filter((item) => !props.playback || props.graph.nodes.some((node) => node.id === item.id)))
const visibleCitations = computed(() => (props.result?.citations ?? []).filter((citation) => !props.playback || props.graph.edges.some((edge) => edge.provenance.evidence_id === citation.evidence_id)))
function status(id: string) { return props.graph.nodes.find((node) => node.id === id)?.status ?? 'pending' }
function sourcesFor(id: string) {
  const ids = props.result?.requirements?.find((item) => item.id === id)?.evidence_ids ?? []
  return visibleCitations.value.filter((citation) => citation.evidence_id && ids.includes(citation.evidence_id))
}
defineExpose({ showSources: () => { tab.value = 'sources' } })
</script>

<template>
  <aside class="audit-panel" aria-label="证据审计栏">
    <div class="panel-heading"><div><p class="eyebrow">EVIDENCE AUDIT</p><h2>证据审计</h2></div><button class="audit-close text-button" @click="emit('close')">收起</button></div>
    <div v-if="result && !playback && result.requirements?.length" class="coverage-line"><strong>{{ result.stats.supported_requirements }}<span> / {{ result.stats.total_requirements }}</span></strong><p>项需求有引用支持<br /><span class="muted">已补检 {{ result.stats.repair_rounds }} 轮 · 非可信度评分</span></p></div>
    <p v-if="playback" class="playback-banner">执行回放中 · 只展示已回放的证据状态</p>
    <div class="audit-tabs" role="tablist" aria-label="审计内容"><button id="tab-requirements" role="tab" :aria-selected="tab === 'requirements'" aria-controls="audit-content" @click="tab = 'requirements'">需求</button><button id="tab-answer" role="tab" :aria-selected="tab === 'answer'" aria-controls="audit-content" @click="tab = 'answer'">回答</button><button id="tab-sources" role="tab" :aria-selected="tab === 'sources'" aria-controls="audit-content" @click="tab = 'sources'">来源</button></div>
    <div id="audit-content" class="audit-content" role="tabpanel" :aria-labelledby="`tab-${tab}`">
      <section v-if="selected" class="selected-node"><p class="eyebrow">已聚焦 · {{ nodeNames[selected.type] }}</p><h3>{{ selected.label }}</h3><p v-if="selected.source_ref?.page" class="muted">实际 PDF 第 {{ selected.source_ref.page }} 页</p><button v-if="selected.type === 'chunk' || selected.type === 'paper' || selected.type === 'concept'" class="text-button" @click="emit('openNode', selected.id)">查看原文 ↗</button><p v-if="selected.type === 'concept'" class="muted">术语共现只表示检索关联，不是语义支持。</p></section>
      <p v-if="!result" class="panel-empty">输入研究问题后，这里会显示证据需求、原文引用与尚未解决的问题。</p>
      <template v-else-if="tab === 'requirements'">
        <p v-if="!requirements.length" class="panel-empty">{{ playback ? '尚未回放到需求规划事件。' : '这条基础问答记录未进行需求审计，可在回答与来源中查看结果。' }}</p>
        <ol class="requirements"><li v-for="(requirement,index) in requirements" :key="requirement.id" :class="{ active: selectedId === requirement.id }"><button class="requirement-select" @click="emit('select', requirement.id)"><span class="requirement-index">{{ String(index + 1).padStart(2,'0') }}</span><span><span class="status-label" :class="status(requirement.id)">{{ status(requirement.id) === 'supported' ? '✓ 有引用支持' : status(requirement.id) === 'insufficient' ? '△ 证据不足' : '○ 待核查' }}</span><strong>{{ requirement.text }}</strong></span></button><p class="muted requirement-explanation">{{ playback ? '状态来自当前回放事件；完整说明见执行结果。' : requirement.explanation }}</p><button v-for="citation in sourcesFor(requirement.id)" :key="citation.id" class="text-button source-shortcut" @click="emit('source', citation)">引用 [{{ citation.id }}] · 第 {{ citation.page }} 页 ↗</button></li></ol>
        <p v-if="result.audit_version === null || result.audit_version === undefined" class="message warning">旧版审计记录未包含新增的术语与数值保护，请重新核查。</p>
        <p class="audit-disclaimer">“有引用支持”是模型判断结合来源检查，不是科学事实认证。点击需求可聚焦对应的来源链。</p>
      </template>
      <template v-else-if="tab === 'answer'">
        <p v-if="playback" class="panel-empty">回放时不提前展示最终回答。点击“回到结果”查看完整结论。</p>
        <template v-else><p class="answer-caption">基于原文的回答</p><p v-for="(paragraph,index) in result.paragraphs" :key="index" class="answer-paragraph">{{ paragraph.text }} <button v-for="id in paragraph.citation_ids" :key="id" class="citation-button" :aria-label="`查看引用 ${id} 原文`" @click="result?.citations.find(c => c.id === id) && emit('source', result.citations.find(c => c.id === id)!)">[{{ id }}]</button></p><p v-if="!result.paragraphs.length" class="answer-paragraph">{{ result.answer }}</p><div v-if="result.insufficient.length" class="evidence-limits"><h3>尚未解决</h3><p v-for="item in result.insufficient" :key="item">{{ item }}</p></div></template>
      </template>
      <template v-else><p v-if="!visibleCitations.length" class="panel-empty">当前没有已核对的有效引用。证据不足的需求不会生成支持来源。</p><article v-for="citation in visibleCitations" :key="citation.id" class="audit-citation"><p class="citation-id">[{{ citation.id }}] · PDF 第 {{ citation.page }} 页</p><h3>{{ citation.document_title }}</h3><blockquote>{{ citation.quote }}</blockquote><button class="text-button" @click="emit('source',citation)">核对完整片段 ↗</button></article></template>
    </div>
    <p class="audit-footer muted">{{ result?.graph?.note ?? '来源可查，缺口保留。' }}</p>
  </aside>
</template>
