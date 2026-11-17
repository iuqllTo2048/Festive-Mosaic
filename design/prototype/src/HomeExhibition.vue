<script setup lang="ts">
import { themes, questions } from './content.mjs'

type Dimension = 'memory' | 'practice' | 'time'
const emit = defineEmits<{
  explore: [dimension: Dimension]
  theme: [id: string]
  compare: []
  source: []
  about: []
  guide: []
}>()
const imageRoot = `${import.meta.env.BASE_URL}images/`
const previewRoot = `${import.meta.env.BASE_URL}previews/`
// Each editorial entry can receive its own illustration without changing the layout.
const entries = [
  { id: 'suzhou', title: '竞渡之间，生活之中。', text: '从龙舟竞渡与伍子胥的地方纪念，读到香包、艾草与日常生活里的端午。', tags: '龙舟竞渡 / 地方纪念 / 生活习俗', image: null as string | null },
  { id: 'miluo', title: '沿着江水，走近纪念。', text: '赛龙舟、祭龙与祭祀屈原相伴展开。地方资料里的节期，从五月初一延续到十五。', tags: '赛龙舟 / 祭祀屈原 / 节期', image: null as string | null },
  { id: 'xisai', title: '一艘神舟，一场祈愿。', text: '从扎制、巡游到送神舟下水，阅读西塞神舟会的仪程，以及其中的祈愿与纪念。', tags: '制作神舟 / 巡游送舟 / 禳灾祈福', image: null as string | null },
].map(entry => ({ ...entry, theme: themes.find(theme => theme.id === entry.id)! }))

function exploreQuestion(id: string) {
  if (id === 'memory' || id === 'practice' || id === 'time') emit('explore', id)
}
</script>

<template>
  <div class="exhibition-home">
    <section class="print-hero" aria-labelledby="exhibition-title">
      <div class="print-hero-art">
        <img :src="imageRoot + 'art/duanwu_dragon_boat.webp'"
          alt="版画风格的龙舟竞渡，朱红船身穿行于深青水纹之间，龙首向前昂起。"
          fetchpriority="high" decoding="async">
      </div>
      <div class="print-hero-copy">
        <p class="exhibition-kicker"><span></span> 端午 · 地方文化特展</p>
        <h1 id="exhibition-title">同一个端午，<br>不同的<span>地方记忆。</span></h1>
        <p class="exhibition-intro">在苏州、汨罗和黄石西塞，端午形成了不同的地方文化实践。沿着仪式与纪念传统，走近各地的端午，也读一读它们留下的资料。</p>
        <div class="exhibition-actions">
          <button class="exhibition-primary" @click="emit('guide')">AI 文化导览 <span aria-hidden="true">↗</span></button>
          <button class="exhibition-secondary" @click="emit('compare')">对照地方习俗 <span aria-hidden="true">→</span></button>
        </div>
      </div>
      <a class="exhibition-scroll" href="#local-traditions" @click.prevent="($event.currentTarget as HTMLAnchorElement).ownerDocument.getElementById('local-traditions')?.scrollIntoView()"><span>走近三种地方端午</span><span aria-hidden="true">↓</span></a>
    </section>

    <section id="local-traditions" class="local-traditions" aria-labelledby="traditions-title">
      <header class="exhibition-section-heading">
        <div><p class="exhibition-kicker">壹 / 地方风物</p><h2 id="traditions-title">同在端午，<br>各有来处。</h2></div>
        <p>竞渡、纪念、祈愿与日常生活。<br>把三份地方记录放在一起，<br>看见相连的元素，也读懂各自的不同。</p>
      </header>
      <div class="traditions-layout">
        <figure class="collage-panel">
          <div class="collage-window"><img :src="imageRoot + 'art/duanwu_collage.webp'" width="1672" height="941" alt="以舟、织物、水纹和香包构成的文化纸艺拼贴。" loading="lazy" decoding="async"></div>
          <figcaption><span>节俗里的器物与记忆</span><span>端午专题图版</span></figcaption>
        </figure>
        <div class="tradition-entries">
          <article v-for="(entry, index) in entries" :key="entry.id" class="tradition-entry" :class="'tradition-' + entry.id">
            <div class="tradition-index"><span>0{{ index + 1 }}</span><span>{{ entry.theme.source }}</span></div>
            <img v-if="entry.image" class="future-place-art" :src="entry.image" :alt="entry.theme.full" loading="lazy">
            <div class="tradition-text"><button @click="emit('theme', entry.id)"><h3>{{ entry.theme.full }}</h3><span aria-hidden="true">↗</span></button><p class="tradition-lead">{{ entry.title }}</p><p class="tradition-description">{{ entry.text }}</p><p class="tradition-tags">{{ entry.tags }}</p></div>
          </article>
        </div>
      </div>
    </section>

    <section class="exhibition-interactions" aria-labelledby="interactions-title">
      <header class="exhibition-section-heading"><div><p class="exhibition-kicker">贰 / 交互阅读</p><h2 id="interactions-title">看见习俗，<span>也看见依据。</span></h2></div><p>从一项实践读到它的地方解释，<br>再回到具体的资料。<br>让每一次发现，都有继续追问的方向。</p></header>
      <div class="interaction-preview-grid">
        <article class="interaction-preview strata-preview">
          <div class="preview-title"><span>01</span><div><h3>文化层理探索</h3><p>沿着实践、解释与资料，展开一条文化关系。</p></div></div>
          <button class="interface-window" @click="emit('explore', 'memory')" aria-label="打开文化层理探索"><img :src="previewRoot + 'cultural-strata.jpg'" width="1425" height="891" alt="已有文化层理工作台的界面预览。" loading="lazy"><span>进入层理空间 ↗</span></button>
        </article>
        <article class="interaction-preview comparison-preview">
          <div class="preview-title"><span>02</span><div><h3>异俗对照镜</h3><p>并读两个地方，保留共同点与不同的解释。</p></div></div>
          <button class="interface-window" @click="emit('compare')" aria-label="打开异俗对照镜"><img :src="previewRoot + 'comparison-lens.jpg'" width="1425" height="891" alt="已有苏州与汨罗双主题对照界面的预览。" loading="lazy"><span>选择两个地方 ↗</span></button>
        </article>
        <article class="source-preview">
          <div class="preview-title"><span>03</span><div><h3>文化资料溯源</h3><p>打开一项说法，查看定位摘录与官方原文。</p></div></div>
          <blockquote>“纪念伍子胥”<cite>苏州端午习俗 · S01</cite></blockquote>
          <button @click="emit('source')">读一条真实资料 <span aria-hidden="true">↗</span></button>
        </article>
      </div>
      <div class="exhibition-questions"><h3>也可以，带着问题出发。</h3><div><button v-for="question in questions" :key="question.id" @click="exploreQuestion(question.id)">{{ question.title }} <span aria-hidden="true">↗</span></button></div></div>
    </section>
    <div class="exhibition-colophon"><span>同节异俗 · 端午地方文化特展</span><button @click="emit('about')">资料目录与阅读说明 ↗</button><span>交互演示版</span></div>
  </div>
</template>
