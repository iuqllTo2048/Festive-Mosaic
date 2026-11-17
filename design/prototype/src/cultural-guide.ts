import { claims, sources, excerpts, compare, themes } from './content.mjs'

export type GuideStatus = 'ready' | 'insufficient' | 'validation_failed'
export type Dimension = 'memory' | 'practice' | 'time'
export interface GuideStep { id:string; label:string; state:'done'|'skipped'|'failed'; detail:string }
export interface GuideEvidence { claim_id:string; source_id:string; quote:string[]; title:string; topic_id:string; dimension:Dimension }
export interface GuideAnswer { text:string; claim_ids:string[] }
export interface GuideTask {
  mode:'demo'; question:string; festival_id:'duanwu'; topic_ids:string[]; dimension:Dimension;
  status:GuideStatus; steps:GuideStep[]; evidence:GuideEvidence[]; answer:GuideAnswer[];
  gaps:string[]; model_calls:0; semantic_review:'not_run'; elapsed_ms:number
}
export const guideExample = '苏州和汨罗的端午习俗有什么不同？'
const aliases:Record<string,string[]> = {suzhou:['苏州','伍子胥'],miluo:['汨罗','屈原'],xisai:['西塞','神舟会','黄石']}
const dimensionTerms:Record<Dimension,string[]> = {memory:['纪念','人物','伍子胥','屈原','祈福'],practice:['习俗','实践','竞渡','龙舟','香包','仪式','神舟','端午'],time:['节期','时间','几天','日期','一天','初一','十五','会期']}

// A deterministic, browser-local retrieval demonstration. No LLM or network call.
export function runCulturalGuide(question:string, catalog = {claims,sources,excerpts}):GuideTask {
  const start=performance.now(), text=question.trim().slice(0,500)
  const explicit=Object.entries(aliases).filter(([,words])=>words.some(w=>text.includes(w))).map(([id])=>id)
  const unsupportedFestival=/春节|元宵|清明|七夕|中秋/.test(text)
  const hasTerms=Object.values(dimensionTerms).flat().some(w=>text.includes(w))
  const topic_ids=unsupportedFestival?[]:explicit.length?explicit:hasTerms?themes.map(t=>t.id):[]
  const dimension:Dimension=dimensionTerms.time.some(w=>text.includes(w))?'time':/纪念|人物|伍子胥|屈原/.test(text)?'memory':'practice'
  const isBroadComparison=explicit.length>=2 && /不同|差异|比较|对照|区别/.test(text) && dimension==='practice'
  const unsupportedClaim=/同一传承|同一起源|起源相同|始于|朝代|哪一年|发明|最早|距今|治病|疗效|能耗|气温|票价|今年|明年|202[0-9]/.test(text)
  const selected=catalog.claims.filter(c=>c.theme && topic_ids.includes(c.theme) && (c.dimension===dimension || isBroadComparison&&c.dimension==='memory'))
  const evidence:GuideEvidence[]=[], rejected:string[]=[]
  for (const c of selected) {
    const source=catalog.sources[c.source as keyof typeof sources]
    const quote=catalog.excerpts[c.id as keyof typeof excerpts]
    if (!source || !quote?.length || !quote.every(q=>typeof q==='string'&&q.trim()) || c.status!=='located' || !source.url.startsWith('https://')) {rejected.push(c.id);continue}
    evidence.push({claim_id:c.id,source_id:c.source!,quote:[...quote],title:c.title,topic_id:c.theme!,dimension:c.dimension as Dimension})
  }
  const gaps:string[]=[]
  if (!text) gaps.push('请先输入一个文化问题。')
  else if (unsupportedFestival) gaps.push('该节日专题尚未开放，当前没有可供回答的专题资料。')
  else if (!topic_ids.length) gaps.push('未在当前端午摘编中定位相关主题，请换用地方、实践或节期线索。')
  if (unsupportedClaim) gaps.push('当前摘编不足以回答这一历史传承、功效或年度信息问题，以下资料只能作为背景阅读。')
  for (const id of topic_ids) if (!evidence.some(e=>e.topic_id===id)) gaps.push(`${themes.find(t=>t.id===id)?.name}在这一维度的摘编不足，不能直接完成比较。`)
  if (rejected.length) gaps.push(`${rejected.length}条候选的本地来源关联检查失败，已从引用中移除。`)
  const status:GuideStatus=rejected.length?'validation_failed':gaps.length||!evidence.length?'insufficient':'ready'
  const answer:GuideAnswer[]=[]
  if (status==='ready') {
    for (const id of topic_ids) {
      const records=selected.filter(c=>c.theme===id&&evidence.some(e=>e.claim_id===c.id))
      answer.push({text:`${themes.find(t=>t.id===id)?.name}：${records.map(c=>`${c.practice} → ${c.interpretation}`).join('；')}。`,claim_ids:records.map(c=>c.id)})
    }
    if(topic_ids.length===2&&dimension==='practice') {
      const common=compare(topic_ids[0],topic_ids[1],'practice')
      answer.push({text:common.common.includes('race')?'两地摘编都记录竞渡；地方纪念与仪式组合需要分别阅读。':'当前摘编没有定位相同的实践细项，不能据此断言当地不存在相关习俗。',claim_ids:common.commonClaims.map(c=>c.id)})
    }
  }
  const steps:GuideStep[]=[
    {id:'plan',label:'任务规划',state:'done',detail:`本地规则识别${topic_ids.length}个地方；没有调用规划模型。`},
    {id:'retrieve',label:'RAG 检索',state:topic_ids.length?'done':'skipped',detail:`演示：筛选预置摘编${selected.length}条；未运行在线RAG或向量检索。`},
    {id:'relations',label:'知识关系探索',state:topic_ids.length?'done':'skipped',detail:'按地方和阅读维度组织现有关系，保留来源ID。'},
    {id:'check',label:'证据核查',state:rejected.length?'failed':evidence.length?'done':'skipped',detail:`本地字段检查保留${evidence.length}条；不验证网页现状、引句语义或历史结论。`},
    {id:'semantic',label:'语义核验',state:'skipped',detail:'尚未接入，不产生模型支持或人工认证记录。'},
    {id:'result',label:'结果展示',state:status==='validation_failed'?'failed':'done',detail:status==='ready'?'展示预置摘编及引用，可定位图谱。':'保留资料缺口，不生成问题结论。'},
  ]
  return {mode:'demo',question:text,festival_id:'duanwu',topic_ids,dimension,status,steps,evidence,answer,gaps,model_calls:0,semantic_review:'not_run',elapsed_ms:Math.round((performance.now()-start)*100)/100}
}
