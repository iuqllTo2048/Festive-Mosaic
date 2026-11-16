<script setup>
import {onMounted,onBeforeUnmount,watch,ref} from 'vue'
import * as T from 'three'
import {OrbitControls} from '../../../frontend/node_modules/three/examples/jsm/controls/OrbitControls.js'
const props=defineProps({data:Object,selected:String,focusLayer:String,view:{type:String,default:'strata'}})
const emit=defineEmits(['select','fallback'])
const host=ref(null),hover=ref('')
let renderer,scene,camera,controls,group,observer,ray,point,hits=[],lines=[],active=true
function paint(){if(active&&renderer)renderer.render(scene,camera)}
function dispose(root){root?.traverse(o=>{o.geometry?.dispose(); const ms=Array.isArray(o.material)?o.material:[o.material];ms.filter(Boolean).forEach(m=>{m.map?.dispose();m.dispose()})})}
function label(text,color){
  const c=document.createElement('canvas'),ctx=c.getContext('2d');const value=text.length>14?text.slice(0,13)+'…':text;ctx.font='28px "Microsoft YaHei", sans-serif';c.width=Math.ceil(ctx.measureText(value).width)+20;c.height=44
  ctx.font='28px "Microsoft YaHei", sans-serif';ctx.textAlign='center';ctx.textBaseline='middle'
  ctx.fillStyle='#f5f2eb';ctx.fillRect(0,0,c.width,44);ctx.fillStyle=color;ctx.fillText(value,c.width/2,22)
  const texture=new T.CanvasTexture(c);texture.colorSpace=T.SRGBColorSpace
  const sprite=new T.Sprite(new T.SpriteMaterial({map:texture,transparent:true,depthTest:false}));sprite.userData.labelSize=[c.width/2,22];return sprite
}
function highlight(){
  if(!group)return
  const related=new Set()
  props.data.edges.filter(e=>e.claim===props.selected).forEach(e=>{related.add(e.source);related.add(e.target)})
  group.traverse(o=>{if(o.userData.node){ const n=o.userData.node;let yes=(!props.selected||related.has(n.id)||n.claim===props.selected)&&(!props.focusLayer||props.focusLayer===n.type); if(o.material)o.material.opacity=o.userData.hit?0:yes?1:.19 } if(o.userData.edge&&o.material)o.material.opacity=(!props.selected||o.userData.edge.claim===props.selected) ? .8 : .12})
  paint()
}
function draw(){
  if(!scene)return
  if(group){scene.remove(group);dispose(group)}
  group=new T.Group();hits=[];lines=[]
  for(const y of [80,-20,-150]){
    const geometry=new T.BufferGeometry().setFromPoints([new T.Vector3(-245,y,-40),new T.Vector3(245,y,-40)])
    const guide=new T.Line(geometry,new T.LineDashedMaterial({color:'#d5cfc3',dashSize:2,gapSize:5}));guide.computeLineDistances();group.add(guide)
  }
  props.data.nodes.forEach(n=>{
    const g=new T.Group();g.position.set(n.x,n.y,n.z);g.userData.node=n
    const geometry=n.type==='source'?new T.BoxGeometry(7,9,2):n.type==='interpretation'||n.type==='uncertain'?new T.OctahedronGeometry(5):new T.SphereGeometry(5,16,10)
    const material=new T.MeshBasicMaterial({color:n.color,transparent:true,wireframe:n.type==='uncertain'})
    const shape=new T.Mesh(geometry,material);shape.userData.node=n;g.add(shape)
    const hit=new T.Mesh(new T.SphereGeometry(11,10,8),new T.MeshBasicMaterial({transparent:true,opacity:0,depthWrite:false}));hit.userData={node:n,hit:true};g.add(hit);hits.push(hit)
    const text=label(n.type==='source'?n.id+' · 地方条目':n.label,n.color);text.position.y=-17;text.userData.node=n;g.add(text);group.add(g)
  })
  props.data.edges.forEach(e=>{
    const a=props.data.nodes.find(n=>n.id===e.source),b=props.data.nodes.find(n=>n.id===e.target)
    const curve=new T.QuadraticBezierCurve3(new T.Vector3(a.x,a.y,a.z),new T.Vector3((a.x+b.x)/2,(a.y+b.y)/2,65),new T.Vector3(b.x,b.y,b.z))
    const material=e.type==='interpretation'?new T.LineBasicMaterial({color:'#81958b',transparent:true,opacity:.7}):new T.LineDashedMaterial({color:e.type==='uncertain'?'#9b7d68':'#a79778',dashSize:e.type==='uncertain'?2:5,gapSize:3,transparent:true,opacity:.7})
    const line=new T.Line(new T.BufferGeometry().setFromPoints(curve.getPoints(28)),material);line.computeLineDistances();line.userData.edge=e;group.add(line);lines.push(line)
  })
  scene.add(group);reset();highlight();paint()
}
function resize(){if(!renderer||!host.value)return;const r=host.value.getBoundingClientRect();renderer.setSize(Math.max(1,r.width),Math.max(1,r.height));camera.aspect=r.width/Math.max(1,r.height);camera.updateProjectionMatrix();reset()}
function reset(){if(!camera||!host.value||!props.data.nodes.length)return;const rect=host.value.getBoundingClientRect(),tan=Math.tan(camera.fov*Math.PI/360);const xs=props.data.nodes.map(n=>n.x),ys=props.data.nodes.map(n=>n.y);const distance=Math.max(300,(Math.max(...ys)-Math.min(...ys)+100)/(2*tan),(Math.max(...xs)-Math.min(...xs)+150)/(2*tan*camera.aspect));const centerY=(Math.max(...ys)+Math.min(...ys))/2;camera.position.set(0,centerY+(props.view==='flat'?0:distance*.17),distance);controls.target.set(0,centerY,0);controls.update();const unit=2*distance*tan/Math.max(1,rect.height);group?.traverse(o=>{if(o.userData.labelSize){o.scale.set(o.userData.labelSize[0]*unit,o.userData.labelSize[1]*unit,1);o.position.y=-18*unit}});paint()}
function pick(event){const r=host.value.getBoundingClientRect();point.set((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1);ray.setFromCamera(point,camera);return ray.intersectObjects(hits,false)[0]?.object.userData.node}
function move(event){const n=pick(event);hover.value=n?`${n.type==='source'?'资料出处':n.type==='interpretation'?'文化解释':n.type==='uncertain'?'候选联系':'地方实践'} · ${n.label}`:'';host.value.style.cursor=n?'pointer':'grab'}
function click(event){const n=pick(event);if(n)emit('select',n.claim);else{ray.params.Line.threshold=3;const link=ray.intersectObjects(lines,false)[0]?.object.userData.edge;if(link)emit('select',link.claim)}}
function lost(event){event.preventDefault();emit('fallback')}
onMounted(()=>{try{
  renderer=new T.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor('#f5f2eb',0);host.value.appendChild(renderer.domElement)
  scene=new T.Scene();camera=new T.PerspectiveCamera(42,1,1,2000);ray=new T.Raycaster();point=new T.Vector2()
  controls=new OrbitControls(camera,renderer.domElement);controls.enablePan=false;controls.enableDamping=false;controls.minDistance=340;controls.maxDistance=950;controls.maxPolarAngle=Math.PI*.8;controls.addEventListener('change',paint)
  observer=new ResizeObserver(resize);observer.observe(host.value);host.value.addEventListener('pointermove',move);host.value.addEventListener('click',click);renderer.domElement.addEventListener('webglcontextlost',lost);draw();resize()
}catch{emit('fallback')}})
watch(()=>props.data,draw);watch(()=>[props.selected,props.focusLayer],highlight);watch(()=>props.view,reset)
onBeforeUnmount(()=>{active=false;observer?.disconnect();host.value?.removeEventListener('pointermove',move);host.value?.removeEventListener('click',click);controls?.dispose();dispose(group);renderer?.domElement.removeEventListener('webglcontextlost',lost);renderer?.dispose();renderer?.forceContextLoss()})
defineExpose({reset})
</script>
<template><div ref="host" class="strata-canvas" role="img" aria-label="文化层理三维关系。实践、解释、证据分层；虚线是资料出处或待核查联系。可使用下方等价列表。"></div><p class="graph-hover" aria-live="polite">{{hover || '拖动改变视角 · 点击关系查看依据 · 不表示地理位置'}}</p></template>
