<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type * as THREE from 'three'
import type { ConfigOptions, ForceGraph3DInstance, NodeObject } from '3d-force-graph'
import { evidencePath, nodeNames, edgeNames, type GraphNode, type GraphEdge, type GraphView } from '../graph-model'

type RenderNode = GraphNode & NodeObject
type RenderLink = Omit<GraphEdge, 'source' | 'target'> & { source: string | RenderNode; target: string | RenderNode }
const props = defineProps<{ data: GraphView; selectedId: string | null; theme: string; reducedMotion: boolean }>()
const emit = defineEmits<{ select: [id: string]; clear: []; unavailable: [message: string] }>()
const host = ref<HTMLDivElement | null>(null)
const busy = ref(true)
const hover = ref('')
let graph: ForceGraph3DInstance<RenderNode, RenderLink> | undefined
let modules: { three: typeof import('three'); Sprite: typeof import('three-spritetext').default } | undefined
const groups = new Map<string, { group: THREE.Group; status: GraphNode['status'] }>()
const materials = new Map<string, THREE.LineBasicMaterial>()
let observer: ResizeObserver | undefined
let active = true
let pauseTimer = 0
let firstFit = true
let fitTimer = 0
let worldPerPixel = 1

function css(name: string) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim() }
function nodeColor(node: GraphNode) {
  if (node.type === 'requirement') return css(node.status === 'supported' ? '--supported' : node.status === 'insufficient' ? '--gap' : '--muted')
  return css(node.type === 'paper' ? '--accent' : node.type === 'concept' ? '--muted' : '--graph-chunk')
}
function disposeObject(group: THREE.Object3D) {
  group.traverse((part) => {
    const mesh = part as THREE.Mesh
    if (part.type !== 'Sprite') mesh.geometry?.dispose()
    const list = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : []
    for (const material of list) { (material as THREE.SpriteMaterial).map?.dispose(); material.dispose() }
  })
}
function objectFor(node: RenderNode) {
  const { three: T, Sprite } = modules!
  let cached = groups.get(node.id)
  if (cached && cached.status !== node.status) { disposeObject(cached.group); groups.delete(node.id); cached = undefined }
  if (!cached) {
    const group = new T.Group()
    if (node.type === 'requirement') {
      const geometry = new T.EdgesGeometry(new T.OctahedronGeometry(6))
      const material = node.status === 'supported' ? new T.LineBasicMaterial({ transparent: true }) : new T.LineDashedMaterial({ dashSize: 1.2, gapSize: .8, transparent: true })
      const shape = new T.LineSegments(geometry, material)
      shape.computeLineDistances()
      const target = new T.Group()
      target.add(shape)
      const hitMaterial = new T.MeshBasicMaterial({ transparent: true, opacity: .035 })
      hitMaterial.userData.baseOpacity = .035
      target.add(new T.Mesh(new T.OctahedronGeometry(6),hitMaterial))
      group.add(target)
    } else {
      const geometry = node.type === 'chunk' ? new T.BoxGeometry(3.8, 3.8, 3.8) : new T.SphereGeometry(node.type === 'paper' ? 5.5 : 2.2, 14, 10)
      group.add(new T.Mesh(geometry, new T.MeshBasicMaterial({ transparent: true })))
    }
    const label = new Sprite('', node.type === 'requirement' ? 6.5 : 5.5, nodeColor(node))
    label.fontFace = 'Segoe UI, Microsoft YaHei, sans-serif'
    label.fontSize = 32
    label.padding = [1.5, 1]
    label.position.set(0, node.type === 'requirement' ? -13 : -11, 0)
    label.name = 'label'
    label.material.depthTest = false
    group.add(label)
    cached = { group, status: node.status }
    groups.set(node.id, cached)
  }
  const path = evidencePath(props.data, props.selectedId)
  const opacity = !path.nodes.size || path.nodes.has(node.id) ? 1 : .13
  cached.group.traverse((part) => {
    const material = (part as THREE.Mesh).material
    if (material && !Array.isArray(material)) {
      material.opacity = opacity * (typeof material.userData.baseOpacity === 'number' ? material.userData.baseOpacity : 1)
      const colored = material as THREE.MeshBasicMaterial
      colored.color?.set(part.type === 'Sprite' ? '#ffffff' : nodeColor(node))
    }
  })
  const label = cached.group.getObjectByName('label') as InstanceType<typeof import('three-spritetext').default>
  cached.group.children[0]!.scale.setScalar(worldPerPixel * (node.type === 'paper' ? 1.35 : 1.3))
  label.textHeight = worldPerPixel * 12.5
  label.position.y = -worldPerPixel * (node.type === 'requirement' ? 17 : 15)
  const status = node.type === 'requirement' ? `\n${node.status === 'supported' ? '✓ 有引用支持' : node.status === 'insufficient' ? '△ 证据不足' : '○ 待核查'}` : ''
  label.text = (node.label.length > 17 ? node.label.slice(0, 17) + '…' : node.label) + status
  label.color = nodeColor(node)
  label.backgroundColor = css('--bg')
  label.visible = node.type === 'paper' || node.type === 'requirement' || node.id === props.selectedId
  return cached.group
}
function linkMaterial(link: RenderLink) {
  const T = modules!.three
  let material = materials.get(link.id)
  if (!material) { material = new T.LineBasicMaterial({ transparent: true }); materials.set(link.id, material) }
  const path = evidencePath(props.data, props.selectedId)
  material.color.set(css(link.type === 'supports' ? '--supported' : '--graph-line'))
  material.opacity = !path.edges.size && !path.nodes.size ? (link.type === 'supports' ? .85 : .38) : path.edges.has(link.id) ? .95 : .055
  return material
}
function wake() {
  graph?.resumeAnimation()
  window.clearTimeout(pauseTimer)
  pauseTimer = window.setTimeout(() => graph?.pauseAnimation(), 650)
}
function resize() {
  if (!host.value || !graph) return
  const size = host.value.getBoundingClientRect()
  graph.width(Math.max(1, Math.floor(size.width))).height(Math.max(1, Math.floor(size.height)))
  reset()
  wake()
}
function updateData() {
  if (!graph) return
  const previous = new Map(graph.graphData().nodes.map((node) => [node.id, node]))
  const requirements = props.data.nodes.filter((node) => node.type === 'requirement')
  const papers = props.data.nodes.filter((node) => node.type === 'paper')
  const nodes: RenderNode[] = props.data.nodes.map((node, index) => {
    const old = previous.get(node.id)
    const angle = index * 2.39996
    const pinned = node.type === 'paper' ? { fx: -85, fy: (papers.indexOf(node) - (papers.length - 1) / 2) * 80, fz: 0 } : node.type === 'requirement'
      ? { fx: 125, fy: (requirements.indexOf(node) - (requirements.length - 1) / 2) * -100, fz: 0 } : {}
    return { ...node, x: old?.x ?? Math.cos(angle) * 55 - 30, y: old?.y ?? Math.sin(angle) * 55,
      z: old?.z ?? (index % 5 - 2) * 16, ...pinned }
  })
  const links: RenderLink[] = props.data.edges.map((edge) => ({ ...edge, provenance: { ...edge.provenance } }))
  graph.graphData({ nodes, links })
  graph.nodeThreeObject((node) => objectFor(node)).linkMaterial((link) => linkMaterial(link))
  graph.backgroundColor(css('--bg'))
  if (!firstFit) { window.clearTimeout(fitTimer); fitTimer = window.setTimeout(reset, 120) }
  wake()
}
function reset() {
  if (!graph || !host.value) return
  // Scene bounds include label sprites whose scale changes during fitting, and
  // matrixWorld can still reflect the previous frame. Fit stable node positions.
  const nodes = graph.graphData().nodes
  if (!nodes.length) return
  const points = nodes.map((node) => ({ x: node.fx ?? node.x ?? 0, y: node.fy ?? node.y ?? 0, z: node.fz ?? node.z ?? 0 }))
  const bounds = { x: [Math.min(...points.map(p=>p.x)), Math.max(...points.map(p=>p.x))],
    y: [Math.min(...points.map(p=>p.y)), Math.max(...points.map(p=>p.y))],
    z: [Math.min(...points.map(p=>p.z)), Math.max(...points.map(p=>p.z))] }
  const camera = graph.camera() as THREE.PerspectiveCamera
  const tangent = Math.tan(camera.fov * Math.PI / 360)
  const rect = host.value.getBoundingClientRect()
  const x = (bounds.x[0] + bounds.x[1]) / 2, y = (bounds.y[0] + bounds.y[1]) / 2, z = (bounds.z[0] + bounds.z[1]) / 2
  const height = Math.max(rect.height - 80, rect.height * .6)
  const width = Math.max(rect.width - 240, rect.width * .5)
  const distance = Math.max(80, (bounds.y[1]!-bounds.y[0]!)/(2*tangent)*rect.height/height,
    (bounds.x[1]!-bounds.x[0]!)/(2*tangent*(rect.width/rect.height))*rect.width/width) + (bounds.z[1]!-bounds.z[0]!)/2
  worldPerPixel = 2 * distance * tangent / rect.height
  graph.cameraPosition({x,y,z:z+distance},{x,y,z},props.reducedMotion?0:240)
  graph.nodeThreeObject((node)=>objectFor(node))
  wake()
}
function contextLost(event: Event) { event.preventDefault(); if (active) emit('unavailable', '3D 上下文已丢失，已切换为等价证据列表。') }

