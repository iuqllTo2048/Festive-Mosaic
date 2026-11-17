<script setup lang="ts">
import { ref } from 'vue'
import { festivals, statusLabels, type Festival } from './festivals.ts'
const emit = defineEmits<{festival:[id:string]; explore:[]; compare:[]; source:[]}>()
const pending = ref<Festival | null>(null)
const pendingDialog = ref<HTMLDialogElement | null>(null)
const previewRoot = `${import.meta.env.BASE_URL}previews/`
function choose(festival: Festival) {
  if (festival.status === 'published') emit('festival', festival.festival_id)
  else { pending.value = festival; pendingDialog.value?.showModal() }
}
</script>

<template>
  <div class="platform-portal">
    <section class="portal-opening" aria-labelledby="portal-title">
      <div class="portal-manifesto">
        <p class="portal-overline">中国传统节俗数字文化探索平台</p>
        <h1 id="portal-title">同一个节日，<br>走进<span>不同的</span><br><em>地方世界。</em></h1>
        <p class="portal-intro">同样的节日，在不同地方拥有不同的文化实践与地方记忆。从一个节日出发，读习俗、看联系，再回到资料。</p>
        <a href="#festival-index" class="portal-index-link" @click.prevent="($event.currentTarget as HTMLAnchorElement).ownerDocument.getElementById('festival-index')?.scrollIntoView()">翻阅节日目录 <span>↓</span></a>
        <div class="portal-edition"><b>首期展厅 · 端午</b><span>苏州 / 汨罗江畔 / 西塞</span><button @click="emit('festival','duanwu')">进入已开放专题 ↗</button></div>
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
      <header class="method-heading"><p class="portal-overline">从端午篇，认识一种阅读方法</p><h2 id="method-title">不止认识节日。<br><span>也理解地方之间的联系。</span></h2><p>先读苏州与汨罗共同记录的竞渡，<br>再追问：相似的实践，是否拥有相同的解释？</p></header>
      <div class="method-body">
        <button class="portal-real-preview" @click="emit('explore')" aria-label="进入端午文化层理探索"><img :src="previewRoot+'cultural-strata.jpg'" width="1425" height="891" alt="现有文化层理工作台，按实践、解释、资料组织文化关系" loading="lazy"><span>端午篇 / 文化知识网络 <b>进入层理探索 ↗</b></span></button>
        <div class="method-reading">
          <div class="method-line"><span>01</span><div><h3>从地方差异进入</h3><p>苏州资料记载纪念伍子胥，汨罗条目记载祭祀屈原。让不同的地方解释并读。</p></div></div>
          <div class="method-line"><span>02</span><div><h3>把关系展开，再对照</h3><p>在实践、解释与依据之间移动，比较竞渡与送神舟的记录。</p><button @click="emit('compare')">打开端午异俗对照镜 ↗</button></div></div>
          <div class="method-line"><span>03</span><div><h3>让每条说法回到出处</h3><blockquote>“以龙舟竞渡等活动纪念伍子胥”</blockquote><p>S01 · 苏州市非物质文化遗产保护管理办公室</p><button @click="emit('source')">阅读摘录与原始资料 ↗</button></div></div>
        </div>
      </div>
      <div class="portal-closing"><span>读到的联系，留下的疑问，都可以存入个人观察档案。</span><button @click="emit('festival','duanwu')">从第一座展厅开始 <b>端午篇 ↗</b></button></div>
    </section>
    <dialog ref="pendingDialog" class="festival-pending" aria-labelledby="pending-title">
      <template v-if="pending"><div class="pending-top"><span>{{statusLabels[pending.status]}}</span><button aria-label="关闭专题筹备说明" @click="pendingDialog?.close()">×</button></div><p class="portal-overline">节日目录 / {{pending.index_note}}</p><h2 id="pending-title">{{pending.name}}篇，<br>留待下一次相见。</h2><p>{{pending.description}}</p><p class="pending-detail">尚未开放专题页面、文化探索或资料检索。</p><button class="button primary" @click="pendingDialog?.close()">继续翻阅目录</button></template>
    </dialog>
  </div>
</template>
