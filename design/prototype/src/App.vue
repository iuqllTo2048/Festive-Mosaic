<script setup>
import {ref,computed,defineAsyncComponent,onMounted,onBeforeUnmount} from 'vue'
import HeroArt from './HeroArt.vue'
import {themes,claims,sources,questions,excerpts,themeById,claimById,compare,graphFor} from './content.mjs'
const StrataScene=defineAsyncComponent(()=>import('./StrataScene.vue'))
const routes=['home','explore','compare','archive']
const page=ref(routes.includes(location.hash.slice(1))?location.hash.slice(1):'home')
const questionId=ref('memory'),dimension=ref('memory'),pairA=ref('suzhou'),pairB=ref('miluo'),themeFilter=ref('all')
const layer=ref(''),listView=ref(innerWidth<760),cameraView=ref('strata'),scene=ref(null),selected=ref(''),drawer=ref(null),about=ref(null)
const notice=ref(''),fallback=ref(false),saved=ref([]),notes=ref(''),archiveQuestion=ref(''),draftObjects=ref([]),storageAvailable=ref(true)
let noticeTimer
try{const value=JSON.parse(localStorage.getItem('festive-mosaic-demo-v1')||'{}');saved.value=(value.saved||[]).filter(id=>claims.some(c=>c.id===id));notes.value=String(value.notes||'').slice(0,500);archiveQuestion.value=value.question||'';draftObjects.value=(value.objects||[]).filter(id=>themes.some(t=>t.id===id))}catch{storageAvailable.value=false}
const activeQuestion=computed(()=>questions.find(q=>q.id===questionId.value))
const pair=computed(()=>[pairA.value,pairB.value])
const ids=computed(()=>page.value==='compare'?pair.value:themeFilter.value==='all'?themes.map(t=>t.id):[themeFilter.value])
const graph=computed(()=>graphFor(ids.value,page.value==='compare'?'compare':'strata',dimension.value))
const comparison=computed(()=>compare(pairA.value,pairB.value,dimension.value))
const current=computed(()=>claimById(selected.value)||claims[0])
const source=computed(()=>sources[current.value.source])
const comparisonPeers=computed(()=>page.value==='compare'&&comparison.value.common.includes(current.value.feature)?comparison.value.commonClaims.filter(c=>c.feature===current.value.feature):[])
const visibleClaims=computed(()=>claims.filter(c=>ids.value.includes(c.theme)&&c.dimension===dimension.value))
const savedClaims=computed(()=>saved.value.map(claimById).filter(Boolean))
const archiveObjects=computed(()=>[...new Set([...draftObjects.value,...savedClaims.value.map(c=>c.theme).filter(Boolean)])].map(themeById))
const commonSaved=computed(()=>savedClaims.value.filter(c=>c.theme&&savedClaims.value.some(other=>other.id!==c.id&&other.theme!==c.theme&&other.feature===c.feature)))
function toast(text){notice.value=text;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>notice.value='',4500)}
function persist(){try{localStorage.setItem('festive-mosaic-demo-v1',JSON.stringify({saved:saved.value,notes:notes.value,question:archiveQuestion.value,objects:draftObjects.value}));storageAvailable.value=true}catch{storageAvailable.value=false}}
function go(next){page.value=next;try{history.replaceState(null,'','#'+next)}catch{} window.scrollTo({top:0,behavior:'instant'})}
function enter(question){questionId.value=question.id;dimension.value=question.id;selected.value='';themeFilter.value='all';layer.value='';go('explore')}
function setDimension(value){dimension.value=value;selected.value='';layer.value=''}
function openClaim(id){selected.value=id;if(!drawer.value.open)drawer.value.showModal()}
function toggleSave(id){
  if(saved.value.includes(id)){saved.value=saved.value.filter(value=>value!==id);toast('已从这份草稿移出，可再次保存。')}
  else{saved.value.push(id);archiveQuestion.value=activeQuestion.value.title;draftObjects.value=[...new Set([...draftObjects.value,...(page.value==='compare'?pair.value:[claimById(id).theme].filter(Boolean))])];toast('已存入观察档案。你可以继续寻找另一份资料。')}
  persist()
}
function startCompare(){go('compare');setDimension(dimension.value)}
function unavailable(){fallback.value=true;listView.value=true;toast('三维视图暂不可用，已显示同一批文化关系列表。')}
function onResize(){if(innerWidth<760)listView.value=true}
function onEscape(event){if(event.key==='Escape'&&!document.querySelector('dialog[open]')){selected.value='';layer.value=''}}
onMounted(()=>{window.addEventListener('resize',onResize);window.addEventListener('keydown',onEscape)})
onBeforeUnmount(()=>{clearTimeout(noticeTimer);window.removeEventListener('resize',onResize);window.removeEventListener('keydown',onEscape)})
</script>

