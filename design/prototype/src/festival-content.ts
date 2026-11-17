import { themes, claims, sources, questions, graphFor } from './content.mjs'
import { festivalById } from './festivals.ts'

// Keep publishing status separate from each source/claim's existing review status.
// Local IDs stay stable so previous browser archives remain readable.
export function getFestivalContent(festival_id: string) {
  const config = festivalById(festival_id)
  const topicIds = config?.status === 'published' ? config.cultural_topics : []
  return {
    themes: themes.filter(t => topicIds.includes(t.id)).map(t => ({...t, festival_id, cultural_topic_id:t.id})),
    claims: claims.filter(c => c.theme ? topicIds.includes(c.theme) : festival_id === 'duanwu' && config?.status === 'published').map(c => ({...c, festival_id, cultural_topic_id:c.theme})),
    sources: Object.fromEntries(Object.entries(sources).filter(([id]) => config?.status === 'published' && config.source_references.includes(id)).map(([id, source]) => [id, {...source, festival_id}])),
    questions: festival_id === 'duanwu' && config?.status === 'published' ? questions.map(q => ({...q, festival_id})) : [],
  }
}

export function festivalGraph(festival_id: string, topicIds: string[], mode = 'strata', dimension = 'practice') {
  const data = getFestivalContent(festival_id)
  const ids = topicIds.filter(id => data.themes.some(t => t.id === id))
  if (!ids.length) return {nodes:[], edges:[]}
  const graph = graphFor(ids, mode, dimension)
  return {
    nodes:graph.nodes.map(node => ({...node, festival_id, cultural_topic_id:node.theme || null})),
    edges:graph.edges.map(edge => ({...edge, festival_id})),
  }
}
