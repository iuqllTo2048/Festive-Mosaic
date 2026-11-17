<script setup lang="ts">
import { ref, watch } from 'vue'
import { guideExample, type GuideTask } from './cultural-guide.ts'
import { themes, claims } from './content.mjs'
const props=defineProps<{task:GuideTask|null; selected:string}>()
const emit=defineEmits<{ask:[question:string]; focus:[id:string]; source:[id:string]; graph:[]; compare:[]}>()
const question=ref(guideExample)
watch(()=>props.task?.question,value=>{if(value)question.value=value},{immediate:true})
const topicName=(id:string)=>themes.find(t=>t.id===id)?.name||id
const citationLabel=(task:GuideTask,id:string)=>`${task.evidence.find(e=>e.claim_id===id)?.source_id||'资料'} · ${claims.find(c=>c.id===id)?.practice||'关系'}`
</script>
<template>
  <aside class="agent-panel" aria-label="AI文化导览面板">
    <header class="agent-panel-heading"><div><p>AI 文化导览</p><h2>让问题，带你深入。</h2><span class="demo-pill">演示模式 · 未连接模型</span></div></header>
    <form class="guide-form" @submit.prevent="emit('ask',question)"><label for="guide-question">想了解什么地方文化？</label><textarea id="guide-question" v-model="question" rows="3" maxlength="500" placeholder="例如：苏州和汨罗的端午习俗有什么不同？"></textarea><div><span>{{question.length}} / 500</span><button class="button primary" :disabled="!question.trim()" type="submit">探索这个问题 ↗</button></div></form>
    <p class="guide-mode-note">本地摘编筛选与引用联动可操作。回答由既有资料拼接，未执行生成式回答。</p>
    <template v-if="task">
      <div class="guide-task-title"><span>当前探索主题</span><strong>{{task.question}}</strong><p>端午篇 / {{task.topic_ids.length?task.topic_ids.map(topicName).join('、'):'未定位地方范围'}}</p></div>
      <details class="guide-trace"><summary>执行记录 <span>本地 {{task.elapsed_ms}} ms · 模型调用 {{task.model_calls}}</span></summary><ol><li v-for="step in task.steps" :key="step.id" :data-state="step.state"><b>{{step.state==='done'?'✓':step.state==='failed'?'!':'—'}}</b><div><strong>{{step.label}}<small>{{step.state==='skipped'?'未执行':step.state==='failed'?'检查失败':'本地演示'}}</small></strong><p>{{step.detail}}</p></div></li></ol></details>
      <section class="guide-answer" aria-live="polite"><p class="guide-result-state" :data-status="task.status">{{task.status==='ready'?'摘编结果 · 待独立审读':task.status==='validation_failed'?'来源关联检查失败':'资料不足 · 暂不形成结论'}}</p><p v-for="gap in task.gaps" :key="gap" class="guide-gap">{{gap}}</p><article v-for="(answer,i) in task.answer" :key="i"><p>{{answer.text}}</p><button v-for="id in answer.claim_ids" :key="id" :aria-pressed="selected===id" :aria-label="'定位图谱：'+citationLabel(task,id)" @click="emit('focus',id)">{{citationLabel(task,id)}} ↗</button></article></section>
      <details class="guide-evidence" :open="task.status!=='ready'"><summary>检索到的摘编资料 <span>{{task.evidence.length}} 条</span></summary><article v-for="e in task.evidence" :key="e.claim_id"><button @click="emit('source',e.claim_id)"><b>{{e.source_id}} / {{topicName(e.topic_id)}}</b><span>{{e.title}}</span></button><blockquote>{{e.quote.map(q=>'“'+q+'”').join(' / ')}}</blockquote><small>来源字段已关联 · 语义未核验</small></article></details>
      <div class="guide-next"><button @click="emit('graph')">查看关联图谱 ↓</button><button v-if="task.topic_ids.length===2" @click="emit('compare')">对照这两个地方 ↗</button></div>
    </template>
    <div v-else class="guide-empty"><span>从一个具体问题开始</span><p>提交问题后，这里会呈现地方范围、实际执行记录、摘编回答和可点击引用。图谱使用同一批文化关系。</p><button @click="question='端午的故事，只发生在一天吗？'">试试：端午的节期有多长？ ↗</button></div>
  </aside>
</template>
