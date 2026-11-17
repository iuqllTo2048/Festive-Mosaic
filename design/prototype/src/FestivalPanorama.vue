<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount, useId } from 'vue'
import { scenes, sceneByKey, p01Asset, type SceneKey } from './p01-scenes.ts'
import { PanoramaAnimation, unfoldContour, EXPANSION_MS, type Point, type PanoramaState } from './p01-animation.ts'
// Explicit override is used only by the separate development QA entry. Product uses system.
const props=withDefaults(defineProps<{motionPreference?:'system'|'full'|'reduced'}>(),{motionPreference:'system'})
const emit=defineEmits<{festival:[key:SceneKey]; transition:[state:PanoramaState & {at:number}]}>()
const svg=ref<SVGSVGElement|null>(null)
const animation=new PanoramaAnimation()
const state=ref({...animation.state})
const seeds=new Map<SceneKey,Point[]>()
const ready=ref(new Set<SceneKey>())
const failed=ref(new Set<SceneKey>())
const centerHint=ref(false)
const loading=ref<SceneKey|null>(null)
const hovered=ref<SceneKey|null>(null)
const coarse=ref(false)
const reduced=ref(false)
const fit=ref('xMidYMin slice')
const clipId='p01-reveal-'+useId().replace(/[^a-z0-9]/gi,'')
let frame=0,disposed=false,media:MediaQueryList,hoverMedia:MediaQueryList
const images:HTMLImageElement[]=[]
const activeScene=computed(()=>state.value.active?sceneByKey(state.value.active):null)
const maskPath=computed(()=>activeScene.value?unfoldContour(seeds.get(activeScene.value.key)||[],activeScene.value.origin,state.value.progress):'')
const boundaryOpacity=computed(()=>Math.min(1,(1-state.value.progress)*10)*Math.min(1,state.value.progress*15))
const artOpacity=computed(()=>Math.min(1,state.value.progress/.12))
function publish() {const previous=state.value;state.value={...animation.state};if(previous.phase!==state.value.phase||previous.active!==state.value.active)emit('transition',{...state.value,at:performance.now()})}
function tick(now:number) {frame=0;animation.advance(now);publish();if(animation.running) frame=requestAnimationFrame(tick)}
function schedule() {if(!frame&&animation.running&&!disposed)frame=requestAnimationFrame(tick)}
function request(key:SceneKey|null) {
  hovered.value=key
  if(key&&!ready.value.has(key)) { loading.value=key;animation.request(null,performance.now());publish();schedule();return }
  loading.value=null;animation.request(key,performance.now());publish();schedule()
}
function pointer(key:SceneKey) {if(!coarse.value) {centerHint.value=false;request(key)}}
function leave() {centerHint.value=false;request(null)}
function focus(key:SceneKey) {centerHint.value=false;request(key)}
function blur(event:FocusEvent) {if(!(event.relatedTarget instanceof Element)||!event.relatedTarget.closest('.p01-hit-areas'))leave()}
function motionChange() {reduced.value=props.motionPreference==='system'?media.matches:props.motionPreference==='reduced';animation.setReduced(reduced.value);publish();schedule()}
function hoverChange() {coarse.value=hoverMedia.matches;if(coarse.value)leave()}
function visible() {if(document.hidden)leave()}
function resize() {const box=svg.value?.getBoundingClientRect();if(box)fit.value=box.width/box.height<1586/907?'xMidYMin meet':'xMidYMin slice'}
onMounted(()=>{
  resize();window.addEventListener('resize',resize)
  for(const scene of scenes) {
    const path=svg.value?.querySelector<SVGPathElement>(`[data-seed="${scene.key}"]`)
    if(path) {const length=path.getTotalLength();seeds.set(scene.key,Array.from({length:112},(_,i)=>{const point=path.getPointAtLength(i*length/112);return{x:point.x,y:point.y}}))}
    const image=new Image();images.push(image)
    image.onload=async()=>{try{await image.decode()}catch{/* onload already supplies a usable image */}if(disposed)return;ready.value=new Set([...ready.value,scene.key]);if(hovered.value===scene.key)request(scene.key)}
    image.onerror=()=>{if(disposed)return;failed.value=new Set([...failed.value,scene.key]);if(loading.value===scene.key)loading.value=null}
    image.src=p01Asset('art/'+scene.file)
  }
  media=matchMedia('(prefers-reduced-motion: reduce)');hoverMedia=matchMedia('(hover: none), (pointer: coarse)')
  motionChange();hoverChange();media.addEventListener('change',motionChange);hoverMedia.addEventListener('change',hoverChange);document.addEventListener('visibilitychange',visible)
})
onBeforeUnmount(()=>{disposed=true;cancelAnimationFrame(frame);for(const image of images){image.onload=null;image.onerror=null}media?.removeEventListener('change',motionChange);hoverMedia?.removeEventListener('change',hoverChange);document.removeEventListener('visibilitychange',visible);window.removeEventListener('resize',resize)})
</script>
<template>
  <section class="p01-panorama" aria-label="五节融合交互画卷" :data-phase="state.phase" :data-active="state.active||''" :data-desired="state.desired||''" :data-progress="state.progress.toFixed(4)" :data-duration="EXPANSION_MS" :data-ready="ready.size" :data-reduced-motion="reduced" @pointerleave="leave" @keydown.esc="leave">
    <h1 class="p01-sr-only">同一个节日，走进不同的地方世界。</h1>
    <svg ref="svg" class="p01-panorama-svg" viewBox="0 85 1586 907" :preserveAspectRatio="fit" aria-label="春节、清明、端午、七夕与中秋画卷">
      <defs><path v-for="scene in scenes" :key="scene.key" :data-seed="scene.key" :d="scene.path"/><clipPath :id="clipId" clipPathUnits="userSpaceOnUse"><path :d="maskPath"/></clipPath></defs>
      <image :href="p01Asset('art/01_home_default_panorama.png')" width="1586" height="992" aria-hidden="true"/>
      <g v-if="activeScene&&state.progress>0" :clip-path="`url(#${clipId})`" :opacity="artOpacity" class="p01-expansion-layer" aria-hidden="true">
        <image :href="p01Asset('art/'+activeScene.file)" x="0" y="85" width="1586" height="907" preserveAspectRatio="xMidYMid slice"/>
      </g>
      <g v-if="activeScene&&state.progress>0&&state.progress<1" :opacity="boundaryOpacity" class="p01-moving-ribbon" aria-hidden="true">
        <path :d="maskPath" fill="none" stroke="#b38342" stroke-width="11"/><path :d="maskPath" fill="none" stroke="#f7dca2" stroke-width="5"/>
      </g>
      <g class="p01-hit-areas" @focusout="blur">
        <path v-for="scene in scenes" :key="scene.key" :d="scene.path" class="p01-festival-hit" role="link" tabindex="0" :aria-label="scene.name+'画卷，点击进入专题'" :data-festival="scene.key" @pointerenter="pointer(scene.key)" @pointerleave="request(null)" @focus="focus(scene.key)" @click="emit('festival',scene.key)" @keydown.enter.prevent="emit('festival',scene.key)" @keydown.space.prevent="emit('festival',scene.key)"><title>{{scene.name}} · 点击进入专题</title></path>
        <circle cx="793" cy="505" r="40" class="p01-center-hit" role="button" tabindex="0" aria-label="如何进入节日" :aria-expanded="centerHint" @pointerenter="leave();centerHint=true" @pointerleave="centerHint=false" @focus="leave();centerHint=true" @click="centerHint=true" @keydown.enter.prevent="centerHint=true" @keydown.space.prevent="centerHint=true"/>
      </g>
      <image v-show="centerHint" class="p01-center-hint" :href="p01Asset('ui_assets/07_center_flower_click_hint.png')" x="443" y="415" width="700" height="233.33" pointer-events="none" aria-label="点击画面进入节日"/>
    </svg>
    <p v-if="loading&&!failed.has(loading)" class="p01-art-status" role="status">正在载入{{sceneByKey(loading).name}}画卷…</p>
    <p v-if="hovered&&failed.has(hovered)" class="p01-art-status" role="status">画卷暂未载入，可点击进入专题。</p>
  </section>
</template>
