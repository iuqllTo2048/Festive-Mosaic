// Development-only Vite entry: not referenced by index.html or the production build.
import { createApp, h, ref } from 'vue'
import TopNavBar from '../src/TopNavBar.vue'
import FestivalPanorama from '../src/FestivalPanorama.vue'
import '../src/style.css'
import '../src/p01.css'
const trace=ref<unknown[]>([])
createApp({render:()=>h('div',{class:'p01-home'},[
  h(TopNavBar),h(FestivalPanorama,{motionPreference:'full',onTransition:(state:unknown)=>{trace.value=[...trace.value.slice(-39),state]}}),
  h('output',{'aria-hidden':'true',class:'p01-sr-only','data-motion-log':JSON.stringify(trace.value)}),
  h('span',{style:'position:fixed;bottom:10px;right:12px;z-index:30;background:#fff1dc;padding:4px 8px;font-size:12px;color:#663b22'},'动效验收 · 常规动画'),
])}).mount('#app')
