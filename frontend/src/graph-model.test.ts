import test from 'node:test'
import assert from 'node:assert/strict'
import { graphFrame, evidencePath, type QueryResult } from './graph-model.ts'

const result = {
  graph: { nodes: [
    { id: 'p', type: 'paper', label: 'Synthetic paper' },
    { id: 'c1', type: 'chunk', label: 'Source one' }, { id: 'c2', type: 'chunk', label: 'Source two' },
    { id: 'term', type: 'concept', label: 'Shared term' },
    { id: 'r1', type: 'requirement', label: 'Supported need', status: 'supported' },
    { id: 'gap', type: 'requirement', label: 'Missing need', status: 'insufficient' },
  ], edges: [
    { id: 'pc1', source: 'p', target: 'c1', type: 'contains', provenance: { method: 'pdf_ingestion' } },
    { id: 'pc2', source: 'p', target: 'c2', type: 'contains', provenance: { method: 'pdf_ingestion' } },
    { id: 'ct1', source: 'c1', target: 'term', type: 'mentions', provenance: { method: 'literal_terms_v1' } },
    { id: 'ct2', source: 'c2', target: 'term', type: 'mentions', provenance: { method: 'literal_terms_v1' } },
    { id: 'support', source: 'c1', target: 'r1', type: 'supports', provenance: { method: 'quote_checked_model_support' } },
  ] },
  trace: [
    { step: 1, type: 'plan', node_ids: ['r1', 'gap'], metadata: { requirement_statuses: { r1: 'pending', gap: 'pending' } } },
    { step: 2, type: 'concept_index', metadata: { enabled: true } },
    { step: 3, type: 'retrieve', node_ids: ['c1'], metadata: {} },
    { step: 4, type: 'verify_requirement', node_ids: ['r1'], edge_ids: ['support'], metadata: { requirement_statuses: { r1: 'supported', gap: 'insufficient' } } },
    { step: 5, type: 'repair_retrieve', node_ids: ['c2'], metadata: {} },
    { step: 6, type: 'stop', metadata: {} },
  ],
} as unknown as QueryResult // Isolated synthetic test data, never rendered in the application.

test('replay reveals sources and supported status only at their recorded events', () => {
  assert.equal(graphFrame(result, 0).nodes.length, 0)
  const planned = graphFrame(result, 1)
  assert.equal(planned.nodes.length, 2)
  assert.ok(planned.nodes.every((node) => node.status === 'pending'))
  const retrieved = graphFrame(result, 3)
  assert.ok(retrieved.nodes.some((node) => node.id === 'p'))
  assert.ok(!retrieved.nodes.some((node) => node.id === 'c2'))
  assert.ok(!retrieved.edges.some((edge) => edge.type === 'supports'))
  assert.ok(graphFrame(result, 4).edges.some((edge) => edge.id === 'support'))
  assert.equal(graphFrame(result).nodes.length, 6)
})

test('requirement focus does not pretend term co-occurrence is support', () => {
  const graph = graphFrame(result)
  const path = evidencePath(graph, 'r1')
  assert.ok(path.nodes.has('c1') && path.nodes.has('p'))
  assert.ok(!path.nodes.has('c2'))
  assert.deepEqual([...evidencePath(graph, 'gap').nodes], ['gap'])
  assert.equal(evidencePath(graph, 'gap').edges.size, 0)
})

test('render copies cannot overwrite persisted backend graph data', () => {
  const original = JSON.stringify(result)
  const graph = graphFrame(result)
  graph.nodes[0]!.label = 'renderer mutation'
  graph.edges[0]!.provenance.method = 'renderer mutation'
  assert.equal(JSON.stringify(result), original)
})

test('large graphs retain requirements and drop dangling edges when capped', () => {
  const large = structuredClone(result)
  for (let index = 0; index < 150; index++) large.graph!.nodes!.push({ id: `extra_${index}`, type: 'concept', label: 'Test-only term' })
  const graph = graphFrame(large)
  assert.equal(graph.nodes.length, 120)
  assert.equal(graph.truncated, true)
  assert.ok(graph.nodes.some((node) => node.id === 'gap'))
  const ids = new Set(graph.nodes.map((node) => node.id))
  assert.ok(graph.edges.every((edge) => ids.has(edge.source) && ids.has(edge.target)))
})
