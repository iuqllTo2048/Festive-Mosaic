import test from 'node:test'
import assert from 'node:assert/strict'
import { runCulturalGuide } from './cultural-guide.ts'
import { claims,sources,excerpts } from './content.mjs'
import { festivalGraph } from './festival-content.ts'

test('comparison question shares source IDs and graph identities without model calls',()=>{
  const task=runCulturalGuide('苏州和汨罗的端午习俗有什么不同？')
  assert.equal(task.status,'ready')
  assert.deepEqual(task.topic_ids,['suzhou','miluo'])
  assert.equal(task.model_calls,0)
  assert.equal(task.semantic_review,'not_run')
  assert.ok(task.evidence.some(e=>e.source_id==='S01')&&task.evidence.some(e=>e.source_id==='S02'))
  for(const evidence of task.evidence){
    const graph=festivalGraph('duanwu',task.topic_ids,'strata',evidence.dimension)
    assert.ok(graph.nodes.some(n=>n.id===evidence.claim_id))
    assert.ok(task.answer.some(a=>a.claim_ids.includes(evidence.claim_id)))
  }
})
test('unopened festivals, unanswerable claims and missing coverage preserve gaps',()=>{
  for(const question of ['中秋节如何祭月？','苏州和汨罗是不是同一传承？','苏州端午的节期有几天？','今年端午活动票价是多少？','西塞神舟会始于哪个朝代？','量子计算是什么？']){
    const task=runCulturalGuide(question)
    assert.equal(task.status,'insufficient',question)
    assert.equal(task.answer.length,0)
    assert.ok(task.gaps.length)
  }
  assert.deepEqual(runCulturalGuide('中秋节如何祭月？').evidence,[])
})
test('broken source linkage is rejected before any answer is assembled',()=>{
  const task=runCulturalGuide('苏州端午习俗',{claims,sources:{},excerpts})
  assert.equal(task.status,'validation_failed')
  assert.equal(task.evidence.length,0)
  assert.equal(task.answer.length,0)
  assert.equal(task.steps.find(s=>s.id==='check').state,'failed')
})
test('guide derives different topic and reading scopes from user input',()=>{
  assert.deepEqual(runCulturalGuide('西塞端午的节期有多长？').topic_ids,['xisai'])
  assert.equal(runCulturalGuide('西塞端午的节期有多长？').dimension,'time')
  assert.equal(runCulturalGuide('苏州纪念谁？').dimension,'memory')
  assert.ok(runCulturalGuide('苏州纪念谁？').evidence.every(e=>e.source_id==='S01'))
})
