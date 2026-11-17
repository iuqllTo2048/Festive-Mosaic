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
// A sampled source contour grows to an outer frame, including rounded corner overscan.
export function unfoldContour(seed: Point[], origin: [number,number], progress: number) {
  const p = Math.max(0, Math.min(1, progress))
  const eased = p*p*(3-2*p)
  const [cx,cy] = origin
  const points = seed.map((point,index) => {
    const dx=point.x-cx, dy=point.y-cy
    const tx = dx > 0 ? (1906-cx)/dx : dx < 0 ? (-320-cx)/dx : Infinity
    const ty = dy > 0 ? (1312-cy)/dy : dy < 0 ? (-235-cy)/dy : Infinity
    const distance = Math.min(tx,ty)
    const wind = Math.sin(Math.PI*p)*Math.sin(index*.26+p*4)*15
    return {x:point.x+(cx+dx*distance-point.x)*eased+wind, y:point.y+(cy+dy*distance-point.y)*eased+wind*.45}
  })
  if (!points.length) return ''
  const mid=(a:Point,b:Point)=>`${((a.x+b.x)/2).toFixed(2)} ${((a.y+b.y)/2).toFixed(2)}`
  return `M${mid(points[points.length-1]!,points[0]!)} ` + points.map((point,index)=>`Q${point.x.toFixed(2)} ${point.y.toFixed(2)} ${mid(point,points[(index+1)%points.length]!)}`).join(' ') + ' Z'
}
