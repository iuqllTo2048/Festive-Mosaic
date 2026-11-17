<script setup lang="ts">
import { ref } from 'vue'
import { festivals, statusLabels, type Festival } from './festivals.ts'
const emit = defineEmits<{festival:[id:string]; explore:[]; guide:[]; compare:[]; source:[]}>()
const pending = ref<Festival | null>(null)
const pendingDialog = ref<HTMLDialogElement | null>(null)
const artRoot = `${import.meta.env.BASE_URL}images/art/`
function choose(festival: Festival) {
  if (festival.status === 'published') emit('festival', festival.festival_id)
  else { pending.value = festival; pendingDialog.value?.showModal() }
}
</script>

<template>
  <div class="platform-portal">
    <section class="portal-opening" aria-labelledby="portal-title">
      <div class="portal-manifesto">
        <img class="portal-main-art" :src="artRoot+'portal_festival_hero.webp'" alt="灯笼、月色、春枝与龙舟交织的多节日版画" fetchpriority="high">
        <p class="portal-overline">中国传统节俗数字文化探索平台</p>
        <h1 id="portal-title">同一个节日，<br>走进<span>不同的</span><br><em>地方世界。</em></h1>
        <p class="portal-intro">向 AI 文化导览提出问题，在知识图谱里展开地方习俗、文化解释与资料之间的联系。</p>
        <div class="portal-main-actions"><button class="button primary" @click="emit('guide')">AI 文化导览 ↗</button><button class="button" @click="emit('explore')">探索文化知识图谱 ↗</button></div>
        <p class="portal-demo-note">当前导览为演示模式 · 端午资料可阅读、可对照、可追溯</p>
        <div class="portal-edition"><b>首期展厅 · 端午</b><span>苏州 / 汨罗江畔 / 西塞</span><button @click="emit('festival','duanwu')">进入端午专题 ↗</button></div>
      </div>
      <div id="festival-index" class="festival-index" aria-label="传统节日专题目录">
        <header><span>节日目录</span><span>壹篇已开放 · 其余待续</span></header>
        <button v-for="(festival,index) in festivals" :key="festival.festival_id" class="festival-leaf"
          :class="{'is-published':festival.status==='published'}" :style="{'--festival-accent':festival.accent}"
          :aria-label="`${festival.name}专题 · ${statusLabels[festival.status]}${festival.status==='published'?'，进入专题':'，查看筹备说明'}`"
          @click="choose(festival)">
          <span class="leaf-number">{{String(index+1).padStart(2,'0')}}</span>
          <span class="leaf-name">{{festival.name}}<small>{{festival.index_note}}</small></span>
          <span class="leaf-description">{{festival.subtitle}}<small v-if="festival.status==='published'">三地习俗 · 文化关系 · 资料依据</small></span>
          <span class="leaf-state">{{statusLabels[festival.status]}}<b aria-hidden="true">{{festival.status==='published'?'↗':'＋'}}</b></span>
        </button>
        <p class="index-colophon">这是一份持续策展的目录。当前仅端午篇可进入探索。</p>
      </div>
    </section>

    <section class="portal-method" aria-labelledby="method-title">
      <header class="method-heading"><p class="portal-overline">以问题为线索，以资料为依据</p><h2 id="method-title">一段探索，<span>从好奇走向理解。</span></h2><p>提问 → 本地资料筛选 → 知识关系 → 来源阅读<br>先在端午篇，体验一条完整的探索路径。</p></header>
      <div class="portal-feature-stories">
        <article class="feature-guide"><img :src="artRoot+'feature_ai_guide.webp'" alt="人物与文化图卷构成的导览插画" loading="lazy"><div><span>01 / 带着问题出发</span><h3>AI 文化导览</h3><p>“苏州和汨罗的端午习俗有什么不同？”<br>输入问题，查看任务记录、摘编回答和图谱引用。</p><button @click="emit('guide')">打开文化导览 <b>↗</b></button><small>演示模式 · 未连接模型或在线RAG</small></div></article>
        <article><img :src="artRoot+'feature_comparison.webp'" alt="不同节俗意象并置的对照版画" loading="lazy"><div><span>02 / 在相似处看见差异</span><h3>异俗对照镜</h3><p>把两地实践并读，分清共同元素与各自的文化解释。</p><button @click="emit('compare')">进入地方对照 <b>↗</b></button></div></article>
        <article><img :src="artRoot+'feature_source_trace.webp'" alt="书页与档案材料构成的资料溯源插画" loading="lazy"><div><span>03 / 让说法回到出处</span><h3>文化资料溯源</h3><p>从图谱或回答进入资料剖面，阅读摘录与官方原文。</p><button @click="emit('source')">读一份文化资料 <b>↗</b></button></div></article>
      </div>
      <div class="portal-closing"><span>读到的联系，留下的疑问，都可以存入个人观察档案。</span><button @click="emit('festival','duanwu')">从第一座展厅开始 <b>端午篇 ↗</b></button></div>
    </section>
    <dialog ref="pendingDialog" class="festival-pending" aria-labelledby="pending-title">
      <template v-if="pending"><div class="pending-top"><span>{{statusLabels[pending.status]}}</span><button aria-label="关闭专题筹备说明" @click="pendingDialog?.close()">×</button></div><p class="portal-overline">节日目录 / {{pending.index_note}}</p><h2 id="pending-title">{{pending.name}}篇，<br>留待下一次相见。</h2><p>{{pending.description}}</p><p class="pending-detail">尚未开放专题页面、文化探索或资料检索。</p><button class="button primary" @click="pendingDialog?.close()">继续翻阅目录</button></template>
    </dialog>
  </div>
</template>
