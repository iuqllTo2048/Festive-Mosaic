// Curated public-source excerpts. Static demonstration, never a generated RAG result.
export const sources = {
  S01:{id:'S01',title:'端午节（苏州端午习俗）',publisher:'苏州市非物质文化遗产保护管理办公室',url:'https://szfy.wglj.suzhou.com.cn/fy-project/16',category:'地方官方非遗项目条目',locator:'正文第二段 · 四类习俗',quote:'以龙舟竞渡等活动纪念伍子胥',checked:'2026-11-16',note:'网页已核对；文化关系尚未经独立人工审读。公开可读不代表图像可自由使用。'},
  S02:{id:'S02',title:'端午节（汨罗江畔端午习俗）',publisher:'中国非物质文化遗产网',url:'https://www.ihchina.cn/project_details/14916.html',category:'国家级非遗项目条目',locator:'项目介绍 · 第一、二段',quote:'祭龙和祭祀屈原等特殊风俗',checked:'2026-11-16',note:'农历节期与活动均按此条目摘编，不视作每年活动安排。'},
  S03:{id:'S03',title:'端午节（西塞神舟会）',publisher:'中国非物质文化遗产网',url:'https://www.ihchina.cn/project_details/14913/',category:'国家级非遗项目条目',locator:'项目介绍 · 第一至三段',quote:'禳灾祈福',checked:'2026-11-16',note:'条目也提及与祭吊屈原传说相联系，不宜将其简化为单一纪念传统。'},
  S04:{id:'S04',title:'端午节专题',publisher:'中国非物质文化遗产网',url:'https://www.ihchina.cn/duanwujie',category:'官方节日专题',locator:'专题导言',quote:'各种活动因地域差别而略有不同',checked:'2026-11-16',note:'总述提供节日背景，不能替代每项地方关系的具体出处。'},
}
export const themes=[
  {id:'suzhou',name:'苏州',full:'苏州端午习俗',number:'01',subtitle:'在竞渡与生活之间',memory:'纪念伍子胥',practice:'龙舟竞渡 · 佩香包',time:'五月初五为节日节点',timeNote:'本次摘编未定位完整地方节期',source:'S01',color:'#8e4539'},
  {id:'miluo',name:'汨罗江畔',full:'汨罗江畔端午习俗',number:'02',subtitle:'从龙舟走近地方纪念',memory:'祭祀屈原',practice:'赛龙舟 · 祭龙',time:'农历五月初一至十五',timeNote:'依据当前项目条目；非本年度日程',source:'S02',color:'#49675c'},
  {id:'xisai',name:'西塞',full:'西塞神舟会',number:'03',subtitle:'让一艘神舟承载祈愿',memory:'禳灾祈福；也关联祭吊屈原传说',practice:'制作神舟 · 巡游 · 送舟入江',time:'四月初八起；五月十五至十八为会期',timeNote:'按项目条目所述的农历仪程',source:'S03',color:'#8b713b'},
]
export const claims=[
  {id:'sz-race',theme:'suzhou',dimension:'practice',feature:'race',practice:'龙舟竞渡',interpretation:'地方纪念',title:'龙舟竞渡，在这里关联伍子胥的纪念。',text:'苏州地方官方条目将胥门、胥江等地的龙舟竞渡与纪念伍子胥联系起来。此处呈现的是地方实践记录，不推断端午节的单一起源。',source:'S01',status:'located'},
  {id:'sz-sachet',theme:'suzhou',dimension:'practice',feature:'sachet',practice:'佩香包',interpretation:'日常生活智慧',title:'节俗也进入了日常衣饰与生活。',text:'条目将做香包、悬艾叶菖蒲等归入适应自然与生活的习俗，另列丝织服饰和饮食相关实践。不能把民间寓意理解为医学疗效。',source:'S01',status:'located'},
  {id:'sz-memory',theme:'suzhou',dimension:'memory',feature:'wuzixu',practice:'地方纪念',interpretation:'伍子胥',title:'一种地方纪念传统，不必覆盖所有地方。',text:'苏州条目记载纪念伍子胥的活动。这与其他地方记录的纪念传统可以并存；本原型不判断谁才是端午唯一的起源人物。',source:'S01',status:'located'},
  {id:'ml-race',theme:'miluo',dimension:'practice',feature:'race',practice:'赛龙舟',interpretation:'地方礼俗',title:'同样有龙舟，资料中的活动组合却不同。',text:'汨罗项目条目同时记载赛龙舟及雕龙头、龙舟下水、祭龙等活动。共享竞渡元素，不表示仪式过程与其他地方完全一致。',source:'S02',status:'located'},
  {id:'ml-memory',theme:'miluo',dimension:'memory',feature:'quyuan',practice:'地方祭祀',interpretation:'屈原',title:'沿江礼俗与对屈原的纪念相联系。',text:'项目介绍直接提及祭祀屈原等风俗，也描述人们对先贤的怀念。此处没有从传说推导完整的历史传承链。',source:'S02',status:'located'},
  {id:'ml-time',theme:'miluo',dimension:'time',feature:'period-miluo',practice:'节期展开',interpretation:'不只一天',title:'条目中的节期，从五月初一延续到十五。',text:'本条记录使用项目介绍的一般性描述。它不等于当年活动日历，也不保证所有社区在相同日期开展相同仪式。',source:'S02',status:'located'},
  {id:'xs-boat',theme:'xisai',dimension:'practice',feature:'send-boat',practice:'制作、巡游与送神舟',interpretation:'共同的祈愿',title:'这艘舟的叙事，是制作、巡游与送行。',text:'西塞条目记载制作神舟、唱戏、巡游和送神舟下水等活动。本次对照不把送神舟直接归为龙舟竞速。',source:'S03',status:'located'},
  {id:'xs-memory',theme:'xisai',dimension:'memory',feature:'blessing',practice:'送神舟',interpretation:'禳灾祈福',title:'祈愿与纪念，在资料中可以同时存在。',text:'条目以禳灾祈福解释送神舟，也提及活动与祭吊屈原传说的联系。这里保留这两层叙述，不把西塞概括为只有祈福、没有纪念。',source:'S03',status:'located'},
  {id:'xs-time',theme:'xisai',dimension:'time',feature:'period-xisai',practice:'扎制至送行',interpretation:'较长的仪程',title:'节日的时间，也有地方性的展开方式。',text:'条目从农历四月初八的开工写起，列出五月十五至十八的正式会期。日期属于条目记录，不是本年度通知。',source:'S03',status:'located'},
  {id:'question-link',theme:null,dimension:'practice',feature:'unknown',practice:'舟的共同意象',interpretation:'候选联系',title:'出现舟，是否就意味着同一种文化解释？',text:'当前资料能分别定位竞渡与送神舟，却不足以据此认定三地存在同一传承链。把这个联系先留作问题，等待更多原始材料与独立人工审读。',source:null,status:'uncertain'},
]
export const questions=[
  {id:'memory',title:'同一个端午，纪念的是同一个人吗？',category:'纪念传统',intro:'先看地方实践，再读资料怎样解释它。'},
  {id:'practice',title:'都与舟有关，仪式就相同吗？',category:'水上实践',intro:'让共享元素与各自的活动过程同时显现。'},
  {id:'time',title:'端午的故事，只发生在一天吗？',category:'节期节奏',intro:'阅读资料中的时间，保留未能确认的空白。'},
]
export const excerpts={
  'sz-race':['龙舟竞渡','纪念伍子胥'],'sz-sachet':['做香包','悬艾叶菖蒲'],'sz-memory':['纪念伍子胥'],
  'ml-race':['赛龙舟'],'ml-memory':['祭龙和祭祀屈原等特殊风俗'],'ml-time':['从五月初一开始，十五结束'],
  'xs-boat':['送神舟下水'],'xs-memory':['禳灾祈福'],'xs-time':['四月初八','五月十五至十八'],
}
export function themeById(id){ return themes.find(t=>t.id===id) }
export function claimById(id){ return claims.find(c=>c.id===id) }
export function compare(a,b,dimension='practice'){
  const left=claims.filter(c=>c.theme===a&&c.dimension===dimension)
  const right=claims.filter(c=>c.theme===b&&c.dimension===dimension)
  const common=[...new Set(left.map(c=>c.feature).filter(f=>right.some(c=>c.feature===f)))]
  return {left,right,common,commonClaims:claims.filter(c=>(c.theme===a||c.theme===b)&&c.dimension===dimension&&common.includes(c.feature))}
}
export function graphFor(ids,mode='strata',dimension='practice'){
  const chosen=claims.filter(c=>ids.includes(c.theme)&&c.dimension===dimension)
  const nodes=[],edges=[]
  const add=n=>{ if(!nodes.some(x=>x.id===n.id))nodes.push(n) }
  chosen.forEach((c,i)=>{
    const theme=themeById(c.theme),side=ids.indexOf(c.theme),row=chosen.filter(x=>x.theme===c.theme).indexOf(c)
    const x=mode==='compare'?(side===0?-250:250):((side-(ids.length-1)/2)*170)
    add({id:c.id,type:'practice',label:c.practice,claim:c.id,theme:c.theme,x,y:80-row*50,z:row*15,color:theme.color})
    const interpretationId='meaning-'+c.id
    add({id:interpretationId,type:'interpretation',label:c.interpretation,claim:c.id,theme:c.theme,x,y:-20-row*50,z:35,color:'#66756a'})
    add({id:c.source,type:'source',label:c.source+' · '+sources[c.source].title,claim:c.id,theme:c.theme,x,y:-150,z:-20,color:'#8d7b54'})
    edges.push({source:c.id,target:interpretationId,type:'interpretation',claim:c.id},{source:interpretationId,target:c.source,type:'source',claim:c.id})
    if(mode==='compare'&&compare(ids[0],ids[1],dimension).common.includes(c.feature)){
      add({id:'shared-'+c.feature,type:'shared',label:'共同记录 · 龙舟竞渡',claim:c.id,x:0,y:75,z:0,color:'#49675c'})
      edges.push({source:c.id,target:'shared-'+c.feature,type:'comparison',claim:c.id})
    }
  })
  if(mode!=='compare'&&dimension==='practice'){
    add({id:'question-link',type:'uncertain',label:'同一传承？待核查',claim:'question-link',x:180,y:155,z:60,color:'#8a6959'})
    chosen.filter(c=>c.feature==='race'||c.feature==='send-boat').forEach(c=>edges.push({source:c.id,target:'question-link',type:'uncertain',claim:'question-link'}))
  }
  return {nodes,edges}
}
