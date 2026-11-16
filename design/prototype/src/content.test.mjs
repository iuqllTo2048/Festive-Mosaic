import test from 'node:test'
import assert from 'node:assert/strict'
import {claims,sources,compare,graphFor} from './content.mjs'
test('shared practice is derived from recorded features, not place proximity',()=>{
  assert.deepEqual(compare('suzhou','miluo').common,['race'])
  assert.deepEqual(compare('suzhou','xisai').common,[])
})
test('missing recorded feature is never labelled absent in the other place',()=>{
  const result=compare('suzhou','xisai')
  assert.ok(result.left.length&&result.right.length)
  assert.equal(result.common.length,0)
  assert.ok(!JSON.stringify(result).includes('不存在'))
})
test('located claims resolve to declared HTTPS sources; uncertain links do not fabricate a source',()=>{
  for(const c of claims)assert.ok(c.status==='uncertain'?c.source===null:sources[c.source]?.url.startsWith('https://'))
  assert.ok(!claims.some(c=>c.status==='human_verified'||c.status==='model_supported'))
})
test('strata and comparison have no dangling relations or random coordinates',()=>{
  assert.deepEqual(graphFor(['suzhou'],'strata','time'),{nodes:[],edges:[]})
  for(const mode of ['strata','compare']){
    const graph=graphFor(['suzhou','miluo'],mode)
    const ids=new Set(graph.nodes.map(n=>n.id))
    assert.equal(ids.size,graph.nodes.length)
    assert.ok(graph.edges.every(e=>ids.has(e.source)&&ids.has(e.target)))
    assert.deepEqual(graph,graphFor(['suzhou','miluo'],mode))
  }
})
