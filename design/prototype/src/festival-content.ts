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
  const topicNodes=ids.map((id,index)=>{
    const topic=data.themes.find(t=>t.id===id)!
    return {id:'topic-'+id,type:'topic',label:topic.full,theme:id,claim:null,x:(index-(ids.length-1)/2)*210,y:190,z:0,color:topic.color}
  })
  const festivalNode={id:'festival-'+festival_id,type:'festival',label:festivalById(festival_id)!.name+'节',theme:null,claim:null,x:0,y:290,z:0,color:'#9c382b'}
  const extraEdges=topicNodes.map(n=>({source:festivalNode.id,target:n.id,type:'festival_topic',claim:null}))
  const practiceEdges=graph.nodes.filter(n=>n.type==='practice').map(n=>({source:'topic-'+n.theme,target:n.id,type:'topic_practice',claim:n.claim}))
  return {
    nodes:[festivalNode,...topicNodes,...graph.nodes].map(node => ({...node, festival_id, cultural_topic_id:node.theme || null})),
    edges:[...extraEdges,...practiceEdges,...graph.edges].map(edge => ({...edge, festival_id,review_state:edge.type==='uncertain'?'insufficient':'not_reviewed'})),
  }
}
