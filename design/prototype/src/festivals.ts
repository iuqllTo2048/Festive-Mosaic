export type FestivalStatus = 'published' | 'in_preparation' | 'planned'
export type FestivalFeature = 'explore' | 'graph' | 'compare' | 'sources' | 'archive'
export interface Festival {
  festival_id: string
  name: string
  subtitle: string
  description: string
  visual_asset: string | null
  status: FestivalStatus
  available_features: FestivalFeature[]
  cultural_topics: string[]
  source_references: string[]
  accent: string
  index_note: string
}

export const statusLabels: Record<FestivalStatus, string> = {
  published: '已开放', in_preparation: '策展中', planned: '规划中',
}

// Descriptions of unopened subjects are editorial intentions, not researched exhibits.
export const festivals: Festival[] = [
  { festival_id:'chunjie', name:'春节', subtitle:'团圆与新岁的地方表达', description:'拟从地方年俗出发，整理迎新与团聚的不同表达。专题资料与视觉正在策划。', visual_asset:null, status:'in_preparation', available_features:[], cultural_topics:[], source_references:[], accent:'#9c382b', index_note:'新岁 / 团聚' },
  { festival_id:'yuanxiao', name:'元宵', subtitle:'灯火之间的公共生活', description:'拟围绕灯俗与地方节庆展开资料整理，尚未开放文化探索。', visual_asset:null, status:'planned', available_features:[], cultural_topics:[], source_references:[], accent:'#9b582d', index_note:'灯火 / 相聚' },
  { festival_id:'qingming', name:'清明', subtitle:'追思与春日的地方记忆', description:'拟研究追思与春日实践在不同地方的表达，尚未建立专题资料。', visual_asset:null, status:'planned', available_features:[], cultural_topics:[], source_references:[], accent:'#536b56', index_note:'追思 / 春日' },
  { festival_id:'duanwu', name:'端午', subtitle:'不同的地方记忆', description:'在苏州、汨罗江畔与黄石西塞，沿着舟、地方纪念与仪程，探索三份端午文化记录。', visual_asset:'images/hero_dragon_boat.webp', status:'published', available_features:['explore','graph','compare','sources','archive'], cultural_topics:['suzhou','miluo','xisai'], source_references:['S01','S02','S03','S04'], accent:'#253d34', index_note:'舟行 / 纪念' },
  { festival_id:'qixi', name:'七夕', subtitle:'巧艺与生活的细密联系', description:'拟从巧艺与生活实践整理地方文化线索，专题尚未开放。', visual_asset:null, status:'planned', available_features:[], cultural_topics:[], source_references:[], accent:'#79565b', index_note:'巧艺 / 生活' },
  { festival_id:'zhongqiu', name:'中秋', subtitle:'月下相聚的多种方式', description:'拟研究不同地方的祭月、灯俗与相聚方式，尚未开发专题内容。', visual_asset:null, status:'in_preparation', available_features:[], cultural_topics:[], source_references:[], accent:'#8b6d32', index_note:'月色 / 相聚' },
]
export const festivalById = (id: string) => festivals.find(f => f.festival_id === id)
export const featureAvailable = (id: string, feature: FestivalFeature) => {
  const festival = festivalById(id)
  return festival?.status === 'published' && festival.available_features.includes(feature)
}
