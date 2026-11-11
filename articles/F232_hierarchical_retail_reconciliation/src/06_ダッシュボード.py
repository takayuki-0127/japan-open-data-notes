# F232 06 静的な HTML ダッシュボード（外部のライブラリなし）を作り、画面の画像を撮る
import json, pathlib, asyncio
B = pathlib.Path(__file__).resolve().parents[1]
D = json.load(open(B / "dashboard/data.json"))
import pandas as pd
Y = pd.read_csv(B / "data/hier_wide.csv", index_col=0)
i0 = list(Y.index).index("2025-08")
D["ym_hist"] = list(Y.index[i0 - 35:i0 + 1]); D["hist"] = Y.values[i0 - 35:i0 + 1].T.round(0).tolist()
D["act"] = Y.values[i0 + 1:i0 + 13].T.round(0).tolist()
json.dump(D, open(B / "dashboard/data.json", "w"), ensure_ascii=False)
html = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>業態×商品の売上予測（そろえ方の比較）</title>
<style>
body{font-family:"Noto Sans CJK JP",sans-serif;margin:0;background:#f6f7f9;color:#222}
header{background:#1f3b57;color:#fff;padding:12px 20px}header h1{font-size:18px;margin:0}header p{margin:4px 0 0;font-size:12px;opacity:.85}
.wrap{display:grid;grid-template-columns:260px 1fr;gap:14px;padding:14px 20px}
.card{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);padding:12px}
select{width:100%;font-size:13px;padding:4px}label{font-size:12px;color:#555}
table{border-collapse:collapse;width:100%;font-size:12px}td,th{border-bottom:1px solid #eee;padding:4px 6px;text-align:right}th:first-child,td:first-child{text-align:left}
.kpi{display:flex;gap:10px;margin-bottom:10px}.kpi div{flex:1;background:#f0f4f8;border-radius:6px;padding:8px}.kpi b{font-size:18px;display:block}
.note{font-size:11px;color:#666;margin-top:8px}
.legend span{display:inline-block;margin-right:12px;font-size:12px}.legend i{display:inline-block;width:14px;height:3px;margin-right:4px;vertical-align:middle}
</style></head><body>
<header><h1>業態×商品の売上予測：全体・業態・商品をそろえる（架空の社内向け画面の例）</h1>
<p>データ：経済産業省「商業動態統計」（全国・月次・販売額、百万円）。2025年8月までの実績から12か月先までを予測。数値は公開データの加工で、実在の会社の数字ではありません。</p></header>
<div class="wrap"><div class="card">
<label>見る系列</label><select id="node"></select>
<p class="note">「そろえない」は系列ごとに別々に作った予測。「足し上げ」は商品の予測を足して業態・全体を作る方法。「MinT」は外れの大きさと相関で全部の予測を同時に直す方法。</p>
<div class="kpi"><div>12か月の合計（足し上げ）<b id="k1"></b></div></div>
<div class="kpi"><div>そろえない予測との差<b id="k2"></b></div></div>
<p class="note">右下の表：選んだ系列の「すぐ下の系列の予測の合計」と、その系列の予測の差。そろえた予測では 0 になる。</p>
</div><div class="card">
<div class="legend"><span><i style="background:#222"></i>実績（点線は予測した期間の実際）</span><span><i style="background:#888"></i>そろえない</span><span><i style="background:#1f77b4"></i>足し上げ（ボトムアップ）</span><span><i style="background:#d62728"></i>MinT</span></div>
<canvas id="cv" width="900" height="330"></canvas>
<table id="tb"></table></div></div>
<script>
const D=__DATA__;
const M={"ベース（そろえない）":"#888","ボトムアップ":"#1f77b4","MinT（縮小）":"#d62728"};
const sel=document.getElementById('node');
D.nodes.forEach((n,i)=>{const o=document.createElement('option');o.value=i;o.textContent='　'.repeat(D.level[i])+n;sel.appendChild(o);});
function kids(i){const n=D.nodes[i];return D.nodes.map((x,j)=>j).filter(j=>{
 if(D.level[i]==0)return D.level[j]==1;
 if(D.level[j]<=D.level[i])return false;const p=D.nodes[j];if(!p.startsWith(D.level[i]==1?n+'/':n.split('/')[0]+'/'))return false;
 if(D.level[i]==1){const mids=D.nodes.filter((x,k)=>D.level[k]==2&&x.startsWith(n+'/'));
   if(D.level[j]==2)return true;
   return !mids.some(mm=>__MID__[mm]&&__MID__[mm].includes(p.split('/')[1]))&&D.level[j]==3;}
 return D.level[j]==3&&(__MID__[n]||[]).includes(p.split('/')[1]);});}
function draw(){const i=+sel.value,cv=document.getElementById('cv'),c=cv.getContext('2d');c.clearRect(0,0,cv.width,cv.height);
 const h=D.hist[i],F={};for(const k in M)F[k]=D.fc[k][i];const A=D.act[i];const all=h.concat(A,...Object.values(F));
 const lo=Math.min(...all)*0.95,hi=Math.max(...all)*1.03,N=h.length+12,X=t=>50+t*(cv.width-70)/(N-1),Yy=v=>cv.height-30-(v-lo)/(hi-lo)*(cv.height-50);
 c.strokeStyle='#ddd';c.font='11px sans-serif';c.fillStyle='#666';for(let g=0;g<5;g++){const v=lo+(hi-lo)*g/4;c.beginPath();c.moveTo(50,Yy(v));c.lineTo(cv.width-20,Yy(v));c.stroke();c.fillText((v/1e4).toFixed(1)+'百億',2,Yy(v)+4);}
 [0,12,24,36].forEach(t=>{const lab=t<36?D.ym_hist[t]:D.ym_fc[0];c.fillText(lab,X(t)-18,cv.height-10);});
 const line=(arr,off,col,w)=>{c.strokeStyle=col;c.lineWidth=w;c.beginPath();arr.forEach((v,k)=>{k?c.lineTo(X(k+off),Yy(v)):c.moveTo(X(k+off),Yy(v));});c.stroke();};
 line(h,0,'#222',2);c.setLineDash([5,4]);line([h[h.length-1]].concat(A),h.length-1,'#222',1.5);c.setLineDash([]);for(const k in M)line([h[h.length-1]].concat(F[k]),h.length-1,M[k],2);
 const s=a=>a.reduce((x,y)=>x+y,0);document.getElementById('k1').textContent=(s(F['ボトムアップ'])/1e6).toFixed(2)+' 兆円';
 document.getElementById('k2').textContent=((s(F['ボトムアップ'])/s(F['ベース（そろえない）'])-1)*100).toFixed(2)+' %';
 const ks=kids(i);let t='<tr><th>予測の月</th><th>そろえない：自分</th><th>そろえない：下の合計</th><th>差</th><th>足し上げ：差</th></tr>';
 if(ks.length){for(let m=0;m<12;m+=3){const own=F['ベース（そろえない）'][m],sub=ks.reduce((a,j)=>a+D.fc['ベース（そろえない）'][j][m],0),bu=ks.reduce((a,j)=>a+D.fc['ボトムアップ'][j][m],0);
  t+=`<tr><td>${D.ym_fc[m]}</td><td>${Math.round(own).toLocaleString()}</td><td>${Math.round(sub).toLocaleString()}</td><td>${((sub/own-1)*100).toFixed(2)}%</td><td>${((bu/F['ボトムアップ'][m]-1)*100).toFixed(2)}%</td></tr>`;}}
 else t+='<tr><td colspan=5>いちばん細かい単位（商品）なので、下の系列はありません</td></tr>';
 document.getElementById('tb').innerHTML=t;}
sel.onchange=draw;draw();
</script></body></html>"""
MID = {"百貨店/衣料品": ["紳士服・洋品", "婦人・子供服・洋品", "その他の衣料品", "身の回り品"],
       "百貨店/その他": ["家具", "家庭用電気機械器具", "家庭用品", "その他の商品", "食堂・喫茶"],
       "スーパー/衣料品": ["紳士服・洋品", "婦人・子供服・洋品", "その他の衣料品", "身の回り品"],
       "スーパー/その他": ["家具", "家庭用電気機械器具", "家庭用品", "その他の商品", "食堂・喫茶"],
       "コンビニ/商品販売額": ["FF・日配食品", "加工食品", "非食品"]}
html = html.replace("__DATA__", json.dumps(D, ensure_ascii=False)).replace("__MID__", "MIDX")
html = html.replace("const D=", "const MIDX=" + json.dumps(MID, ensure_ascii=False) + ";const D=", 1)
(B / "dashboard/index.html").write_text(html, encoding="utf-8")

async def shot():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1240, "height": 640}, device_scale_factor=1.5)
        await pg.goto((B / "dashboard/index.html").as_uri()); await pg.select_option("#node", "1")
        await pg.wait_for_timeout(500); await pg.screenshot(path=str(B / "figures/f232_6_dashboard.png"), full_page=True); await b.close()
asyncio.run(shot()); print("ok")
