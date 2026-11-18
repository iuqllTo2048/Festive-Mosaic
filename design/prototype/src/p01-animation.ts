import type { SceneKey } from './p01-scenes.ts'

export const EXPANSION_MS = 2000
export type Phase = 'idle' | 'expanding' | 'expanded' | 'collapsing'
export interface PanoramaState {
  phase: Phase
  active: SceneKey | null
  desired: SceneKey | null
  progress: number
}

// Pure clock-driven controller. No timers, DOM, images or animation framework.
export class PanoramaAnimation {
  state: PanoramaState = { phase:'idle', active:null, desired:null, progress:0 }
  private start = 0
  private from = 0
  private reduced = false

  request(key: SceneKey | null, now: number) {
    this.advance(now)
    this.state.desired = key
    if (this.reduced) { this.snap(); return }
    if (this.state.phase === 'idle' && key) this.expand(key, now)
    else if ((this.state.phase === 'expanding' || this.state.phase === 'expanded') && key !== this.state.active) {
      this.from = this.state.progress
      this.start = now
      this.state.phase = 'collapsing'
    }
  }

  advance(now: number) {
    const state = this.state
    if (state.phase === 'idle' && state.desired) { this.expand(state.desired, now); return }
    if (state.phase === 'expanding') {
      state.progress = Math.min(1, Math.max(0, (now - this.start) / EXPANSION_MS))
      if (state.progress === 1) state.phase = 'expanded'
    } else if (state.phase === 'collapsing') {
      state.progress = Math.max(0, this.from - Math.max(0, now - this.start) / EXPANSION_MS)
      // Publish a complete default frame. B may start only on the next RAF.
      if (state.progress === 0) { state.phase = 'idle'; state.active = null }
    }
  }

  setReduced(reduced: boolean) {
    this.reduced = reduced
    if (reduced) this.snap()
  }

  get running() { return this.state.phase === 'expanding' || this.state.phase === 'collapsing' || (this.state.phase === 'idle' && !!this.state.desired) }
  private expand(key: SceneKey, now: number) { this.start = now; this.state.active = key; this.state.phase = 'expanding'; this.state.progress = 0 }
  private snap() { const key=this.state.desired; this.state.active=key; this.state.phase=key?'expanded':'idle'; this.state.progress=key?1:0 }
}

export type Point = { x:number; y:number }
export type MotionPreference = 'system' | 'full' | 'reduced'
export function motionIsReduced(systemReduced: boolean, preference: MotionPreference) {
  return preference === 'system' ? systemReduced : preference === 'reduced'
}
const clamp=(value:number)=>Math.max(0,Math.min(1,value))
function smoothPath(points:Point[]) {
  if (!points.length) return ''
  const mid=(a:Point,b:Point)=>`${((a.x+b.x)/2).toFixed(2)} ${((a.y+b.y)/2).toFixed(2)}`
  return `M${mid(points[points.length-1]!,points[0]!)} ` + points.map((point,index)=>`Q${point.x.toFixed(2)} ${point.y.toFixed(2)} ${mid(point,points[(index+1)%points.length]!)}`).join(' ') + ' Z'
}
// Geometry depends on progress alone: collapse retraces the same folds, including
// a partially interrupted reveal. Time-based CSS waves would break that guarantee.
function contourPoints(seed: Point[], origin: [number,number], progress: number) {
  const p = Math.max(0, Math.min(1, progress))
  const eased = p*p
  const [cx,cy] = origin
  const reach=Math.max(...[[0,85],[1586,85],[1586,992],[0,992]].map(([x,y])=>Math.hypot(x!-cx,y!-cy)))+110
  return seed.map((point,index) => {
    const dx=point.x-cx, dy=point.y-cy
    // Expand towards an enclosing circle, rather than a rectangle: the visible
    // front stays a sweeping, rippling curve instead of becoming a picture frame.
    const t=index/seed.length, radius=Math.hypot(dx,dy)||1
    const distance=reach/radius
    const wind = Math.sin(Math.PI*p)*(Math.sin(t*Math.PI*4-p*5)*46+Math.sin(t*Math.PI*10+p*4)*18)
    return {x:point.x+(cx+dx*distance-point.x)*eased+dx/radius*wind, y:point.y+(cy+dy*distance-point.y)*eased+dy/radius*wind}
  })
}
export function unfoldContour(seed: Point[], origin: [number,number], progress: number) {
  return smoothPath(contourPoints(seed,origin,progress))
}

// A filled, variable-width silk band rides the reveal seam. The front, dark
// reverse folds and two gold hems are real surfaces, rather than a thin outline.
export function unfoldRibbon(seed:Point[], origin:[number,number], progress:number) {
  const p=clamp(progress), center=contourPoints(seed,origin,p)
  const empty={mask:'',body:'',outer:'',inner:'',crease:'',folds:[] as {path:string;opacity:number}[],opacity:0}
  if(center.length<3)return empty
  const area=center.reduce((sum,point,i)=>{const next=center[(i+1)%center.length]!;return sum+point.x*next.y-next.x*point.y},0)
  const outside:Point[]=[],inside:Point[]=[],crease:Point[]=[],folds:{path:string;opacity:number}[]=[]
  for(let i=0;i<center.length;i++) {
    const point=center[i]!,prev=center[(i+center.length-1)%center.length]!,next=center[(i+1)%center.length]!
    const tx=next.x-prev.x,ty=next.y-prev.y,length=Math.hypot(tx,ty)||1,side=area>=0?1:-1
    const nx=ty/length*side,ny=-tx/length*side,t=i/center.length
    const twist=Math.sin(t*Math.PI*6-p*Math.PI*2)
    const width=(22+44*Math.sin(Math.PI*p))*(.65+.35*Math.abs(twist))
    outside.push({x:point.x+nx*width*.58,y:point.y+ny*width*.58})
    inside.push({x:point.x-nx*width*.42,y:point.y-ny*width*.42})
    crease.push({x:point.x+nx*width*twist*.18,y:point.y+ny*width*twist*.18})
  }
  for(let i=0;i<center.length;i++) {
    const j=(i+1)%center.length,t=(i+.5)/center.length
    const shade=clamp(-Math.sin(t*Math.PI*6-p*Math.PI*2))*.62
    if(shade>.02)folds.push({path:`M${outside[i]!.x},${outside[i]!.y} L${outside[j]!.x},${outside[j]!.y} L${inside[j]!.x},${inside[j]!.y} L${inside[i]!.x},${inside[i]!.y} Z`,opacity:shade})
  }
  return {mask:smoothPath(center),body:smoothPath(outside)+' '+smoothPath(inside),outer:smoothPath(outside),inner:smoothPath(inside),crease:smoothPath(crease),folds,opacity:Math.min(1,p*14)*Math.min(1,(1-p)*12)}
}
