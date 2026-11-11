"""F271 03 画面：同じデータから3つのダッシュボード（D1 水準グラフ型・D2 表型・D3 問いから作る型）と、
共通の「元データの表」を、それぞれ1つの HTML（外部ライブラリなし）で作る。?m=YYYY-MM で「最新月」を決める。
読む人の手順（04）が値を探せるように、答えになる要素に data-k（何の値か）と data-v（表示）を付ける。
data-item は「探すときに目に入る要素」、data-grp はそのまとまり（2段の探索に使う）。"""
import os, json
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
p = pd.read_csv(os.path.join(ROOT, "data", "processed", "panel.csv"))
G = ["百貨店", "スーパー", "コンビニ", "ドラッグストア", "ホームセンター", "家電大型専門店"]
T = "6業態合計"
months = sorted(p.ym.unique())
def ser(col, g):
    s = p[p.g == g].set_index("ym").reindex(months)[col]
    return [None if pd.isna(v) else round(float(v), 6) for v in s]
D = dict(months=months, G=G, T=T,
         lvl={g: ser("lvl", g) for g in G + [T]}, yoy={g: ser("yoy", g) for g in G + [T]},
         lo={g: ser("band_lo", g) for g in G + [T]}, hi={g: ser("band_hi", g) for g in G + [T]},
         flag={g: ser("flag", g) for g in G + [T]}, yoy12=ser("yoy12", T))
DATA = json.dumps(D, ensure_ascii=False, separators=(",", ":"))

