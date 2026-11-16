import type { components } from './api/schema'

export type GraphNode = components['schemas']['GraphNode']
export type GraphEdge = components['schemas']['GraphEdge']
export type QueryResult = components['schemas']['QueryResult']
export type GraphView = { nodes: GraphNode[]; edges: GraphEdge[]; total: number; truncated: boolean }

export const nodeNames = { paper: '论文', chunk: '原文片段', concept: '术语', requirement: '证据需求' }
export const edgeNames = { contains: '包含片段', mentions: '提及术语', supports: '引用支持' }

export function graphFrame(result: QueryResult | null, cursor: number | null = null): GraphView {
  const sourceNodes = result?.graph?.nodes ?? []
  const sourceEdges = result?.graph?.edges ?? []
  const trace = result?.trace ?? []
  const finalFrame = cursor === null || cursor >= trace.length
  const visible = new Set<string>()
  const supportEdges = new Set<string>()
  const statuses = new Map<string, GraphNode['status']>()
  let conceptsIndexed = false
  if (finalFrame) sourceNodes.forEach((node) => visible.add(node.id))
  else for (const event of trace.slice(0, Math.max(0, cursor))) {
    event.node_ids?.forEach((id) => visible.add(id))
    event.edge_ids?.forEach((id) => supportEdges.add(id))
    if (event.type === 'concept_index') conceptsIndexed = event.metadata?.enabled === true
    const snapshot = event.metadata?.requirement_statuses
    if (typeof snapshot === 'object' && snapshot !== null && !Array.isArray(snapshot)) {
      for (const [id, status] of Object.entries(snapshot)) {
        if (status === 'pending' || status === 'supported' || status === 'insufficient') {
          statuses.set(id, status)
          visible.add(id)
        }
      }
    }
  }
  for (const edge of sourceEdges) {
    if (edge.type === 'contains' && visible.has(edge.target)) visible.add(edge.source)
    if (edge.type === 'mentions' && visible.has(edge.source) && (finalFrame || conceptsIndexed)) visible.add(edge.target)
  }
  const priority = { requirement: 0, paper: 1, chunk: 2, concept: 3 }
  const eligible = sourceNodes.filter((node) => visible.has(node.id))
    .sort((a, b) => priority[a.type] - priority[b.type])
  const nodes = eligible.slice(0, 120).map((node) => ({ ...node,
    source_ref: node.source_ref ? { ...node.source_ref } : node.source_ref,
    status: node.type === 'requirement' && !finalFrame ? statuses.get(node.id) ?? 'pending' : node.status,
  }))
  const ids = new Set(nodes.map((node) => node.id))
  const edges = sourceEdges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)
    && (finalFrame || edge.type !== 'supports' || supportEdges.has(edge.id)))
    .map((edge) => ({ ...edge, provenance: { ...edge.provenance } }))
  return { nodes, edges, total: eligible.length, truncated: eligible.length > 120 }
}

export function evidencePath(graph: GraphView, selectedId: string | null): { nodes: Set<string>; edges: Set<string> } {
  const selected = graph.nodes.find((node) => node.id === selectedId)
  if (!selected) return { nodes: new Set(), edges: new Set() }
  const ids = new Set([selected.id])
  const chunks = new Set<string>()
  if (selected.type === 'chunk') chunks.add(selected.id)
  for (const edge of graph.edges) {
    if (selected.type === 'requirement' && edge.type === 'supports' && edge.target === selected.id) chunks.add(edge.source)
    if (selected.type === 'paper' && edge.type === 'contains' && edge.source === selected.id) chunks.add(edge.target)
    if (selected.type === 'concept' && edge.type === 'mentions' && edge.target === selected.id) chunks.add(edge.source)
  }
  chunks.forEach((id) => ids.add(id))
  for (const edge of graph.edges) {
    if (edge.type === 'contains' && chunks.has(edge.target)) ids.add(edge.source)
    if (edge.type === 'mentions' && chunks.has(edge.source)) ids.add(edge.target)
    if (selected.type !== 'requirement' && edge.type === 'supports' && chunks.has(edge.source)) ids.add(edge.target)
  }
  return { nodes: ids, edges: new Set(graph.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)).map((edge) => edge.id)) }
}
