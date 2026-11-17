<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { scenes, p01Asset, type SceneKey } from './p01-scenes.ts'
const emit=defineEmits<{festival:[key:SceneKey]; home:[]; archive:[]; about:[]}>()
const open=ref(false)
const root=ref<HTMLElement|null>(null)
function leave(event:FocusEvent) { if(!root.value?.contains(event.relatedTarget as Node)) open.value=false }
function close() { open.value=false; nextTick(()=>root.value?.querySelector<HTMLButtonElement>('.p01-catalog')?.focus()) }
function select(key:SceneKey) { open.value=false; emit('festival',key) }
function hoverOpen(event:PointerEvent) { if(event.pointerType==='mouse')open.value=true }
function openKeyboard() { open.value=true; nextTick(()=>root.value?.querySelector<HTMLButtonElement>('.p01-menu-item')?.focus()) }
function move(event:KeyboardEvent) {
  const buttons=[...(root.value?.querySelectorAll<HTMLButtonElement>('.p01-menu-item')||[])]
  const index=buttons.indexOf(event.target as HTMLButtonElement)
  if(event.key==='ArrowDown'||event.key==='ArrowUp') {event.preventDefault();buttons[(index+(event.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus()}
  else if(event.key==='Home') {event.preventDefault();buttons[0]?.focus()}
  else if(event.key==='End') {event.preventDefault();buttons.at(-1)?.focus()}
}
</script>
<template>
  <header ref="root" class="p01-navigation" @focusout="leave" @keydown.esc.stop="close">
    <img class="p01-nav-art" :src="p01Asset('ui_assets/08_navigation_bar.png')" alt="" width="1589" height="162" fetchpriority="high">
    <svg class="p01-mobile-brand-art" viewBox="100 20 450 110" aria-hidden="true"><image :href="p01Asset('ui_assets/08_navigation_bar.png')" width="1589" height="162"/></svg>
    <svg class="p01-mobile-nav-art" viewBox="770 38 755 80" aria-hidden="true"><image :href="p01Asset('ui_assets/08_navigation_bar.png')" width="1589" height="162"/></svg>
    <button class="p01-nav-hit p01-brand" aria-label="同节异俗 · 平台首页" @click="emit('home')"></button>
    <div class="p01-catalog-zone" @pointerenter="hoverOpen" @pointerleave="open=false">
      <button class="p01-nav-hit p01-catalog" aria-label="节日目录" :aria-expanded="open" aria-controls="p01-festival-menu" aria-haspopup="menu" @click="open=true" @keydown.down.prevent="openKeyboard"></button>
      <nav v-show="open" id="p01-festival-menu" class="p01-festival-menu" aria-label="节日目录" role="menu" @keydown="move">
        <img :src="p01Asset('ui_assets/09_festival_dropdown.png')" alt="" width="385" height="504">
        <button v-for="(scene,index) in scenes" :key="scene.key" class="p01-menu-item" :style="{top:(10+index*17.15)+'%'}" :aria-label="scene.name+'专题'+(scene.key==='duanwu'?'':'（尚未开放）')" role="menuitem" @click="select(scene.key)"></button>
      </nav>
    </div>
    <button class="p01-nav-hit p01-archive" aria-label="观察档案" @click="emit('archive')"></button>
    <button class="p01-nav-hit p01-about" aria-label="关于文化馆" @click="emit('about')"></button>
  </header>
</template>