CSS = """
*{box-sizing:border-box}body{margin:0;background:#fff;color:#1f2328;font-family:'Noto Sans CJK JP','Noto Sans JP',sans-serif;font-size:14px;line-height:1.5}
.wrap{max-width:1200px;margin:0 auto;padding:16px}h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;margin:20px 0 8px}
.sub{color:#57606a;font-size:13px}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.card{border:1px solid #d0d7de;border-radius:6px;padding:8px 10px}.cl{font-size:12px;color:#57606a}.cv{font-size:20px;font-weight:700}
svg text{font-family:inherit;font-size:11px;fill:#57606a}#tip{position:absolute;pointer-events:none;background:#24292f;color:#fff;font-size:12px;padding:3px 6px;border-radius:4px;display:none;white-space:nowrap}
.tw{overflow-x:auto}table{border-collapse:collapse;font-size:13px;white-space:nowrap}th,td{border:1px solid #d0d7de;padding:2px 6px;text-align:right}th{background:#f6f8fa}td.m{text-align:left}
a{color:#0969da}.legend span{display:inline-block;margin-right:12px;font-size:12px}.legend i{display:inline-block;width:10px;height:10px;margin-right:4px;vertical-align:middle}
.bars .row{display:grid;grid-template-columns:110px 1fr 150px;align-items:center;gap:8px;height:30px}.bars .bar{height:16px}
.sm{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:10px}.sm .p{border:1px solid #d0d7de;border-radius:6px;padding:6px 8px}
.flag{color:#bc4c00;font-weight:700;font-size:12px}.kv{font-size:24px;font-weight:700}
"""
COMMON_JS = r"""
const D=__DATA__;const Q=new URLSearchParams(location.search);const L=Q.get('m')||D.months[D.months.length-1];
const iL=D.months.indexOf(L);const MS=D.months.slice(0,iL+1);
const J=m=>{const a=m.split('-');return (+a[0])+'年'+(+a[1])+'月'};
const fL=v=>Math.round(v).toLocaleString('ja-JP')+'億円';const fP=v=>(v>=0?'+':'')+v.toFixed(1)+'%';
const NOTIP=Q.get('notip')==='1';
const tip=document.createElement('div');tip.id='tip';document.body.appendChild(tip);
function hov(el,txt){el.setAttribute('data-tip',txt);el.addEventListener('mouseenter',e=>{if(NOTIP)return;tip.textContent=txt;tip.style.display='block';const r=el.getBoundingClientRect();tip.style.left=(r.left+scrollX+8)+'px';tip.style.top=(r.top+scrollY-28)+'px'});el.addEventListener('mouseleave',()=>tip.style.display='none')}
const NS='http://www.w3.org/2000/svg';function S(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e}
function lineChart(svg,series,o){svg.innerHTML='';const W=svg.parentNode.clientWidth,H=o.h;svg.setAttribute('width',W);svg.setAttribute('height',H);
 const ml=64,mr=12,mt=10,mb=24,pw=W-ml-mr,ph=H-mt-mb;const n=series[0].m.length;let lo=Infinity,hi=-Infinity;
 for(const s of series)for(const v of s.v){if(v==null)continue;lo=Math.min(lo,v);hi=Math.max(hi,v)}
 if(o.zero){lo=Math.min(lo,0)}else{lo=lo*0.9}hi=hi*1.05;if(o.band){for(const v of o.band.lo.concat(o.band.hi)){if(v!=null){lo=Math.min(lo,v);hi=Math.max(hi,v)}}const pad=(hi-lo)*0.08;lo-=pad;hi+=pad}
 const X=i=>ml+(n<=1?0:i*pw/(n-1)),Y=v=>mt+ph*(1-(v-lo)/(hi-lo));svg.dataset.lo=lo;svg.dataset.hi=hi;svg.dataset.ph=ph;
 const gr=o.grp;for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4;S('line',{x1:ml,x2:W-mr,y1:Y(v),y2:Y(v),stroke:'#eaeef2'},svg);const t=S('text',{x:ml-6,y:Y(v)+4,'text-anchor':'end','data-item':'1','data-grp':gr},svg);t.textContent=o.yfmt(v)}
 const yrs=[];series[0].m.forEach((m,i)=>{if(m.endsWith('-01'))yrs.push(i)});const step=Math.max(1,Math.ceil(yrs.length/(pw/60)));
 yrs.forEach((i,j)=>{if(j%step)return;const t=S('text',{x:X(i),y:H-6,'text-anchor':'middle','data-item':'1','data-grp':gr},svg);t.textContent=series[0].m[i].slice(0,4)});
 if(o.band){let pts=[];o.band.hi.forEach((v,i)=>{if(v!=null)pts.push(X(i)+','+Y(v))});for(let i=o.band.lo.length-1;i>=0;i--){const v=o.band.lo[i];if(v!=null)pts.push(X(i)+','+Y(v))}S('polygon',{points:pts.join(' '),fill:'#eaeef2'},svg);S('line',{x1:ml,x2:W-mr,y1:Y(0),y2:Y(0),stroke:'#8c959f'},svg)}
 for(const s of series){const pts=s.v.map((v,i)=>v==null?null:X(i)+','+Y(v)).filter(x=>x).join(' ');S('polyline',{points:pts,fill:'none',stroke:s.c,'stroke-width':1.6,'data-item':'1','data-grp':gr},svg);
  if(o.hover){s.v.forEach((v,i)=>{if(v==null)return;const c=S('circle',{cx:X(i),cy:Y(v),r:4,fill:'transparent','data-k':'lvl|'+s.g+'|'+s.m[i],'data-v':String(Math.round(v)),'data-hover':'1','data-grp':gr},svg);hov(c,s.g+' '+J(s.m[i])+' '+fL(v))})}}}
"""
COL = {"百貨店": "#0969da", "スーパー": "#bc4c00", "コンビニ": "#1a7f37", "ドラッグストア": "#8250df", "ホームセンター": "#9a6700", "家電大型専門店": "#cf222e", T: "#24292f"}

def page(title, body, js):
    return ("<!doctype html><html lang='ja'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{title}</title><style>{CSS}</style></head><body><div class='wrap'>{body}</div><script>"
            + COMMON_JS.replace("__DATA__", DATA) + "const COL=" + json.dumps(COL, ensure_ascii=False) + ";" + js + "</script></body></html>")

