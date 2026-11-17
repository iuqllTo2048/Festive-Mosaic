import test from 'node:test'
import assert from 'node:assert/strict'
import { festivals, featureAvailable } from './festivals.ts'
import { parseRoute, routeHash } from './navigation.ts'
import { getFestivalContent, festivalGraph } from './festival-content.ts'

test('only actual published content exposes workspaces and references', () => {
  assert.equal(festivals.length, 6)
  assert.deepEqual(festivals.filter(f => f.status === 'published').map(f => f.festival_id), ['duanwu'])
  for (const f of festivals) {
    const data = getFestivalContent(f.festival_id)
    if (f.status !== 'published') {
      assert.deepEqual(f.available_features, [])
      assert.deepEqual(data.themes, [])
      assert.deepEqual(data.claims, [])
      assert.deepEqual(data.sources, {})
      assert.equal(featureAvailable(f.festival_id, 'explore'), false)
      assert.equal(parseRoute(`#/festivals/${f.festival_id}/explore`).page, 'unavailable')
    } else {
      assert.deepEqual(data.themes.map(t => t.id), f.cultural_topics)
      assert.deepEqual(Object.keys(data.sources), f.source_references)
      assert.ok(data.claims.every(c => c.festival_id === f.festival_id && (!c.cultural_topic_id || f.cultural_topics.includes(c.cultural_topic_id))))
      assert.ok(data.claims.every(c => c.status === 'uncertain' || data.sources[c.source]))
    }
  }
})
test('new routes, legacy bookmarks and direct navigation resolve without false exhibits', () => {
  assert.equal(parseRoute('').page, 'portal')
  assert.equal(parseRoute('#/').page, 'portal')
  for (const [old, page] of Object.entries({home:'festival', explore:'explore', compare:'compare', archive:'archive'})) {
    assert.deepEqual(parseRoute('#'+old), {page, festival_id:'duanwu'})
    assert.equal(parseRoute(routeHash(page)).page, page)
  }
  assert.equal(parseRoute('#/festivals/unknown').page, 'unavailable')
  assert.equal(parseRoute('#/festivals/duanwu/nonexistent').page, 'unavailable')
  assert.deepEqual(parseRoute('#/archive'), {page:'archive', festival_id:null})
})
test('scoped cultural records retain all existing local archive identifiers and review states', () => {
  const data = getFestivalContent('duanwu')
  assert.equal(data.themes.length, 3)
  assert.equal(data.claims.length, 10)
  assert.equal(data.claims.find(c => c.id === 'sz-race').status, 'located')
  assert.equal(data.claims.find(c => c.id === 'question-link').source, null)
  assert.deepEqual(getFestivalContent('unknown').claims, [])
})

test('graphs only accept the published festival topic scope and preserve source identities', () => {
  assert.deepEqual(festivalGraph('zhongqiu', ['suzhou']), {nodes:[], edges:[]})
  assert.deepEqual(festivalGraph('duanwu', ['unknown']), {nodes:[], edges:[]})
  const graph = festivalGraph('duanwu', ['suzhou','miluo'])
  assert.ok(graph.nodes.every(n => n.festival_id === 'duanwu'))
  assert.ok(graph.edges.every(e => e.festival_id === 'duanwu'))
  assert.ok(graph.nodes.some(n => n.id === 'S01'))
})
