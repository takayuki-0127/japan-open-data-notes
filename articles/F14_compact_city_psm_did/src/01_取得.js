// F14 01 取得（ブラウザのコンソールで実行したコード）
// コンテナからは国交省・国土数値情報のサイトに届かないため、Chrome のページ内で取得した。
// (1) 立地適正化計画の作成状況（国交省 PDF）：文字ごとの色と位置を pdf.js で取り出す
//     赤字・青字＝作成・公表済み、黒字＝取組中。→ data/raw/plans_pdf_chars.json
// (2) 国土数値情報 人口集中地区（A16）2010・2015・2020 の属性表（DBF）→ data/raw/did_ksj_A16.json
const SRC = {
  H2907: ['https://www.mlit.go.jp/common/001203972.pdf', 1],                // 2017-07-31 時点
  H3005: ['https://www.mlit.go.jp/common/001239916.pdf', 1],                // 2018-05-01 時点
  H3012: ['https://www.mlit.go.jp/common/001280657.pdf', 4],                // 2018-12-31 時点（資料2の4ページ）
  R0204: ['https://www.mlit.go.jp/toshi/city_plan/content/001353376.pdf', 1], // 2020-04-01 時点
  R0207: ['https://www.mlit.go.jp/toshi/city_plan/content/001378865.pdf', 1], // 2020-07-31 時点
};
async function loadScript(u){await new Promise((res,rej)=>{const s=document.createElement('script');s.src=u;s.onload=res;s.onerror=rej;document.head.appendChild(s)});}
async function charpos(u, pageNo){
  const d = await pdfjsLib.getDocument({data: await (await fetch(u)).arrayBuffer()}).promise;
  const p = await d.getPage(pageNo); const ops = await p.getOperatorList();
  const names = Object.fromEntries(Object.entries(pdfjsLib.OPS).map(([k,v])=>[v,k]));
  let col='0,0,0', lm=[1,0,0,1,0,0], x=0, fs=1; const out=[];
  for (let i=0;i<ops.fnArray.length;i++){ const n=names[ops.fnArray[i]], a=ops.argsArray[i];
    if (n==='setFillRGBColor') col=a.join(',');
    else if (n==='setFont') fs=a[1];
    else if (n==='setTextMatrix'){ lm=a.slice(); x=0; }
    else if (n==='moveText'){ lm=[lm[0],lm[1],lm[2],lm[3],lm[4]+a[0]*lm[0]+a[1]*lm[2],lm[5]+a[0]*lm[1]+a[1]*lm[3]]; x=0; }
    else if (n==='showText'||n==='showSpacedText'){ for (const g of a[0]){ if (typeof g==='number'){x-=g/1000*fs;continue} if(!g)continue;
        out.push([g.unicode,col,+(lm[4]+x*lm[0]).toFixed(1),+lm[5].toFixed(1),+(fs*lm[0]).toFixed(1)]); x+=(g.width||1000)/1000*fs; } } }
  return out;
}
async function getPlans(){ // www.mlit.go.jp のページで実行
  await loadScript('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js');
  pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  const all={}; for (const [k,[u,p]] of Object.entries(SRC)) all[k]=await charpos(u,p); return all;
}
function parseDbf(buf, enc){
  const dv=new DataView(buf); const n=dv.getUint32(4,true), hl=dv.getUint16(8,true), rl=dv.getUint16(10,true);
  const td=new TextDecoder(enc||'utf-8'); const f=[];
  for (let o=32; dv.getUint8(o)!==0x0D; o+=32) f.push({name:td.decode(new Uint8Array(buf,o,11)).replace(/\0.*$/,''), len:dv.getUint8(o+16)});
  const rows=[]; for (let i=0;i<n;i++){ let o=hl+i*rl+1; const r=[]; for (const x of f){ r.push(td.decode(new Uint8Array(buf,o,x.len)).trim()); o+=x.len; } rows.push(r); }
  return {f:f.map(x=>x.name), rows};
}
async function getDID(){ // nlftp.mlit.go.jp のページで実行
  await loadScript('https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js');
  const out={};
  for (const y of ['20','15','10']){
    const z=await JSZip.loadAsync(await (await fetch(`/ksj/gml/data/A16/A16-${y}/A16-${y}_GML.zip`)).arrayBuffer());
    const names=Object.keys(z.files); const dn=names.find(n=>/\.dbf$/i.test(n)); const cn=names.find(n=>/\.cpg$/i.test(n));
    const cpg=cn? await z.file(cn).async('string') : '';
    out[y]=parseDbf(await z.file(dn).async('arraybuffer'), /utf/i.test(cpg)?'utf-8':'shift_jis');
  }
  return out;
}
