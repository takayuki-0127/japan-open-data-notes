// 01_取得（ブラウザ版）：日本銀行の「金融市場調節方針に関する公表文」をすべて集める。
// 実行場所：https://www.boj.or.jp/mopo/mpmdeci/state_all/index.htm を開いた状態で、開発者ツールのコンソールに貼る。
// PDF は pdf.js（cdnjs）で文字を取り出す。1文書ごとに 0.25 秒あける。
// 結果は f53_boj_statements.json としてダウンロードされる（[{date,title,href,text}, ...]）。
(async () => {
  const pdfjs = await import('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.min.mjs');
  pdfjs.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/pdf.worker.min.mjs';
  const yrs = [...new Set([...document.querySelectorAll('a')].map(a => a.getAttribute('href'))
    .filter(h => /state_\d{4}\/index/.test(h)))];
  const by = {};
  for (const y of yrs) {
    const d = new DOMParser().parseFromString(await fetch(y).then(r => r.text()), 'text/html');
    for (const tr of d.querySelectorAll('tr')) {
      const a = tr.querySelector('a'); if (!a) continue;
      const t = (tr.innerText || tr.textContent).replace(/\s+/g, ' ').trim();
      const m = t.match(/(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日/); if (!m) continue;
      if (/（参考）|^参考/.test(t.replace(/^.*?日\s*/, ''))) continue;   // 参考資料は除く
      const key = `${m[1]}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`;
      (by[key] = by[key] || []).push({ t, h: a.getAttribute('href') });
    }
  }
  const docs = [];
  for (const date of Object.keys(by).sort()) {
    for (const r of by[date]) {
      let text = '';
      if (/\.pdf$/.test(r.h)) {
        const buf = await fetch(r.h).then(x => x.arrayBuffer());
        const doc = await pdfjs.getDocument({ data: buf,
          cMapUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/cmaps/', cMapPacked: true }).promise;
        for (let i = 1; i <= doc.numPages; i++) {
          const c = await (await doc.getPage(i)).getTextContent();
          text += c.items.map(x => x.str + (x.hasEOL ? '\n' : '')).join('');
        }
      } else {
        const d = new DOMParser().parseFromString(await fetch(r.h).then(x => x.text()), 'text/html');
        const main = d.querySelector('#contents, main, .main, #main') || d.body;
        text = main.innerText || main.textContent;
      }
      docs.push({ date, title: r.t.replace(/^.*?日\s*/, '').replace(/\[.*$/, '').trim(), href: r.h, text });
      await new Promise(z => setTimeout(z, 250));
    }
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(docs)], { type: 'application/json' }));
  a.download = 'f53_boj_statements.json'; document.body.appendChild(a); a.click();
  console.log('documents:', docs.length);
})();
