import test from 'node:test'
import assert from 'node:assert/strict'
import { PanoramaAnimation, EXPANSION_MS, unfoldContour, unfoldRibbon, motionIsReduced } from './p01-animation.ts'
import { scenes } from './p01-scenes.ts'
import { parseRoute, routeHash } from './navigation.ts'

test('expansion uses a complete 2000 ms clock interval',()=>{
  const animation=new PanoramaAnimation()
  animation.request('spring',100)
  for(const [now,p] of [[600,.25],[1100,.5],[2099,.9995]]){
    animation.advance(now);assert.equal(animation.state.phase,'expanding');assert.equal(animation.state.progress,p)
  }
  animation.advance(2100)
  assert.equal(EXPANSION_MS,2000)
  assert.deepEqual(animation.state,{phase:'expanded',active:'spring',desired:'spring',progress:1})
})
test('switch publishes the default state before the next festival can expand',()=>{
  const animation=new PanoramaAnimation()
  animation.request('spring',0);animation.advance(2000);animation.request('mid-autumn',2500)
  animation.advance(3500);assert.equal(animation.state.active,'spring');assert.equal(animation.state.progress,.5)
  animation.advance(4500);assert.equal(animation.state.phase,'idle');assert.equal(animation.state.active,null);assert.equal(animation.state.progress,0)
  animation.advance(4516);assert.equal(animation.state.active,'mid-autumn');assert.equal(animation.state.progress,0)
  animation.advance(6516);assert.equal(animation.state.phase,'expanded')
})
test('interruption retraces partial progress and keeps only the latest requested festival',()=>{
  const animation=new PanoramaAnimation()
  animation.request('spring',0);animation.request('qingming',500)
  assert.equal(animation.state.progress,.25)
  animation.request('qixi',700);assert.equal(animation.state.active,'spring');assert.ok(Math.abs(animation.state.progress-.15)<1e-9)
  animation.advance(1000);assert.equal(animation.state.phase,'idle')
  animation.advance(1016);assert.equal(animation.state.active,'qixi')
  animation.request(null,1216);animation.advance(1416)
  assert.equal(animation.state.phase,'idle');assert.equal(animation.running,false)
})
test('reduced motion snaps without scheduling a moving reveal',()=>{
  const animation=new PanoramaAnimation();animation.setReduced(true);animation.request('duanwu',10)
  assert.equal(animation.state.phase,'expanded');assert.equal(animation.running,false)
  animation.request(null,20);assert.equal(animation.state.phase,'idle')
  animation.setReduced(false);animation.request('qixi',30);assert.equal(animation.state.progress,0)
})
test('frame drops do not change the configured expansion duration or skip the default switch frame',()=>{
  const animation=new PanoramaAnimation();animation.request('duanwu',0);animation.advance(2800)
  assert.equal(animation.state.progress,1)
  animation.request('qingming',3000);animation.advance(8500)
  assert.equal(animation.state.phase,'idle');assert.equal(animation.state.active,null)
  animation.advance(8516);assert.equal(animation.state.active,'qingming');assert.equal(animation.state.progress,0)
})
test('art and menu keys share existing routes and never publish unfinished subjects',()=>{
  assert.equal(scenes.length,5)
  for(const scene of scenes){
    assert.match(scene.file,/fullscreen\.png$/)
    const route=parseRoute(routeHash('festival',scene.festivalId))
    assert.equal(route.page,scene.key==='duanwu'?'festival':'unavailable')
    assert.equal(route.festival_id,scene.festivalId)
  }
})
test('contour coordinates remain finite and reverse along the same geometric path',()=>{
  const seed=[{x:0,y:100},{x:500,y:200},{x:700,y:500},{x:0,y:500}]
  const paths=[0,.25,.5,.75,1].map(p=>unfoldContour(seed,[300,350],p))
  assert.equal(new Set(paths).size,5)
  assert.ok(paths.every(path=>!/(NaN|Infinity)/.test(path)))
  assert.equal(unfoldContour(seed,[300,350],.25),paths[1])
})

test('configured component motion mode resolves independently from the system preference',()=>{
  assert.equal(motionIsReduced(true,'system'),true)
  assert.equal(motionIsReduced(false,'system'),false)
  assert.equal(motionIsReduced(true,'full'),false)
  assert.equal(motionIsReduced(false,'reduced'),true)
})

test('filled ribbon follows the reveal seam and reverses all its folds deterministically',()=>{
  const seed=[{x:0,y:100},{x:500,y:200},{x:700,y:500},{x:0,y:500}]
  const ribbon=unfoldRibbon(seed,[300,350],.4)
  assert.equal(ribbon.mask,unfoldContour(seed,[300,350],.4))
  assert.notEqual(ribbon.outer,ribbon.inner)
  assert.equal(ribbon.opacity,1)
  assert.ok(ribbon.folds.length>0)
  assert.ok(!/(NaN|Infinity)/.test(JSON.stringify(ribbon)))
  unfoldRibbon(seed,[300,350],.8)
  assert.deepEqual(unfoldRibbon(seed,[300,350],.4),ribbon)
  assert.equal(unfoldRibbon(seed,[300,350],0).opacity,0)
  assert.equal(unfoldRibbon(seed,[300,350],1).opacity,0)
  assert.equal(unfoldRibbon([],[300,350],.5).body,'')
})