onMounted(async () => {
  try {
    const [force, three, sprite] = await Promise.all([import('3d-force-graph'), import('three'), import('three-spritetext')])
    if (!active || !host.value) return
    modules = { three, Sprite: sprite.default }
    const Constructor = force.default as unknown as { new(element: HTMLElement, options: ConfigOptions): ForceGraph3DInstance<RenderNode, RenderLink> }
    graph = new Constructor(host.value, { controlType: 'orbit', rendererConfig: { antialias: true, preserveDrawingBuffer: true, alpha: true } })
    ;(graph.d3Force('charge') as unknown as { strength: (value: number) => void }).strength(-90)
    ;(graph.d3Force('link') as unknown as { distance: (value: number) => void }).distance(45)
    graph.showNavInfo(false).enableNodeDrag(false).warmupTicks(90).cooldownTicks(props.reducedMotion ? 0 : 35)
      .nodeThreeObject(objectFor).linkMaterial(linkMaterial).linkWidth(0)
      .linkDirectionalArrowLength((link) => link.type === 'supports' ? 3 : 0)
      .linkDirectionalArrowColor(css('--supported'))
      .nodeLabel((node) => { const label = document.createElement('span'); label.textContent = `${nodeNames[node.type]} · ${node.label}`; return label })
      .linkLabel((link) => edgeNames[link.type])
      .onNodeClick((node) => emit('select', node.id)).onBackgroundClick(() => emit('clear'))
      .onNodeHover((node) => { hover.value = node ? `${nodeNames[node.type]} · ${node.label}` : '' })
      .onEngineStop(() => { if (firstFit) { firstFit = false; reset() }; wake() })
    graph.renderer().domElement.addEventListener('webglcontextlost', contextLost)
    observer = new ResizeObserver(resize)
    observer.observe(host.value)
    host.value.addEventListener('pointermove', wake)
    host.value.addEventListener('pointerdown', wake)
    host.value.addEventListener('wheel', wake, { passive: true })
    updateData()
    resize()
    await nextTick()
    fitTimer = window.setTimeout(() => { if (active) reset() }, 400)
    busy.value = false
  } catch {
    if (active) emit('unavailable', '当前浏览器无法初始化 3D，已切换为等价证据列表。')
  }
})
watch(() => props.data, updateData)
watch(() => [props.selectedId, props.theme], () => {
  graph?.nodeThreeObject((node) => objectFor(node)).linkMaterial((link) => linkMaterial(link)).backgroundColor(css('--bg')).linkDirectionalArrowColor(css('--supported'))
  wake()
})
onBeforeUnmount(() => {
  active = false
  window.clearTimeout(pauseTimer)
  window.clearTimeout(fitTimer)
  observer?.disconnect()
  host.value?.removeEventListener('pointermove', wake)
  host.value?.removeEventListener('pointerdown', wake)
  host.value?.removeEventListener('wheel', wake)
  if (graph) {
    const renderer = graph.renderer()
    renderer.domElement.removeEventListener('webglcontextlost', contextLost)
    graph._destructor()
    renderer.dispose()
    renderer.forceContextLoss()
  }
  groups.forEach(({ group }) => disposeObject(group))
  materials.forEach((material) => material.dispose())
})
defineExpose({ reset })
</script>

<template>
  <div ref="host" class="graph-canvas" role="img" aria-label="科研证据三维图谱，等价信息可通过证据列表和审计栏操作"></div>
  <p v-if="busy" class="graph-loading" role="status">正在初始化证据空间…</p>
  <p v-if="hover" class="graph-hover">{{ hover }}</p>
</template>
