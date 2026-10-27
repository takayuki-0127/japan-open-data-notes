// 01 取得（ブラウザ版）：https://www5.cao.go.jp/keizai3/whitepaper.html を開いた状態で、開発者ツールのコンソールに貼って実行する。
// 01_取得.py と同じ処理。終わったら crawl2.pages を JSON で保存して data/raw/pages.json に置く。
window.dec = async u => { const r = await fetch(u); const buf = await r.arrayBuffer(); let t = new TextDecoder('utf-8').decode(buf); if ((t.match(/�/g) || []).length > 5) t = new TextDecoder('shift_jis').decode(buf); return [r.status, t]; };
(async () => {
  const [, ti] = await dec('https://www5.cao.go.jp/keizai3/keizaiwp/index.html');
  const di = new DOMParser().parseFromString(ti, 'text/html');
  let tops = [...di.querySelectorAll('a')].map(a => new URL(a.getAttribute('href') || '', 'https://www5.cao.go.jp/keizai3/keizaiwp/').href).filter(u => /wp-je\d\d/.test(u));
  const yr = u => { const y = +u.match(/wp-je(\d\d)/)[1]; return y <= 30 ? 2000 + y : 1900 + y; };
  tops = ['https://www5.cao.go.jp/j-j/wp/wp-je25/index.html', 'https://www5.cao.go.jp/j-j/wp/wp-je24/index.html', ...tops.filter(u => yr(u) >= 1985)];
  window.crawl2 = { pages: [], log: [] };
  const W = t => new Promise(r => setTimeout(r, t));
  for (const top of tops) {
    const Y = yr(top); if (crawl2.pages.some(p => p.year == Y)) continue;
    const dir = top.slice(0, top.lastIndexOf('/') + 1); const seen = new Set([top]); const q = [[top, 0]]; let n = 0;
    while (q.length && n < 500) {
      const [u, dep] = q.shift(); n++; let s, t;
      try { [s, t] = await dec(u); } catch (e) { continue; }
      await W(150); if (s !== 200) continue;
      const d = new DOMParser().parseFromString(t, 'text/html');
      const h1 = (d.querySelector('h1,h2') || { textContent: '' }).textContent;
      const isFig = /図表|^第?\s*[\d０-９\-－]+\s*[図表]|付図|付表|ウェブアクセシビリティ|電子書籍|PDF版/.test(h1) || /zuhyo|fig|pdf|syoseki|webaccess/i.test(u);
      if (dep < 3 && !isFig) for (const a of d.querySelectorAll('a[href]')) {
        const at = a.textContent.trim(); if (/図|表|CSV|PDF|ＰＤＦ/.test(at) && !/第\d+章|節/.test(at)) continue;
        let h; try { h = new URL(a.getAttribute('href'), u).href.split('#')[0].split('?')[0]; } catch (e) { continue; }
        if (h.startsWith(dir) && /\.html?$/.test(h) && !seen.has(h)) { seen.add(h); q.push([h, dep + 1]); }
      }
      if (isFig) continue;
      d.querySelectorAll('script,style,noscript').forEach(e => e.remove());
      const main = d.querySelector('#mainContents,#main,main,#contents,.main') || d.body;
      const hs = [...main.querySelectorAll('h1,h2,h3,h4,h5')].map(e => e.tagName + ':' + e.textContent.trim().replace(/\s+/g, ' ')).slice(0, 120);
      const body = (main.innerText || main.textContent).replace(/[ \t\r]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim();
      if (body.length >= 200) crawl2.pages.push({ year: Y, url: u, title: (d.title || '').trim(), h: hs, text: body });
    }
    crawl2.log.push(Y + ' ' + n);
  }
})();
