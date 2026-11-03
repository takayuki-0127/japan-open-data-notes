// 日本郵便のページ（https://www.post.japanpost.jp/newsrelease/）の上で実行
const m = await import('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.min.mjs');
m.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.worker.min.mjs';
async function pdfText(u){
  const b = await fetch(u).then(r=>r.arrayBuffer());
  const doc = await m.getDocument({data:b}).promise; let s='';
  for(let p=1;p<=doc.numPages;p++){const tc=await (await doc.getPage(p)).getTextContent();
    s+='\n#P'+p+'\n'+tc.items.map(x=>x.str+(x.hasEOL?'\n':'')).join('|');}
  return s;
}
// 行の読み取り: 区切りと空白を除いたあと「ラベル 当年度物数 増減率 前年度物数 増減率」を正規表現で読む
const labs=['総計','郵便物','内国','普通','第一種','第二種','第三種','第四種','年賀','選挙','特殊','国際(差立)','荷物','ゆうパック','ゆうパケット','ゆうメール'];
function parse(s){
  const t0=s.replace(/[|\s]/g,''); let t=t0.slice(t0.search(/千通/)); const rows={}; let pos=0;
  for(const L of labs){
    const re=new RegExp(L.replace(/[()]/g,'\\$&')+'(\\d{1,3}(?:,\\d{3})*)(▲|△|＋|\\+|-|－)?(\\d+\\.\\d)(\\d{1,3}(?:,\\d{3})*)(▲|△|＋|\\+|-|－)?(\\d+\\.\\d)');
    const mm=t.slice(pos).match(re);
    if(mm){const sg=x=>x&&/[▲△\-－]/.test(x)?-1:1;
      rows[L]=[+mm[1].replace(/,/g,''),sg(mm[2])*+mm[3],+mm[4].replace(/,/g,''),sg(mm[5])*+mm[6]]; pos+=mm.index+mm[0].length;}
  }
  return rows;
}
