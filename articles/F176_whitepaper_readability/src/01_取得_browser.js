// 01 取得（ブラウザ版）：白書の HTML 版を目次から3階層までたどり、本文のテキストを集める。
// 白書ごとに、そのサイトのページ（下の START）を開いた状態で開発者ツールのコンソールに貼って実行し、
// 終わったら window.crawl.pages を JSON で保存して data/raw/pages_<wp>.json に置く（GitHub には置かない）。
//   keizai：https://www5.cao.go.jp/keizai3/keizaiwp/index.html （経済白書 1947〜2000、経済財政白書 2001〜2025）
//   joho  ：https://www.soumu.go.jp/johotsusintokei/whitepaper/ （通信白書 1973〜2000、情報通信白書 2001〜2025）
//   kokudo：https://www.mlit.go.jp/statistics/file000004.html （国土交通白書 2004〜2025。2008年版は HTML がない）
// 1998年版の通信白書は EUC-JP なので、文字化けの少ない方の文字コードを自動で選ぶ。
const WP = 'keizai'; // ← 'keizai' / 'joho' / 'kokudo'
window.dec = async u => {
  const r = await fetch(u); const b = await r.arrayBuffer();
  let t = new TextDecoder('utf-8').decode(b);
  if ((t.match(/�/g) || []).length > 5) {
    const bad = x => (x.match(/[｡-ﾟ-�]/g) || []).length;
    const s = new TextDecoder('shift_jis').decode(b), e = new TextDecoder('euc-jp').decode(b);
    t = bad(e) < bad(s) ? e : s;
  }
  return [r.status, t];
};
const code = Y => Y >= 2019 ? 'r' + String(Y - 2018).padStart(2, '0') : 'h' + String(Y - 1988).padStart(2, '0');
async function years() {
  if (WP === 'keizai') {
    const [, ti] = await dec('https://www5.cao.go.jp/keizai3/keizaiwp/index.html');
    const d = new DOMParser().parseFromString(ti, 'text/html');
    const yr = u => { const y = +u.match(/wp-je(\d\d)/)[1]; return y <= 30 ? 2000 + y : 1900 + y; };
    let tops = [...new Set([...d.querySelectorAll('a')].map(a => new URL(a.getAttribute('href') || '', 'https://www5.cao.go.jp/keizai3/keizaiwp/').href).filter(u => /wp-je\d\d/.test(u)))];
    tops = ['https://www5.cao.go.jp/j-j/wp/wp-je25/index.html', 'https://www5.cao.go.jp/j-j/wp/wp-je24/index.html', ...tops];
    return tops.map(u => [yr(u), u]);
  }
  if (WP === 'joho') {
    const ys = [];
    for (let i = 48; i <= 63; i++) ys.push([1925 + i, 's' + i]);
    for (let Y = 1989; Y <= 2025; Y++) ys.push([Y, code(Y)]);
    return ys.map(([Y, y]) => [Y, `https://www.soumu.go.jp/johotsusintokei/whitepaper/ja/${y}/index.html`]);
  }
  const ys = []; for (let Y = 2004; Y <= 2025; Y++) if (Y !== 2008) ys.push(Y);
  return ys.map(Y => [Y, `https://www.mlit.go.jp/hakusyo/mlit/${code(Y - 1)}/hakusho/${code(Y)}/index.html`]);
}
const FIG = { keizai: /図表|^第?\s*[\d０-９\-－]+\s*[図表]|付図|付表|ウェブアクセシビリティ|電子書籍|PDF版/, joho: /^\s*(図表|図|表)\s*[\d０-９]/, kokudo: /^\s*(図表|図|表)\s*[\d０-９]/ };
const FIGURL = { keizai: /zuhyo|fig|pdf|syoseki|webaccess/i, joho: /zuhyou|zu\d|pdf/i, kokudo: /\/data\/|pdf|target|_e\//i };
async function one(Y, top) {
  const dir = top.slice(0, top.lastIndexOf('/') + 1); const seen = new Set([top]); const q = [[top, 0]]; let n = 0, k = 0; const buf = [];
  while (q.length && n < 500) {
    const [u, dep] = q.shift(); n++; let s, t;
    try { [s, t] = await dec(u); } catch (e) { continue; }
    await new Promise(r => setTimeout(r, 80)); if (s !== 200) continue;
    const d = new DOMParser().parseFromString(t, 'text/html');
    const h1 = (d.querySelector('h1,h2,h3') || { textContent: '' }).textContent;
    const isFig = FIG[WP].test(h1) || FIGURL[WP].test(u);
    if (dep < (WP === 'kokudo' ? 4 : 3) && !isFig) for (const a of d.querySelectorAll('a[href],frame[src],iframe[src]')) {
      const at = a.textContent.trim(); if (/^(図表|図|表)\s*[\d０-９]|CSV|PDF|ＰＤＦ|Excel/.test(at)) continue;
      let h; try { h = new URL(a.getAttribute('href') || a.getAttribute('src'), u).href.split('#')[0].split('?')[0]; } catch (e) { continue; }
      if (h.startsWith(dir) && /\.html?$/.test(h) && !seen.has(h)) { seen.add(h); q.push([h, dep + 1]); }
    }
    if (isFig) continue;
    d.querySelectorAll('script,style,noscript').forEach(e => e.remove());
    const main = d.querySelector('#mainContents,#contentsWrapper,#contents,#main,main,.main') || d.body; if (!main) continue;
    const body = (main.innerText || main.textContent).replace(/[ \t\r]+/g, ' ').replace(/\n\s*\n+/g, '\n').trim();
    if (body.length >= 200) buf.push({ wp: WP, year: Y, ord: k++, dep, url: u, title: (d.title || '').trim(), text: body });
  }
  window.crawl.pages.push(...buf); window.crawl.log.push(Y + ' ' + n + ' ' + k);
}
window.crawl = { pages: [], log: [] };
(async () => {
  const ys = await years(); let i = 0;
  const worker = async () => { while (i < ys.length) { const [Y, u] = ys[i++]; await one(Y, u); } };
  await Promise.all([worker(), worker(), worker()]); window.crawl.done = true;
})();
