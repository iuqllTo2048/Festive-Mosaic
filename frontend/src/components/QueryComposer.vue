<script setup lang="ts">
import { ref } from 'vue'
export type ResearchOptions = { onlyCurrent: boolean; audited: boolean; repair: boolean }
defineProps<{ busy: boolean; documentCount: number; selectedId: string; configured: boolean; model: string; restoring: boolean }>()
const question = defineModel<string>({ required: true })
const emit = defineEmits<{ submit: [options: ResearchOptions] }>()
const onlyCurrent = ref(false)
const audited = ref(true)
const repair = ref(true)
defineExpose({ setMode: (mode: string) => { audited.value = mode === 'audited' } })
</script>
<template>
  <section class="query-composer" aria-labelledby="research-heading"><div class="composer-heading"><h1 id="research-heading">研究问题</h1><span class="muted">{{ configured ? model : '问答 API 未配置' }}</span></div><form @submit.prevent="emit('submit',{onlyCurrent,audited,repair})"><label for="research-question" class="sr-only">研究问题</label><div class="question-input"><textarea id="research-question" v-model="question" :disabled="busy" maxlength="2000" rows="2" placeholder="提出研究问题，从论文原文检索证据…"></textarea><button class="primary" type="submit" :disabled="busy || !documentCount">{{ busy ? restoring ? '读取中…' : '检索中…' : '开始检索' }} ↗</button></div><details class="search-settings"><summary>{{ audited ? '证据需求审计' : '基础问答' }} · {{ audited && repair ? '允许一次补检 · ' : '' }}{{ onlyCurrent ? '当前论文' : '全部语料' }}</summary><div><label><input v-model="onlyCurrent" type="checkbox" :disabled="busy || !selectedId" /> 仅检索当前论文</label><label><input v-model="audited" type="checkbox" :disabled="busy" /> 拆解需求并审计</label><label v-if="audited"><input v-model="repair" type="checkbox" :disabled="busy" /> 允许一次补检</label><p>问题与每轮至多 8 个片段会发送到 DeepSeek；审计模式可能多次请求模型。</p></div></details></form></section>
</template>
