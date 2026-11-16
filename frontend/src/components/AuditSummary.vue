<script setup lang="ts">
import type { Citation, QueryResult } from '../api/client'
import { computed } from 'vue'

const props = defineProps<{ result: QueryResult }>()
const emit = defineEmits<{ source: [citation: Citation] }>()
const requirements = computed(() => props.result.requirements ?? [])
const trace = computed(() => props.result.trace ?? [])
const stopLabels: Record<string, string> = {
  all_supported: '全部需求已有引用支持', covered_after_repair: '补检后需求已有引用支持',
  repair_exhausted: '一轮补检已结束，仍有证据缺口', repair_disabled: '本次关闭定向补检',
  agent_timeout: '本轮时间预算已用完', agent_request_budget: '本轮请求预算已用完',
}

function sourceFor(evidenceId: string) {
  const citation = props.result.citations.find((item) => item.evidence_id === evidenceId)
  if (citation) emit('source', citation)
}
</script>

<template>
  <section v-if="requirements.length" class="audit-summary" aria-label="证据需求审计">
    <div class="section-heading"><h3>证据需求</h3><span class="muted">{{ result.stats.supported_requirements }} / {{ result.stats.total_requirements }} 项有引用支持 · 补检 {{ result.stats.repair_rounds }} 轮</span></div>
    <p class="muted audit-stop">{{ stopLabels[result.stats.stop_reason ?? ''] ?? '执行受阻，详见下方轨迹' }}</p>
    <p v-if="!result.audit_version" class="message warning">这是旧版审计记录，未包含新增的术语与数值匹配检查；建议重新执行问题。</p>
    <ol class="requirement-list"><li v-for="requirement in requirements" :key="requirement.id">
      <div class="requirement-heading"><span class="requirement-status" :class="requirement.status">{{ requirement.status === 'supported' ? '✓ 有引用支持' : requirement.status === 'pending' ? '○ 待核查' : '△ 证据不足' }}</span><strong>{{ requirement.text }}</strong></div>
      <p class="muted">{{ requirement.explanation }}</p>
      <button v-for="evidenceId in requirement.evidence_ids" :key="evidenceId" class="text-button" @click="sourceFor(evidenceId)">核对支持片段 ↗</button>
    </li></ol>
    <p class="muted graph-note">本次来源关系：{{ result.graph?.nodes?.length ?? 0 }} 个节点、{{ result.graph?.edges?.length ?? 0 }} 条关系。{{ result.graph?.note }}</p>
    <details class="trace-details"><summary>本次执行轨迹 · {{ trace.length }} 项实际事件</summary><p class="muted">以下是执行完成后的真实记录，不是实时进度或模型思维过程。</p><ol class="trace-list"><li v-for="event in trace" :key="event.step"><span class="trace-step">{{ event.step }}</span><span>{{ event.description }}</span></li></ol></details>
  </section>
</template>

<style scoped>
.audit-summary { margin: 20px 0; border-top: 1px solid var(--line); padding-top: 20px; }
.audit-stop { margin: 8px 0; }
.requirement-list { list-style: none; margin: 0; padding: 0; }
.requirement-list li { padding: 14px 0; border-bottom: 1px solid var(--line); }
.requirement-heading { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 14px; }
.requirement-heading strong { font-size: 13px; font-weight: 500; }
.requirement-status { font-size: 12px; white-space: nowrap; }
.requirement-status.supported { color: var(--supported); }
.requirement-status.insufficient { color: var(--gap); }
.requirement-status.pending { color: var(--muted); }
.requirement-list p { margin: 6px 0; overflow-wrap: anywhere; }
.graph-note { margin-top: 16px; }
.trace-details { margin-top: 16px; font-size: 12px; }
.trace-details > p { margin-top: 12px; }
.trace-list { list-style: none; margin: 12px 0 0; padding: 0; }
.trace-list li { display: flex; gap: 12px; padding: 7px 0; overflow-wrap: anywhere; }
.trace-step { color: var(--muted); font-family: monospace; width: 24px; flex-shrink: 0; }
</style>
