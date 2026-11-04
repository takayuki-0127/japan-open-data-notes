// F184 01_取得：e-Stat「航空輸送統計調査」統計表3（国内定期航空路線別、区間別、月別運航及び輸送実績）を
// ブラウザ（https://www.e-stat.go.jp/ を開いたタブ）の中で読み、路線×年・路線×月の表に直す。
// 使い方：e-Stat のページで開発者ツールのコンソールに貼る（SheetJS 0.18.5 を読み込む）。
// 2020年の表は検索で見つからなかったため含めていない（コロナ期として分析からも除く）。
const FILES = { // statInfId: 年
  '000001264853': 2006, '000001264833': 2007, '000002949463': 2008, '000007732115': 2009,
  '000023618821': 2010, '000023619161': 2011, '000023619144': 2012, '000025861723': 2013,
  '000031507074': 2014, '000031487797': 2015, '000031607434': 2016, '000031730081': 2017,
  '000031842369': 2018, '000031959671': 2019, '000032211479': 2021, '000040074178': 2022,
  '000040191398': 2023, '000040290549': 2024, '000040471584': 2025 };
await new Promise((res, rej) => { const s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js'; s.onload = res; s.onerror = rej; document.head.appendChild(s); });
const num = x => { const v = String(x).replace(/[,\s]/g, ''); return /^-?\d+(\.\d+)?$/.test(v) ? +v : null; };
const norm = s => s.replace(/線$/, '').replace(/^計/, '').replace(/東京[（(]羽田[）)]/g, '羽田').replace(/東京[（(]成田[）)]/g, '成田')
  .replace(/[（(]/g, '(').replace(/[）)]/g, ')').replace(/[－\-ー]/g, '―');
const ANN = [], MON = [];
for (const [id, yr] of Object.entries(FILES)) {
  const b = await (await fetch('/stat-search/file-download?statInfId=' + id + '&fileKind=0')).arrayBuffer();
  const wb = XLSX.read(b, { type: 'array' });
  const blocks = {}; // 路線 -> [{lab, ann, mon}]（2009年以前は航空会社ごとの表＋「計」の表）
  for (const sn of wb.SheetNames) {
    const rows = XLSX.utils.sheet_to_json(wb.Sheets[sn], { header: 1, blankrows: false, defval: '' });
    let cur = null, cnt = 0, done = false, gotA = false;
    for (const r of rows) {
      const c = r.map(x => String(x).replace(/\s+/g, ''));
      const hi = c.findIndex(x => /線$/.test(x) && !/^\d/.test(x));
      if (hi >= 0 && num(c[2]) == null) { // 路線の見出し行
        const route = norm(c[hi]); const lab = hi > 0 ? (c[0] || '?') : '?';
        cur = { lab, ann: null, mon: {} }; (blocks[route] = blocks[route] || []).push(cur);
        cnt = 0; done = false; gotA = false; continue; }
      if (!cur) continue;
      const mo = num(c[0]); // 1〜12月（暦年）。そのあとの1〜3月は翌年分なので使わない
      if (mo != null && mo >= 1 && mo <= 12 && !done) { cnt++; if (cnt === mo) { cur.mon[mo] = [num(c[2]), num(c[5]), num(c[6])]; if (mo === 12) done = true; } }
      if (c[0] === '計' && c[1] === '計' && !gotA) { cur.ann = [num(c[2]), num(c[5]), num(c[6])]; gotA = true; } // 暦年計（往復）
    }
  }
  for (const [route, bl] of Object.entries(blocks)) {
    const tot = bl.filter(x => x.lab === '計');
    const use = tot.length ? tot.slice(0, 1) : (yr >= 2010 ? bl.slice(0, 1) : bl); // 「計」があればそれ、なければ足し上げ
    const A = [0, 0, 0]; use.forEach(x => x.ann && x.ann.forEach((v, i) => A[i] += v || 0));
    ANN.push([yr, route, ...A]);
    for (let m = 1; m <= 12; m++) { const M = [0, 0, 0]; let any = false;
      use.forEach(x => { if (x.mon[m]) { any = true; x.mon[m].forEach((v, i) => M[i] += v || 0); } });
      if (any) MON.push([yr, m, route, ...M]); }
  }
}
// 同じ年・同じ路線を足し合わせ、8年以上あって平均旅客3万人以上の路線だけ残す
const agg = {}; ANN.forEach(([y, r, f, p, s]) => { const k = y + '|' + r; agg[k] = agg[k] || [y, r, 0, 0, 0]; agg[k][2] += f; agg[k][3] += p; agg[k][4] += s; });
const byR = {}; Object.values(agg).forEach(r => (byR[r[1]] = byR[r[1]] || []).push(r));
const keep = Object.keys(byR).filter(n => byR[n].length >= 8 && byR[n].reduce((a, r) => a + r[3], 0) / byR[n].length >= 30000);
// 年次：year,route,flights,pax,seats ／ 月次：year,month,route,flights,pax,seats
// → data/air_routes_annual.csv, data/air_routes_monthly.csv として保存した