# ---------- D1 水準グラフ型 ----------
D1_BODY = """<h1 data-item='1' data-grp='head'>商業動態統計 業態別販売額</h1><div class='sub' id='sub' data-item='1' data-grp='head'></div>
<h2 id='h-cards' data-item='1' data-grp='sec'></h2><div class='cards' id='cards'></div>
<h2 data-item='1' data-grp='sec'>業態別の販売額の推移</h2><label data-item='1' data-grp='sec'>業態：<select id='sel'></select></label><div><svg id='c1'></svg></div>
<h2 data-item='1' data-grp='sec'>6業態の販売額（直近5年）</h2><div class='legend' id='lg'></div><div><svg id='c2'></svg></div>
<p><a id='raw' data-item='1' data-grp='sec'>元データの表</a></p>"""
D1_JS = r"""
const sub=document.getElementById('sub');sub.textContent='データ：2014年1月〜'+J(L)+'（単位：億円）';sub.setAttribute('data-k','latest');sub.setAttribute('data-v',L);
document.getElementById('h-cards').textContent=J(L)+'の販売額';
const cards=document.getElementById('cards');for(const g of [D.T].concat(D.G)){const v=D.lvl[g][iL];const c=document.createElement('div');c.className='card';c.setAttribute('data-item','1');c.setAttribute('data-grp','cards');
 c.innerHTML='<div class="cl">'+g+'</div><div class="cv" data-k="lvl|'+g+'|'+L+'" data-v="'+Math.round(v)+'" data-grp="cards">'+fL(v)+'</div>';cards.appendChild(c)}
const sel=document.getElementById('sel');for(const g of [D.T].concat(D.G)){const o=document.createElement('option');o.value=g;o.textContent=g;sel.appendChild(o)}
const H=innerWidth<600?220:300;
function draw1(){const g=sel.value;lineChart(document.getElementById('c1'),[{g:g,m:MS,v:D.lvl[g].slice(0,iL+1),c:COL[g]}],{h:H,hover:true,grp:'c1',yfmt:v=>Math.round(v).toLocaleString('ja-JP')})}
sel.addEventListener('change',draw1);if(Q.get('sel'))sel.value=Q.get('sel');draw1();
const i0=Math.max(0,iL-59);const M5=D.months.slice(i0,iL+1);
lineChart(document.getElementById('c2'),D.G.map(g=>({g:g,m:M5,v:D.lvl[g].slice(i0,iL+1),c:COL[g]})),{h:H,hover:true,grp:'c2',yfmt:v=>Math.round(v).toLocaleString('ja-JP')});
document.getElementById('lg').innerHTML=D.G.map(g=>'<span data-item="1" data-grp="c2"><i style="background:'+COL[g]+'"></i>'+g+'</span>').join('');
document.getElementById('raw').href='table.html?m='+L;
"""
# ---------- D2 表型 ----------
D2_BODY = """<h1 data-item='1' data-grp='head'>商業動態統計 業態別販売額</h1><div class='sub' id='sub' data-item='1' data-grp='head'></div>
<div class='tw'><table id='tb'></table></div><p><a id='raw' data-item='1' data-grp='head'>元データの表（全期間）</a></p>"""
D2_JS = r"""
const sub=document.getElementById('sub');sub.textContent='直近25か月（'+J(D.months[iL-24])+'〜'+J(L)+'）。販売額は億円、前年同月比は%';sub.setAttribute('data-k','latest');sub.setAttribute('data-v',L);
const GG=D.G.concat([D.T]);let h='<thead><tr><th rowspan="2" data-item="1" data-grp="tb">月</th>'+GG.map(g=>'<th colspan="2" data-item="1" data-grp="tb">'+g+'</th>').join('')+'</tr><tr>'+GG.map(g=>'<th data-grp="tb">販売額</th><th data-grp="tb">前年比</th>').join('')+'</tr></thead><tbody>';
for(let i=iL-24;i<=iL;i++){const m=D.months[i];h+='<tr><td class="m" data-item="1" data-grp="tb">'+J(m)+'</td>';for(const g of GG){const v=D.lvl[g][i],y=D.yoy[g][i];
 h+='<td data-k="lvl|'+g+'|'+m+'" data-v="'+Math.round(v)+'">'+Math.round(v).toLocaleString('ja-JP')+'</td><td data-k="yoy|'+g+'|'+m+'" data-v="'+y.toFixed(1)+'">'+fP(y)+'</td>'}h+='</tr>'}
document.getElementById('tb').innerHTML=h+'</tbody>';document.getElementById('raw').href='table.html?m='+L;
"""
# ---------- D3 問いから作る型 ----------
D3_BODY = """<h1 data-item='1' data-grp='head'>今月の業態別販売額：前年と比べて</h1><div class='sub' id='sub' data-item='1' data-grp='head'></div>
<div class='cards' id='kpi'></div><h2 id='h-bars' data-item='1' data-grp='sec'></h2><div class='bars' id='bars'></div>
<div class='sub' data-item='1' data-grp='sec'>色つき＝前年同月比が「いつもの揺れ」（その前の36か月の平均±1.645×標準偏差）の外</div>
<h2 data-item='1' data-grp='sec'>業態別の前年同月比（直近24か月、灰色の帯＝いつもの揺れ）</h2><div class='sm' id='sm'></div>
<p><a id='raw' data-item='1' data-grp='sec'>元データの表（販売額）</a></p>"""
D3_JS = r"""
const sub=document.getElementById('sub');sub.textContent='最新：'+J(L)+'（経済産業省 商業動態統計、6業態）';sub.setAttribute('data-k','latest');sub.setAttribute('data-v',L);
const kpi=document.getElementById('kpi');kpi.style.gridTemplateColumns='repeat(auto-fill,minmax(260px,1fr))';
const ky=D.yoy[D.T][iL],k12=D.yoy12[iL];
kpi.innerHTML='<div class="card" data-item="1" data-grp="kpi"><div class="cl">6業態合計の前年同月比（'+J(L)+'）</div><div class="kv" data-k="yoy|'+D.T+'|'+L+'" data-v="'+ky.toFixed(1)+'">'+fP(ky)+'</div></div>'+
 '<div class="card" data-item="1" data-grp="kpi"><div class="cl">6業態合計 直近12か月の前年比</div><div class="kv" data-k="yoy12|'+D.T+'|'+L+'" data-v="'+k12.toFixed(1)+'">'+fP(k12)+'</div></div>';
document.getElementById('h-bars').textContent='業態別の前年同月比（'+J(L)+'、高い順）';
const rows=D.G.map(g=>({g:g,y:D.yoy[g][iL],f:D.flag[g][iL]})).sort((a,b)=>b.y-a.y);const mx=Math.max(...rows.map(r=>Math.abs(r.y)),1);
const bars=document.getElementById('bars');rows.forEach((r,j)=>{const d=document.createElement('div');d.className='row';const col=r.f===1?'#bc4c00':'#8c959f';const w=Math.abs(r.y)/mx*50;
 d.innerHTML='<div data-item="1" data-grp="bars">'+r.g+'</div><div style="position:relative;height:16px"><div style="position:absolute;left:50%;top:-4px;bottom:-4px;border-left:1px solid #57606a"></div><div class="bar" style="position:absolute;background:'+col+';width:'+w+'%;'+(r.y>=0?'left:50%':'right:50%')+'"></div></div>'+
 '<div data-item="1" data-grp="bars"><span data-k="yoy|'+r.g+'|'+L+'" data-v="'+r.y.toFixed(1)+'" data-rank="'+(j+1)+'" data-flag="'+(r.f===1?'外':'内')+'" data-grp="bars">'+fP(r.y)+'</span>'+(r.f===1?' <span class="flag" data-k="flag|'+r.g+'|'+L+'" data-v="外" data-grp="bars">いつもの揺れの外</span>':'<span data-k="flag|'+r.g+'|'+L+'" data-v="内" data-grp="bars"></span>')+'</div>';bars.appendChild(d)});
const sm=document.getElementById('sm');const i0=Math.max(0,iL-23);const M2=D.months.slice(i0,iL+1);
for(const g of D.G){const p=document.createElement('div');p.className='p';const y1=D.yoy[g][iL],y0=D.yoy[g][iL-1];
 p.innerHTML='<div data-item="1" data-grp="sm-'+g+'"><b>'+g+'</b>　今月 <span data-k="yoy|'+g+'|'+L+'" data-v="'+y1.toFixed(1)+'" data-grp="sm-'+g+'">'+fP(y1)+'</span>（先月 <span data-k="yoy|'+g+'|'+D.months[iL-1]+'" data-v="'+y0.toFixed(1)+'" data-grp="sm-'+g+'">'+fP(y0)+'</span>）</div><div><svg></svg></div>';sm.appendChild(p);
 lineChart(p.querySelector('svg'),[{g:g,m:M2,v:D.yoy[g].slice(i0,iL+1),c:COL[g]}],{h:120,hover:false,grp:'sm-'+g,zero:true,band:{lo:D.lo[g].slice(i0,iL+1),hi:D.hi[g].slice(i0,iL+1)},yfmt:v=>v.toFixed(0)+'%'})}
document.getElementById('raw').href='table.html?m='+L;
"""
# ---------- D4 問い直し用：D3 に「水準」の部分（D1 のカードと業態を選ぶ折れ線）を足したもの（結果を見てから足した） ----------
D4_BODY = D3_BODY.replace("<p><a id='raw' data-item='1' data-grp='sec'>元データの表（販売額）</a></p>", "") + """
<h2 id='h-cards' data-item='1' data-grp='sec'></h2><div class='cards' id='cards'></div>
<h2 data-item='1' data-grp='sec'>業態別の販売額の推移</h2><label data-item='1' data-grp='sec'>業態：<select id='sel'></select></label><div><svg id='c1'></svg></div>
<p><a id='raw' data-item='1' data-grp='sec'>元データの表（販売額）</a></p>"""
_a = D1_JS.index("document.getElementById('h-cards')"); _b = D1_JS.index("draw1();") + len("draw1();")
D4_JS = D3_JS + D1_JS[_a:_b]
# ---------- 元データの表（共通） ----------
TB_BODY = """<h1 data-item='1' data-grp='head'>元データ：業態別販売額（億円）</h1><div class='sub' id='sub' data-item='1' data-grp='head'></div><div class='tw'><table id='tb'></table></div>"""
TB_JS = r"""
const sub=document.getElementById('sub');sub.textContent='2014年1月〜'+J(L)+'。新しい月が下';sub.setAttribute('data-k','latest');sub.setAttribute('data-v',L);
const GG=D.G.concat([D.T]);let h='<thead><tr><th data-item="1" data-grp="tb">月</th>'+GG.map(g=>'<th data-item="1" data-grp="tb">'+g+'</th>').join('')+'</tr></thead><tbody>';
for(let i=0;i<=iL;i++){const m=D.months[i];h+='<tr><td class="m" data-item="1" data-grp="tb">'+J(m)+'</td>'+GG.map(g=>'<td data-k="lvl|'+g+'|'+m+'" data-v="'+Math.round(D.lvl[g][i])+'">'+Math.round(D.lvl[g][i]).toLocaleString('ja-JP')+'</td>').join('')+'</tr>'}
document.getElementById('tb').innerHTML=h+'</tbody>';
"""
out = os.path.join(ROOT, "dashboard"); os.makedirs(out, exist_ok=True)
for fn, title, body, js in [("d1.html", "D1 水準グラフ型", D1_BODY, D1_JS), ("d2.html", "D2 表型", D2_BODY, D2_JS),
                            ("d3.html", "D3 問いから作る型", D3_BODY, D3_JS), ("d4.html", "D4 D3＋水準", D4_BODY, D4_JS), ("table.html", "元データの表", TB_BODY, TB_JS)]:
    open(os.path.join(out, fn), "w").write(page(title, body, js))
print("ok", [os.path.getsize(os.path.join(out, f)) for f in os.listdir(out)])
