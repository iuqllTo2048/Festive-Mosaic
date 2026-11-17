import { festivalById, featureAvailable, type FestivalFeature } from './festivals.ts'

export type Page = 'portal' | 'festival' | 'explore' | 'compare' | 'archive' | 'unavailable'
export interface Route { page: Page; festival_id: string | null }
const legacy: Record<string, Page> = { home:'festival', explore:'explore', compare:'compare', archive:'archive' }
export function parseRoute(hash: string): Route {
  const path = hash.replace(/^#/, '').replace(/\/$/, '')
  if (!path || path === '/') return {page:'portal', festival_id:null}
  if (legacy[path]) return {page:legacy[path], festival_id:'duanwu'}
  if (path === '/archive') return {page:'archive', festival_id:null}
  const match = /^\/festivals\/([a-z0-9-]+)(?:\/(explore|compare|archive))?$/.exec(path)
  if (!match) return {page:'unavailable', festival_id:null}
  const [, id, feature] = match
  const festival = festivalById(id)
  if (festival?.status !== 'published' || (feature && !featureAvailable(id, feature as FestivalFeature))) return {page:'unavailable', festival_id:id}
  return {page:(feature || 'festival') as Page, festival_id:id}
}
export function routeHash(page: Page, id = 'duanwu'): string {
  if (page === 'portal') return '#/'
  if (page === 'archive') return '#/archive'
  return `#/festivals/${id}${page === 'festival' ? '' : '/' + page}`
}