<template>
  <a class="skip-link" href="#main">跳至主要内容</a>
  <header class="masthead">
    <button class="brand" @click="go('home')" aria-label="同节异俗 首页"><span class="brand-symbol" aria-hidden="true"><i></i><i></i><i></i></span><span><b>同节异俗</b><small>FESTIVE MOSAIC</small></span></button>
    <nav aria-label="主要导航"><button :class="{active:page==='home'||page==='explore'}" @click="go(page==='home'?'home':'explore')"><span>01</span> 文化探索</button><button :class="{active:page==='compare'}" @click="startCompare"><span>02</span> 异俗对照镜</button><button :class="{active:page==='archive'}" @click="go('archive')"><span>03</span> 观察档案 <i class="saved-count">{{saved.length}}</i></button></nav>
    <button class="edition" @click="about?.showModal()">端午 · 第一期 <span>↗</span></button>
  </header>
  <main id="main">
    <template v-if="page==='home'">
      <section class="exhibition-hero">
        <div class="hero-copy"><p class="eyebrow"><span class="red-rule"></span> 地方节俗观察计划 / VOL. 01</p><h1>同一个端午，<br>不同的<span class="serif-red">来处。</span></h1><p class="hero-intro">从一艘舟、一场仪式开始，<br>走近地方文化的多种解释，再回到它的资料依据。</p><div class="hero-caption"><span>苏州</span><i></i><span>汨罗江畔</span><i></i><span>西塞</span><em>三份地方记录，一次开放的阅读。</em></div></div>
        <div class="hero-plate"><HeroArt/><div class="plate-caption"><span>图版 01 / 文化层理</span><span>原创抽象图形 · 非实物复原</span></div></div>
      </section>
      <section class="question-section" aria-labelledby="question-title"><div class="section-intro"><p class="eyebrow">A QUESTION OPENS A CULTURE</p><h2 id="question-title">从一个问题开始</h2><p>先不急着给出答案。<br>看看不同地方留下了什么记录。</p></div><div class="question-list"><button v-for="(q,index) in questions" :key="q.id" @click="enter(q)"><span class="question-number">0{{index+1}}</span><span><strong>{{q.title}}</strong><small>{{q.intro}}</small></span><em>{{q.category}}</em><span class="row-arrow" aria-hidden="true">↗</span></button></div></section>
      <div class="home-footnote"><span>内容摘编自官方文化资料 <button @click="about?.showModal()">查看资料与设计说明 ↗</button></span><span><i class="demo-dot"></i> DEMO · 静态设计原型 · 未调用 AI</span></div>
    </template>

    <template v-else-if="page==='explore'||page==='compare'">
      <div class="workspace-title"><div><p class="eyebrow"><button @click="go('home')">端午地方记录</button> / {{page==='compare'?'异俗对照镜':'文化层理探索'}}</p><h1>{{page==='compare'?'让共同点与差异，同时被看见。':activeQuestion.title}}</h1></div><button v-if="page==='explore'" class="button primary" @click="startCompare">打开异俗对照镜 <span>↗</span></button><button v-else class="button" @click="go('explore')">回到层理探索 ↗</button></div>
      <div v-if="page==='compare'" class="pair-selector"><span class="label">正在对照</span><label class="pair-choice"><small>主题 A</small><select v-model="pairA" aria-label="对照主题 A"><option v-for="t in themes" :key="t.id" :value="t.id" :disabled="t.id===pairB">{{t.full}}</option></select></label><span class="pair-divider" aria-hidden="true">⇄</span><label class="pair-choice"><small>主题 B</small><select v-model="pairB" aria-label="对照主题 B"><option v-for="t in themes" :key="t.id" :value="t.id" :disabled="t.id===pairA">{{t.full}}</option></select></label><p>共同出现，不等于全部相同。<br>未被记录，也不等于不存在。</p></div>
      <div class="workspace-grid" :class="{'is-compare':page==='compare'}">
        <aside v-if="page==='explore'" class="theme-rail"><p class="eyebrow">地方资料 / 03</p><button class="all-themes" :class="{chosen:themeFilter==='all'}" @click="themeFilter='all'">并读三地资料 <span>↗</span></button><button v-for="t in themes" :key="t.id" class="theme-entry" :class="{chosen:themeFilter===t.id}" @click="themeFilter=t.id"><small>{{t.number}} / {{t.source}}</small><h2>{{t.name}}</h2><p>{{t.subtitle}}</p><span>阅读此地 →</span></button><div class="rail-note"><span class="mini-index">编者说明</span><p>地方解释可以并存。<br>不以单一起源覆盖多样实践。</p><button @click="about?.showModal()">关于这次摘编 ↗</button></div></aside>
        <section class="reading-space" aria-label="文化关系探索">
          <div class="dimension-tabs" role="group" aria-label="文化对照维度"><button v-for="(text,key) in {memory:'纪念传统',practice:'水上与生活实践',time:'节期节奏'}" :key="key" :aria-pressed="dimension===key" @click="setDimension(key)">{{text}}</button><span class="static-mark">静态摘编 · DEMO</span></div>
          <div v-if="page==='compare'" class="common-strip"><span class="small-glyph">◇</span><div><strong>{{comparison.common.length?`现有摘编共同记录 ${comparison.common.length} 项细节`:'本次摘编未定位到相同的细项记录'}}</strong><p>{{comparison.common.length?'两份资料都记录竞渡；它们的纪念解释仍分别保留。':'保留两方各自的记录，不将资料空白推断为当地没有这一习俗。'}}</p></div><button v-if="comparison.common.length" @click="openClaim(comparison.commonClaims[0].id)">查看双方出处 ↗</button></div>
          <div class="graph-heading"><div><p class="eyebrow">{{page==='compare'?'COMPARISON LENS':'CULTURAL STRATA'}}</p><h2>{{page==='compare'?'两个地方，一组可追溯的对照':'沿着实践，读到解释与证据'}}</h2></div><div class="view-tools"><button :aria-pressed="!listView" @click="listView=false;fallback=false">三维</button><button :aria-pressed="listView" @click="listView=true">列表</button><button v-if="!listView" @click="cameraView=cameraView==='flat'?'strata':'flat'">{{cameraView==='flat'?'层理视角':'平面读图'}}</button><button @click="selected='';layer='';scene?.reset()" aria-label="重置文化图谱视角">复位 ↺</button></div></div>
          <div v-if="!listView" class="strata-legend" role="group" aria-label="聚焦文化层次"><button :class="{on:!layer}" @click="layer=''">全览</button><button v-for="(label,key) in {practice:'01 文化实践',interpretation:'02 文化解释',source:'03 资料依据'}" :key="key" :class="{on:layer===key}" @click="layer=layer===key?'':key"><i :class="key"></i>{{label}}</button><span>⋯ 候选联系 / 待核查</span></div>
          <div class="scene-stage"><template v-if="!listView&&graph.nodes.length"><StrataScene ref="scene" :data="graph" :selected="selected" :focus-layer="layer" :view="cameraView" @select="openClaim" @fallback="unavailable"/><div class="layer-axis" aria-hidden="true"><span>实践</span><span>解释</span><span>资料</span></div></template><div v-else class="relation-list"><p v-if="fallback" role="status">当前三维视图不可用，以下为同一批文化关系。</p><p class="list-description">{{visibleClaims.length}} 条摘编关系 · 与三维视图同源</p><p v-if="!visibleClaims.length" class="blank-note">本次摘编未定位此地在该维度的完整记录。<br>资料空白不等于当地不存在这一实践。</p><button v-for="c in visibleClaims" :key="c.id" @click="openClaim(c.id)"><span>{{themeById(c.theme).name}}</span><strong>{{c.practice}} <i>→</i> {{c.interpretation}}</strong><small>{{c.source}} · 来源已定位</small><b>↗</b></button><button v-if="page==='explore'&&dimension==='practice'" class="uncertain-row" @click="openClaim('question-link')"><span>候选问题</span><strong>舟的共同意象，能否说明同一传承？</strong><small>待核查</small><b>↗</b></button></div></div>
          <div class="graph-bottom"><span>{{graph.nodes.length}} 个关系节点 · {{graph.edges.length}} 条资料/解释连线</span><span>按内容关系布局 · 非地图 · 非事实认证</span></div>
          <div v-if="page==='compare'" class="comparison-columns"><article v-for="(side,index) in [comparison.left,comparison.right]" :key="index"><p class="eyebrow">{{index?'主题 B':'主题 A'}} / {{themeById(pair[index]).source}}</p><h3>{{themeById(pair[index]).name}}</h3><template v-if="side.length"><button v-for="c in side" :key="c.id" @click="openClaim(c.id)"><strong>{{c.practice}}</strong><span>{{c.interpretation}} ↗</span></button></template><p v-else class="blank-note">本次摘编未定位完整记录。<br>不据此判断当地不存在。</p></article></div>
        </section>
        <aside class="reading-note"><p class="eyebrow">READING NOTE / 观察提示</p><span class="quote-mark">“</span><h2>{{dimension==='memory'?'不同的纪念，可以在同一个节日里并存。':dimension==='practice'?'看见共同的舟，不急着说它们相同。':'一个节日，也有不同的时间刻度。'}}</h2><p>{{dimension==='memory'?'这里阅读的是地方资料中的解释，不为节日起源排出唯一答案。':dimension==='practice'?'竞渡与送神舟都与水上活动有关，但资料所述的仪式过程与地方解释需要分别阅读。':'条目中的一般节期与当年活动安排不同。本次原型不提供年度日程。'}}</p><div class="evidence-key"><h3>如何阅读关系状态</h3><span><i class="located-dot"></i>来源已定位</span><small>短引句定位到网页，关系待独立审读</small><span><i class="pending-dot"></i>候选联系 · 待核查</span><small>没有充分材料时，先保留问题</small><button @click="about?.showModal()">模型判断与人工核对如何区分？ ↗</button></div><button :disabled="!visibleClaims.length" class="prompt-observation" @click="openClaim(visibleClaims[0]?.id||'question-link')">选一条关系，查看剖面 <span>↗</span></button><p class="disclosure">本原型没有调用模型，<br>没有“人工已核对”的关系。</p></aside>
      </div>
      <div class="workspace-footer"><span>一次阅读不会消除所有空白。</span><button @click="go('archive')">整理我的观察 <span>{{saved.length}} 条已存</span> ↗</button></div>
    </template>

    <template v-else-if="page==='archive'">
      <section class="archive-header"><p class="eyebrow">PERSONAL CULTURAL FIELDNOTES / 本地草稿</p><h1>把发现留下，<br>也把问题留下。</h1><div><p>文化观察档案 <span>001 / DEMO</span></p><button class="button" @click="startCompare">返回对照，继续观察 ↗</button></div></section>
      <div class="archive-layout"><aside class="archive-meta"><span class="mini-index">这一次，我在观察</span><h2>{{archiveQuestion||'尚未保存探索主题'}}</h2><p>{{archiveObjects.length?archiveObjects.map(t=>t.name).join(' / '):'选择两个地方，保存一条你想继续理解的文化关系。'}}</p><dl><dt>资料范围</dt><dd>官方网页静态摘编</dd><dt>核验状态</dt><dd>来源可定位 / 待人工审读</dd><dt>保存位置</dt><dd>{{storageAvailable?'当前浏览器本地':'仅当前会话 · 本地存储不可用'}}</dd></dl></aside><section class="archive-main"><div class="archive-section-title"><h2>已保存的文化关系</h2><span>{{saved.length}} 条</span></div><div v-if="!saved.length" class="archive-empty"><span>＋</span><h3>从一条关系开始，形成自己的观察。</h3><p>回到探索或对照界面，查看说法剖面，再将值得保留的关系存入这里。</p><button class="button primary" @click="startCompare">去看两种地方实践 ↗</button></div><article v-for="c in savedClaims" :key="c.id" class="saved-relation"><span class="eyebrow">{{c.theme?themeById(c.theme).name:'待核查问题'}} / {{c.source||'未定位依据'}}</span><button @click="openClaim(c.id)"><h3>{{c.title}}</h3><span>↗</span></button><p>{{c.text}}</p><small>{{c.status==='uncertain'?'证据不足 · 不生成事实结论':'来源已定位 · 文化解释待独立人工审读'}}</small></article><section class="observed-summary"><h3>共同点与差异</h3><p>{{commonSaved.length?'你保存的关系中，至少两地共享同一记录元素。点击各条来源继续核对解释。':'当前保存内容尚不足以整理跨地方共同点。保留各自记录，继续寻找另一份资料。'}}</p><p>不同地方的解释并存，不自动标记为冲突。</p></section><label class="fieldnote" for="fieldnote">仍想继续核查的问题 <textarea id="fieldnote" v-model="notes" maxlength="500" rows="4" placeholder="例如：竞渡和送神舟的联系，还需要哪些地方文献？" @input="persist"></textarea><small>{{notes.length}} / 500 · 由你记录，不由模型代写</small></label><p class="archive-limit">这是一份浏览器内的设计原型草稿。尚未提供账号、云同步或正式导出。</p></section></div>
    </template>
  </main>
  <footer class="site-footer"><span>同节异俗 <i>FESTIVE MOSAIC</i></span><span>以地方实践为入口，以资料依据为归处。</span><button @click="about?.showModal()">DEMO / 内容与使用说明 ↗</button></footer>
  <div v-if="notice" class="toast" role="status">{{notice}}</div>

  <dialog ref="drawer" class="claim-drawer" aria-labelledby="claim-title"><header><div><p class="eyebrow">CULTURAL CLAIM TRACE</p><span>文化说法剖面</span></div><button class="close-button" @click="drawer.close()" aria-label="关闭说法剖面">×</button></header><div class="drawer-content"><p class="claim-context">{{current.theme?themeById(current.theme).full:'跨地方候选关系'}} <span>静态摘编 · DEMO</span></p><h2 id="claim-title">{{current.title}}</h2><div v-if="comparisonPeers.length" class="peer-sources" aria-label="共同元素的双方出处"><p>共同记录的元素，分别阅读双方资料</p><button v-for="peer in comparisonPeers" :key="peer.id" :aria-pressed="selected===peer.id" @click="selected=peer.id">{{themeById(peer.theme).name}} · {{peer.source}} ↗</button></div><p class="status-badge" :class="current.status">{{current.status==='uncertain'?'○ 证据不足 · 候选联系':'◇ 来源已定位 · 待人工审读'}}</p><div class="trace-step"><b>01</b><div><h3>看到的地方实践</h3><strong>{{current.practice}}</strong><p>{{current.text}}</p><small>以上为编辑摘编，非模型回答。</small></div></div><div class="trace-step"><b>02</b><div><h3>资料中的解释</h3><strong>{{current.interpretation}}</strong><p>地方解释可以并存。关系是否充分，需要结合全文与地方语境审读。</p></div></div><div class="trace-step"><b>03</b><div><h3>回到资料原文</h3><template v-if="source"><p class="source-catalog">{{source.id}} · {{source.category}}</p><h4>{{source.title}}</h4><blockquote v-for="(quote,index) in excerpts[current.id]||[source.quote]" :key="quote"><small>定位摘录 {{index+1}}</small>“{{quote}}”</blockquote><p class="source-location">{{source.publisher}}<br>{{source.locator}} · 网页核对 {{source.checked}}</p><a class="source-link" :href="source.url" target="_blank" rel="noopener noreferrer">打开官方原文，核对完整语境 ↗</a><p class="source-warning">短摘录分别展示，不拼成连续引文。来源已定位不等于文化关系已认证。{{source.note}}</p></template><div v-else class="unknown-source"><h4>把空白留在档案里。</h4><p>当前没有充分材料支持这一候选联系。相关条目只能提供背景，不能证明同一传承。</p><button v-for="s in Object.values(sources).slice(0,3)" :key="s.id" @click="selected=claims.find(c=>c.source===s.id).id">继续阅读 {{s.title}} ↗</button></div></div></div></div><footer><button class="button primary" @click="toggleSave(current.id)">{{saved.includes(current.id)?'已存入 · 移出此条':'＋ 存入观察档案'}}</button><button class="text-link" @click="drawer.close();go('archive')">查看档案 {{saved.length}} ↗</button></footer></dialog>
  <dialog ref="about" class="about-dialog" aria-labelledby="about-title"><div class="about-heading"><p class="eyebrow">ABOUT THIS EDITION</p><button class="close-button" @click="about.close()" aria-label="关闭说明">×</button></div><h2 id="about-title">一份开放的地方节俗阅读。</h2><p>《同节异俗》是独立高保真设计原型。内容来自官方网页摘编，三维位置按实践、解释与资料关系组织，不使用地图。没有连接检索、模型或事实认证服务。</p><div class="status-explanation"><p><b>◇ 来源已定位</b><span>本原型已核对网页文字的位置。</span></p><p><b>△ 模型认为支持</b><span>未来状态；本原型未执行模型判断。</span></p><p><b>□ 人工已核对</b><span>未来状态；当前独立人工核验为0。</span></p><p><b>○ 证据不足</b><span>候选联系不进入已记录关系。</span></p><p><b>≠ 解释差异</b><span>地方传统不同，不自动判断互相矛盾。</span></p></div><div class="about-sources"><a v-for="s in Object.values(sources)" :key="s.id" :href="s.url" target="_blank" rel="noopener noreferrer">{{s.id}} · {{s.title}} ↗</a></div><p class="muted">视觉图形为本原型原创示意，不复原具体文物或仪式实物。未使用网页摄影图片。正式参赛前仍需地方文化专家审读、素材权属与竞赛要求核查。</p></dialog>
</template>
