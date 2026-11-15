
function shortLabel(group,key){
 if(['age','city'].includes(group))return (group==='age'?'年龄层级 ':'城市层级 ')+String(key).replace(/^编码\s*/,'');
 return label(group,key);
}
function compareChart(rows,group,target){
 if(!rows?.length){el(target).innerHTML=empty();return;}
 const W=900,L=250,R=95,T=40,rowH=48,H=T+rows.length*rowH+32,w=W-L-R;
 const maxN=Math.max(...rows.map(r=>r.impressions),1),maxC=Math.max(...rows.map(r=>r.ctr||0),.01)*1.1;
 let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="曝光次数条形与点击率点图"><text x="${L}" y="18">青色条：曝光次数</text><text x="${L+w/2}" y="18">橙色点：点击率（独立刻度）</text>`;
 rows.forEach((r,i)=>{const y=T+i*rowH;const title=esc(`${label(group,r.group_key)}：${n(r.impressions)}次曝光，${n(r.clicks)}次点击，点击率${pct(r.ctr)}`);svg+=`<text x="${L-10}" y="${y+14}" text-anchor="end">${esc(shortLabel(group,r.group_key))}</text><rect x="${L}" y="${y}" width="${w*r.impressions/maxN}" height="20" rx="3" fill="#168b9c" opacity=".8"><title>${title}</title></rect><text x="${L+w+8}" y="${y+14}">${n(r.impressions)}</text><line x1="${L}" x2="${L+w}" y1="${y+31}" y2="${y+31}" stroke="#dce5ec"/><circle cx="${L+w*(r.ctr||0)/maxC}" cy="${y+31}" r="5" fill="#df8749"><title>${title}</title></circle><text x="${L+w+8}" y="${y+35}">${pct(r.ctr)}</text>`;});
 svg+=`<text x="${L}" y="${H-3}">点击率刻度：0%</text><text x="${L+w}" y="${H-3}" text-anchor="end">${pct(maxC)}</text></svg>`;
 el(target).innerHTML=svg;
}
function rankChart(d){
 const rows=d.ranking.slice(0,10), group=d.ranking_group;
 if(!rows.length){el('rank-chart').innerHTML=empty();el('scatter').innerHTML=empty();return;}
 const max=Math.max(...rows.map(r=>d.ranking_order==='ctr'?r.ctr:r.clicks),.0001);
 el('rank-chart').innerHTML=rows.map((r,i)=>{const value=d.ranking_order==='ctr'?r.ctr:r.clicks;return `<div class="bar-row"><div class="bar-top"><strong>${i+1}. ${esc(shortLabel(group,r.group_key))}</strong><span>${d.ranking_order==='ctr'?pct(value):n(value)+'次点击'} · ${n(r.impressions)}次曝光</span></div><div class="track"><div class="fill" style="width:${100*value/max}%"></div></div></div>`;}).join('');
 const W=900,H=330,L=75,R=30,T=25,B=55,w=W-L-R,h=H-T-B;
 const mx=Math.max(...d.ranking.map(r=>r.impressions),1)*1.1,my=Math.max(...d.ranking.map(r=>r.ctr||0),.01)*1.15;
 let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="当前展示对象的曝光量与点击率散点图">`;
 for(let i=0;i<=4;i++){const y=T+h-i*h/4;svg+=`<line x1="${L}" x2="${W-R}" y1="${y}" y2="${y}" stroke="#dce5ec"/><text x="${L-10}" y="${y+4}" text-anchor="end">${pct(my*i/4)}</text><text x="${L+i*w/4}" y="${H-B+22}" text-anchor="middle">${n(Math.round(mx*i/4))}</text>`;}
 if(d.overview.ctr!=null&&d.overview.ctr<=my){const y=T+h-h*d.overview.ctr/my;svg+=`<line x1="${L}" x2="${W-R}" y1="${y}" y2="${y}" stroke="#df8749" stroke-dasharray="5 5"><title>当前筛选范围整体点击率 ${pct(d.overview.ctr)}；仅作描述参考</title></line>`;}
 d.ranking.forEach(r=>svg+=`<circle tabindex="0" cx="${L+w*r.impressions/mx}" cy="${T+h-h*(r.ctr||0)/my}" r="6" fill="#168b9c" opacity=".75"><title>${esc(label(group,r.group_key))}：${n(r.impressions)}次曝光，${n(r.clicks)}次点击，点击率${pct(r.ctr)}</title></circle>`);
 svg+=`<text x="${L}" y="15">点击率</text><text x="${W-R}" y="${H-6}" text-anchor="end">曝光次数</text></svg>`;el('scatter').innerHTML=svg;
}
function heatmap(rows){
 if(!rows.length){el('heatmap').innerHTML=empty();return;}
 const positions=[...new Set(rows.map(r=>r.group_key))],groups=[...new Set(rows.map(r=>r.second_key))];
 const max=Math.max(...rows.map(r=>r.ctr||0),.0001);
 el('heatmap').innerHTML='<table><thead><tr><th>年龄层级</th>'+positions.map(p=>`<th>${esc(label('resource',p))}</th>`).join('')+'</tr></thead><tbody>'+groups.map(g=>'<tr><td>'+esc(shortLabel('age',g))+'</td>'+positions.map(p=>{const r=rows.find(r=>r.group_key===p&&r.second_key===g);return r?`<td class="heat-cell" style="background:rgba(22,139,156,${.06+.4*(r.ctr||0)/max})" title="${n(r.clicks)}次点击；${n(r.impressions)}次曝光"><strong>${pct(r.ctr)}</strong><small>${n(r.impressions)}次曝光 · ${n(r.clicks)}次点击</small></td>`:'<td>无曝光</td>';}).join('')+'</tr>').join('')+'</tbody></table><p>颜色越深，点击率越高；各次筛选使用当前最大值着色，不宜跨筛选比较颜色。小样本颜色偏深不代表可靠优势。</p>';
}
function coverageChart(q){
 const coverage=q.profile_row_coverage;
 if(coverage==null){el('coverage-chart').innerHTML=empty();return;}
 el('coverage-chart').innerHTML=`<div class="coverage-track" role="img" aria-label="画像匹配曝光占比${pct(coverage)}"><div style="width:${100*coverage}%"></div></div><div class="coverage-key"><span>已匹配画像：${pct(coverage)}</span><span>未匹配画像：${pct(1-coverage)}</span></div><p>按质量检查范围内的曝光次数计算；已匹配不代表所有画像属性完整。</p>`;
}
function visuals(d){
 compareChart(d.resources,'resource','resources');
 for(const key of ['gender','shopping','pvalue']){
  if(d.audiences)compareChart(d.audiences[key],key,key+'-chart');
  else el(key+'-chart').innerHTML=empty('请重启看板服务以载入新增人群统计。');
 }
 rankChart(d);heatmap(d.cross);coverageChart(d.quality);
}
// Labels are presentation only; raw grouping keys remain unchanged.
const groupNames={campaign:'广告计划ID（匿名）',advertiser:'广告主ID（匿名）',category:'商品类目ID（匿名）',brand:'品牌ID（匿名）',ad:'广告单元ID（匿名）',resource:'广告展示位置ID',pid:'广告展示位置ID',age:'年龄层级',gender:'性别',shopping:'购物深度',pvalue:'消费档次',city:'城市层级编码'};
const codeLabels={gender:{1:'男',2:'女'},shopping:{1:'浅层用户',2:'中度用户',3:'深度用户'},pvalue:{1:'低消费档次',2:'中消费档次',3:'高消费档次'}};
function label(group,value){
 const raw=String(value??'');
 if(!raw || ['未知','未匹配画像','属性缺失'].includes(raw))return raw==='未匹配画像'?'未关联到用户画像':raw==='属性缺失'?'已关联画像，当前属性未提供':raw||'未提供';
 const code=raw.replace(/^编码\s*/, '');
 if(codeLabels[group]?.[code])return codeLabels[group][code]+'（'+code+'）';
 if(['age','city'].includes(group))return groupNames[group]+' '+code+'（具体映射未核实）';
 return (groupNames[group]||'对象')+' '+raw;
}
function insights(d){
 const notes=[], o=d.overview;
 if(!o.impressions){el('findings').innerHTML=empty();return;}
 const daily=d.daily.filter(r=>r.impressions>0);
 if(daily.length){const peak=daily.reduce((a,b)=>a.impressions>=b.impressions?a:b);notes.push(['总体与趋势',`当前范围有${n(o.impressions)}次曝光、${n(o.clicks)}次点击，点击率${pct(o.ctr)}。曝光最多的是${peak.group_key}，占当前曝光的${pct(peak.impressions/o.impressions)}。`]);}
 const rs=d.resources.filter(r=>r.impressions>0);
 if(rs.length>1){const a=rs.reduce((a,b)=>a.ctr>=b.ctr?a:b), b=rs.reduce((a,b)=>a.ctr<=b.ctr?a:b);notes.push(['资源位差异',`${label('resource',a.group_key)}点击率${pct(a.ctr)}，比${label('resource',b.group_key)}高${((a.ctr-b.ctr)*100).toFixed(2)}个百分点；曝光分别为${n(a.impressions)}和${n(b.impressions)}。差异也可能与广告和人群构成有关。`]);}
 const threshold=Math.max(1,Number(d.ranking_min_impressions)||0);
 const candidates=d.ranking.filter(r=>r.impressions>=threshold && r.ctr!=null);
 if(candidates.length){const best=candidates.reduce((a,b)=>a.ctr>=b.ctr?a:b);notes.push(['值得进一步观察',`在当前展示的${d.ranking.length}组中，曝光至少${n(threshold)}次的对象里，${label(d.ranking_group,best.group_key)}点击率最高（${pct(best.ctr)}，${n(best.impressions)}次曝光、${n(best.clicks)}次点击）。可继续按人群、日期和资源位拆分观察。此处不代表全部对象的点击率第一，也不代表统计显著。`]);}else{notes.push(['值得进一步观察',`当前展示的分组中没有达到${n(threshold)}次曝光的对象，暂不判断高点击率对象。`]);}
 notes.push(['画像覆盖',`质量检查范围内，${pct(d.quality.profile_row_coverage)}的曝光匹配到画像。未知群体保留在统计中；缺失属性不能解释成真实人群特征。`]);
 el('findings').innerHTML=notes.map(([title,body])=>`<article class="finding"><h3>${esc(title)}</h3><p>${esc(body)}</p></article>`).join('');
}
let current = null;
let optionsReady = false;
const el = id => document.getElementById(id);
const n = v => Number(v).toLocaleString('zh-CN');
const pct = v => v == null ? '—' : (v * 100).toFixed(2) + '%';
const fixed = v => v == null ? '—' : Number(v).toFixed(2);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function empty(msg='当前范围没有有效曝光'){return `<div class="empty">${esc(msg)}</div>`;}
function bars(rows, target, group){
 if(!rows.length){el(target).innerHTML=empty();return;}
 const max=Math.max(...rows.map(r=>r.impressions),1);
 el(target).innerHTML=rows.map(r=>`<div class="bar-row"><div class="bar-top"><strong>${esc(label(group,r.group_key))}</strong><span>${n(r.impressions)} 次曝光 · 点击率 ${pct(r.ctr)}</span></div><div class="track"><div class="fill" style="width:${100*r.impressions/max}%"></div></div></div>`).join('');
}
function trend(rows){
 if(!rows.length){el('trend').innerHTML=empty();return;}
 const W=1120,H=260,L=65,R=70,T=25,B=38,w=W-L-R,h=H-T-B;
 const maxN=Math.max(...rows.map(r=>r.impressions),1)*1.15,maxC=Math.max(...rows.map(r=>r.ctr||0),.01)*1.2;
 const step=w/rows.length,bw=Math.min(60,step*.55),xs=rows.map((r,i)=>L+step*(i+.5));
 let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="每日曝光柱状图与点击率折线图"><text x="${L}" y="13">曝光次数</text><text x="${W-R}" y="13" text-anchor="end">点击率</text>`;
 for(let i=0;i<=4;i++){const y=T+h-h*i/4;s+=`<line class="axis" x1="${L}" x2="${W-R}" y1="${y}" y2="${y}"/><text x="${L-10}" y="${y+4}" text-anchor="end">${Math.round(maxN*i/4/1000)}千</text><text x="${W-R+10}" y="${y+4}">${pct(maxC*i/4)}</text>`;}
 rows.forEach((r,i)=>{const bh=h*r.impressions/maxN;s+=`<rect x="${xs[i]-bw/2}" y="${T+h-bh}" width="${bw}" height="${bh}" rx="4" fill="#168b9c" opacity=".8"><title>${esc(r.group_key)}：${n(r.impressions)}曝光，${n(r.clicks)}点击，点击率 ${pct(r.ctr)}</title></rect><text x="${xs[i]}" y="${H-12}" text-anchor="middle">${esc(r.group_key.slice(5))}</text>`;});
 s+=`<polyline fill="none" stroke="#df8749" stroke-width="3" points="${rows.map((r,i)=>xs[i]+','+(T+h-h*(r.ctr||0)/maxC)).join(' ')}"/>`;
 rows.forEach((r,i)=>{s+=`<circle cx="${xs[i]}" cy="${T+h-h*(r.ctr||0)/maxC}" r="4" fill="#df8749"/>`;});
 el('trend').innerHTML=s+'</svg>';
}
function hours(rows){
 if(!rows.length){el('hours').innerHTML=empty();return;}
 const vals=Array.from({length:24},(_,i)=>rows.find(r=>+r.group_key===i)||{group_key:String(i),impressions:0,ctr:null});
 const W=1120,H=170,L=45,R=15,T=18,B=30,h=H-T-B,w=W-L-R,step=w/24,max=Math.max(...vals.map(r=>r.impressions),1)*1.1;
 let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="小时曝光分布"><line class="axis" x1="${L}" x2="${W-R}" y1="${H-B}" y2="${H-B}"/>`;
 vals.forEach((r,i)=>{const bh=h*r.impressions/max;s+=`<rect x="${L+i*step+5}" y="${T+h-bh}" width="${step-10}" height="${bh}" rx="3" fill="#608ba6"><title>${i}时：${n(r.impressions)}曝光；点击率 ${pct(r.ctr)}</title></rect><text x="${L+(i+.5)*step}" y="${H-9}" text-anchor="middle">${i}</text>`;});
 el('hours').innerHTML=s+'</svg>';
}
function rank(rows){
 if(!rows.length){el('ranking').innerHTML=empty('当前范围没有符合排行门槛的分组，可调整最小曝光量。');return;}
 el('ranking').innerHTML='<table><thead><tr><th>分组编码 / 类别</th><th>曝光量</th><th>点击量</th><th>点击率</th><th>触达用户</th><th>曝光贡献</th><th>点击贡献</th></tr></thead><tbody>'+rows.map(r=>`<tr><td>${esc(label(current.ranking_group,r.group_key))}<small>原始值：${esc(r.group_key)}</small></td><td>${n(r.impressions)}</td><td>${n(r.clicks)}</td><td>${pct(r.ctr)}</td><td>${n(r.reached_users)}</td><td>${pct(r.impression_share)}</td><td>${pct(r.click_share)}</td></tr>`).join('')+'</tbody></table>';
}
function cross(rows){
 if(!rows.length){el('cross').innerHTML=empty();return;}
 const pids=[...new Set(rows.map(r=>r.group_key))],ages=[...new Set(rows.map(r=>r.second_key))];
 el('cross').innerHTML='<table><thead><tr><th>年龄层次</th>'+pids.map(p=>`<th>${esc(label('resource',p))}</th>`).join('')+'</tr></thead><tbody>'+ages.map(a=>'<tr><td>'+esc(label('age',a))+'</td>'+pids.map(p=>{const r=rows.find(r=>r.group_key===p&&r.second_key===a);return r?`<td>${pct(r.ctr)}<small>${n(r.impressions)}次曝光</small></td>`:'<td>—</td>';}).join('')+'</tr>').join('')+'</tbody></table>';
}
function render(d){
 current=d;const o=d.overview,q=d.quality,m=d.meta;
 el('mode').textContent=m.mode==='full'?'全量版本':'开发样本 · '+(m.sample_rate*100).toFixed(0)+'%目标抽样';
 el('scope').textContent=`业务日期 ${m.start_date}—${m.end_date} · ${m.timezone} · 固定种子 ${m.sample_seed}。本版保留 ${n(m.source_selected_rows)} 条源记录；当前筛选 ${n(o.impressions)} 次有效曝光。${window.STATIC_SNAPSHOT?'当前为静态结果预览，筛选需启动本地分析服务。':''}`;
 const cards=[['样本曝光量',n(o.impressions),'有效曝光记录数'],['样本点击量',n(o.clicks),`点击用户 ${n(o.clicked_users)} 人`],['样本点击率',pct(o.ctr),`用户点击比例 ${pct(o.user_click_rate)}`],['样本触达用户',n(o.reached_users),`人均曝光 ${fixed(o.avg_impressions_per_user)} 次 · 广告单元 ${n(o.exposed_ads)} 个`]];
 el('cards').innerHTML=cards.map(c=>`<div class="card"><small>${c[0]}</small><strong>${c[1]}</strong><div class="sub">${c[2]}</div></div>`).join('');
 trend(d.daily);hours(d.hourly);bars(d.resources,'resources','resource');bars(d.audience,'audience','age');rank(d.ranking);cross(d.cross);insights(d);visuals(d);
 el('quality-note').textContent=d.quality_scope_note+'。属性缺失率仅针对已匹配画像的曝光。';
 el('quality').innerHTML=[['曝光记录的画像匹配率',pct(q.profile_row_coverage)],['触达用户的画像匹配率',pct(q.profile_user_coverage)],['曝光记录的广告信息匹配率',pct(q.ad_row_coverage)],['已匹配画像中消费档次缺失率',pct(q.pvalue_missing_rate)],['已匹配画像中城市层级缺失率',pct(q.city_missing_rate)]].map(r=>`<div class="quality-row"><span>${r[0]}</span><strong>${r[1]}</strong></div>`).join('');
 el('built').textContent=`构建时间 ${m.created_at} · ODS / DIM / DWD / DWS / ADS · 真实数据；不含行为日志扩展。`;
 if(!optionsReady){for(const [key,values]of Object.entries(d.options||{})){const select=document.querySelector(`select[name="${key}"]`);if(!select)continue;for(const v of values)select.add(new Option(label(key==='pid'?'resource':key,v),v));if(key!=='pid'){select.add(new Option('未关联到用户画像','__unmatched__'));select.add(new Option('已关联画像，当前属性未提供','__missing__'));}}optionsReady=true;}
}
async function load(){
 el('error').hidden=true;el('loading').textContent='正在按当前范围重新统计，跨日用户数精确去重…';document.body.classList.add('busy');
 const buttons=document.querySelectorAll('button');buttons.forEach(b=>b.disabled=true);
 try{if(window.STATIC_SNAPSHOT){render(window.STATIC_SNAPSHOT);return;}
 const params=new URLSearchParams(new FormData(el('filters')));const res=await fetch('/api/data?'+params);const d=await res.json();if(!res.ok)throw new Error(d.error||'查询失败');render(d);
 }catch(e){el('error').hidden=false;el('error').textContent='读取失败：'+e.message+'。请确认分析服务和数据库可用。';}
 finally{el('loading').textContent='';document.body.classList.remove('busy');buttons.forEach(b=>b.disabled=false);if(window.STATIC_SNAPSHOT){document.querySelectorAll('#filters input,#filters select,#filters button,.rank-controls input,.rank-controls select').forEach(e=>e.disabled=true);}}
}
el('filters').addEventListener('submit',e=>{e.preventDefault();load();});
el('reset').addEventListener('click',()=>{el('filters').reset();load();});
el('export').addEventListener('click',()=>{if(!current)return;const keys=['group_label','group_key','impressions','clicks','ctr','reached_users','impression_share','click_share'];const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';const titles=['分析对象名称','原始分组值','曝光次数','点击次数','点击率（小数）','触达用户数（去重）','曝光贡献率（小数）','点击贡献率（小数）'];const csv='\ufeff'+[titles.map(quote).join(','),...current.ranking.map(r=>keys.map(k=>quote(k==='group_label'?label(current.ranking_group,r.group_key):r[k])).join(','))].join('\r\n');const u=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download='ad_ranking.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);});
load();
