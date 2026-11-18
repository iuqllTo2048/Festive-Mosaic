<script setup lang="ts">
import TopNavBar from './TopNavBar.vue'
import FestivalPanorama from './FestivalPanorama.vue'
import {scenes,sceneByKey,type SceneKey} from './p01-scenes.ts'
const emit=defineEmits<{festival:[id:string]; home:[]; archive:[]; about:[]}>()
function goToFestival(key:SceneKey) {emit('festival',sceneByKey(key).festivalId)}
</script>
<template>
  <div class="p01-home">
    <TopNavBar @festival="goToFestival" @home="emit('home')" @archive="emit('archive')" @about="emit('about')"/>
    <FestivalPanorama motion-preference="full" @festival="goToFestival"/>
    <nav class="p01-mobile-festivals" aria-label="选择节日专题"><p>点击画卷或选择节日</p><button v-for="scene in scenes" :key="scene.key" @click="goToFestival(scene.key)"><span>{{scene.name}}</span><small>{{scene.key==='duanwu'?'进入专题':'尚未开放'}}</small><span aria-hidden="true">→</span></button></nav>
  </div>
</template>
