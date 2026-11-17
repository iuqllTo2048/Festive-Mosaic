<script setup lang="ts">
import { festivals, statusLabels } from './festivals.ts'
import { themes, questions } from './content.mjs'

defineProps<{ mode: 'portal' | 'festival' }>()
const emit = defineEmits<{
  festival: []
  explore: [dimension: 'memory' | 'practice' | 'time']
  theme: [id: string]
  guide: []
  compare: []
  archive: []
}>()
</script>

<template>
  <section class="rebuild-entry" aria-labelledby="entry-title">
    <p class="rebuild-status">前端展示重构准备</p>
    <h1 id="entry-title">{{ mode === 'portal' ? '同节异俗' : '端午专题' }}</h1>
    <p class="rebuild-intro">旧版展示与美术素材已撤下。文化资料与交互框架保留，以下入口可继续使用。</p>
    <div class="rebuild-actions" aria-label="保留的功能入口">
      <button class="button primary" @click="emit('guide')">文化导览 · 演示模式</button>
      <button class="button" @click="emit('explore', 'practice')">文化知识图谱</button>
      <button class="button" @click="emit('compare')">地方习俗对照</button>
      <button class="button" @click="emit('archive')">观察档案</button>
    </div>

    <template v-if="mode === 'portal'">
      <h2>节日目录</h2>
      <ul class="rebuild-directory">
        <li v-for="festival in festivals" :key="festival.festival_id">
          <button v-if="festival.status === 'published'" @click="emit('festival')">{{ festival.name }}专题 →</button>
          <span v-else>{{ festival.name }}</span>
          <small>{{ statusLabels[festival.status] }}</small>
        </li>
      </ul>
    </template>
    <template v-else>
      <h2>保留的地方资料</h2>
      <ul class="rebuild-directory">
        <li v-for="theme in themes" :key="theme.id">
          <button @click="emit('theme', theme.id)">{{ theme.full }} →</button>
          <small>{{ theme.source }}</small>
        </li>
      </ul>
      <h2>已有探索问题</h2>
      <div class="rebuild-questions">
        <button v-for="question in questions" :key="question.id" @click="emit('explore', question.id)">{{ question.title }} →</button>
      </div>
    </template>
    <p class="rebuild-note">当前导览使用本地摘编，尚未连接文化 Agent 或在线 RAG。此页仅用于保留功能入口，后续展示方案待重新设计。</p>
  </section>
</template>
