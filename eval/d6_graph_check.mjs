// Offline model/provenance checks only; browser rendering is verified separately.
import fs from 'node:fs'
import assert from 'node:assert/strict'
import { performance } from 'node:perf_hooks'
import { graphFrame, evidencePath } from '../frontend/src/graph-model.ts'
const root = new URL('../', import.meta.url)
const result = JSON.parse(fs.readFileSync(new URL('artifacts/d5/E7-repair_on.json',root),'utf8')).result
const before = JSON.stringify(result)
const response=await fetch(`http://127.0.0.1:8000/api/runs/${result.run_id}`)
assert.equal(response.status,200)
assert.deepEqual(await response.json(),result)
const graph = graphFrame(result)
const supported = result.requirements.find(r=>r.status==='supported')
const gap = result.requirements.find(r=>r.status==='insufficient')
const path = evidencePath(graph,supported.id)
const actualSources = new Set(result.evidence.filter(e=>e.validated&&supported.evidence_ids.includes(e.id)).map(e=>e.chunk_id))
for(const id of actualSources) assert.ok(path.nodes.has(id))
for(const edge of graph.edges.filter(e=>path.edges.has(e.id)&&e.type==='supports')) assert.ok(actualSources.has(edge.source))
assert.equal(evidencePath(graph,gap.id).edges.size,0)
assert.equal(evidencePath(graph,gap.id).nodes.size,1)
for(const citation of result.citations){
  const chunk=graph.nodes.find(n=>n.id===citation.chunk_id)
  assert.equal(chunk.source_ref.document_id,citation.document_id)
  assert.equal(chunk.source_ref.page,citation.page)
}
const tick=performance.now()
for(let cycle=0;cycle<100;cycle++){
  for(let cursor=0;cursor<=result.trace.length;cursor++){
    const frame=graphFrame(result,cursor)
    assert.equal(new Set(frame.nodes.map(n=>n.id)).size,frame.nodes.length)
    assert.equal(new Set(frame.edges.map(e=>e.id)).size,frame.edges.length)
    const ids=new Set(frame.nodes.map(n=>n.id))
    assert.ok(frame.edges.every(e=>ids.has(e.source)&&ids.has(e.target)))
  }
  assert.equal(graphFrame(result).nodes.length,graph.nodes.length)
  assert.equal(graphFrame(result).edges.length,graph.edges.length)
}
assert.equal(JSON.stringify(result),before)
const record={test:'D_auto',id:'graph_stress',recorded_at:new Date().toISOString(),run_id:result.run_id,
  actual_browser:false,nodes:graph.nodes.length,edges:graph.edges.length,cycles:100,
  support_focus:{nodes:path.nodes.size,edges:path.edges.size},gap_focus:{nodes:1,edges:0},
  model_replay_ms:Math.round(performance.now()-tick),data_mutation:false,gpu_memory_leak_verified:false,
  assertions:'passed',saved_api_exact_match:true,scope:'graphFrame/evidencePath plus saved API equality; no claim about GPU rendering or human semantic correctness'}
fs.appendFileSync(new URL('eval/d6_results.jsonl',root),JSON.stringify(record)+'\n')
console.log(JSON.stringify(record))
