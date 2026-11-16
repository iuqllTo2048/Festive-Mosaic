<script setup lang="ts">
import type { components } from '../api/schema'
defineProps<{ events: components['schemas']['TraceEvent'][]; cursor: number; playing: boolean; reducedMotion: boolean }>()
const emit = defineEmits<{ seek: [cursor: number]; play: []; final: [] }>()
</script>
<template>
  <section class="trace-player" aria-label="实际执行轨迹回放"><div class="trace-heading"><p><strong>执行回放</strong><span> · {{ cursor }} / {{ events.length }} 项事件</span></p><div><button :disabled="!events.length" @click="emit('play')">{{ reducedMotion ? '逐步回放' : playing ? '暂停' : cursor === events.length ? '开始回放' : '播放' }}</button><button :disabled="!events.length || cursor === events.length" @click="emit('final')">回到结果</button></div></div><div class="trace-slider"><button :disabled="cursor <= 0" aria-label="上一个执行事件" @click="emit('seek',cursor-1)">←</button><input type="range" min="0" :max="events.length" :value="cursor" :disabled="!events.length" aria-label="回放事件位置" @input="emit('seek',Number(($event.target as HTMLInputElement).value))" /><button :disabled="cursor >= events.length" aria-label="下一个执行事件" @click="emit('seek',cursor+1)">→</button></div><p class="trace-description" role="status">{{ cursor === 0 ? events.length ? '回放起点 · 尚未出现证据节点' : '完成一次审计后，这里显示真实执行记录。' : events[cursor-1]?.description }}</p><p class="trace-disclaimer">完成后的执行记录 · 展示间隔不代表模型响应耗时</p></section>
</template>
