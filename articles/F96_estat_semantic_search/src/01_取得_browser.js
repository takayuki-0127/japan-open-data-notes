// F96 01 取得：e-Stat「統計データを探す → ファイル」の一覧（データセット表示）を、公開（更新）年月ごとにたどって表題を集める。
// 使い方：ブラウザで https://www.e-stat.go.jp/ を開き、開発者ツールのコンソールに貼り付けて実行する。
// 1ページ50件。サーバーに負担をかけないよう、1ページごとに1秒あける（実測で1ページ約2.6秒、2026年1〜10月分で約40分）。
// 終わったら estat_files_2026.json がダウンロードされる → data/raw/ に置く。
// 背景のタブではタイマーが間引かれるので、待ち時間は Web Worker の setTimeout で作る。
const sleep = ms => new Promise(r => { const w = new Worker(URL.createObjectURL(new Blob(['onmessage=e=>setTimeout(()=>postMessage(1),e.data)']))); w.onmessage = () => { w.terminate(); r(); }; w.postMessage(ms); });
function parse(d, month) {
  const out = [];
  for (const a of d.querySelectorAll('article.stat-resource_list-item')) {
    const li = [...a.querySelectorAll('li.stat-resource_list-detail-item')].map(e => e.textContent.trim().replace(/\s+/g, ' '));
    const txt = a.textContent.replace(/\s+/g, ' ');
    const survey = (txt.match(/調査年月\s*(.*?)\s*公開（更新）日/) || [])[1] || '';
    const open = (txt.match(/公開（更新）日\s*(\d{4}-\d{2}-\d{2})/) || [])[1] || '';
    const ta = a.querySelector('a.js-data');  // 表題のリンク（DB へのリンクにも stat_infid が入るので、クラスで選ぶ）
    const title = ta ? [...ta.querySelectorAll('span.stat-separator')].map(s => s.textContent.trim().replace(/\s+/g, ' ')).filter(Boolean).join(' ') : '';
    const id = ta ? ((ta.getAttribute('href').match(/stat_infid=(\d+)/) || [])[1] || '') : '';
    const kinds = [...a.querySelectorAll('.stat-dl_text')].map(s => s.textContent.trim()).join('/');
    out.push({ id, toukei: li[0] || '', path: li[1] || '', survey, open, title, kinds, month });
  }
  return out;
}
(async () => {
  const rows = [], log = [];
  for (let m = 202601; m <= 202610; m++) {
    let page = 1, np = 9999;
    while (page <= np) {
      let ok = false;
      for (let t = 0; t < 3 && !ok; t++) {
        try {
          const h = await fetch(`/stat-search/files?layout=dataset&page=${page}&open_date=${m}`).then(r => { if (!r.ok) throw r.status; return r.text(); });
          const d = new DOMParser().parseFromString(h, 'text/html');
          const pm = d.body.textContent.match(/\d+\/(\d+)ページ/); if (pm) np = +pm[1];
          rows.push(...parse(d, m)); ok = true;
        } catch (e) { log.push([m, page, String(e)]); await sleep(10000); }
      }
      page++; await sleep(1000);
    }
    log.push([m, 'done', np, rows.length]);
  }
  const blob = new Blob([JSON.stringify({ fetched: new Date().toISOString(), log, rows })], { type: 'application/json' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'estat_files_2026.json'; a.click();
})();
