// 毎月勤労統計（全国調査）の各月の速報・確報ページから、第1表（給与）・第2表（労働時間）・第3表（雇用）を集める。
// 厚生労働省のサイト（https://www.mhlw.go.jp/toukei/list/30-1a.html）を開いたブラウザのコンソールで実行する。
// Excel は SheetJS（xlsx@0.18.5）で CSV にし、5人以上の「調査産業計」の行と見出しだけを残して
// data/raw/f152_maikin_releases.json として保存する。2013年1月〜2026年8月、164か月×2段階。
// GDP の速報は F50 で集めた data/raw/f50_qe_releases.json・f50_qe_extra.json をそのまま使う。
await new Promise((res, rej) => { const s = document.createElement('script'); s.src = 'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js'; s.onload = res; s.onerror = rej; document.head.appendChild(s); });
function cands(y, m, k) {  // ページの置き場所（年のフォルダと番号）の候補
  const mm = String(m).padStart(2, '0'), c = [];
  if (y <= 2018) { const h = y - 1988; c.push([String(h), h + mm + k]); }
  else if (y == 2019) { if (m <= 4) c.push(['31', '31' + mm + k]); else c.push(['r01', '01' + mm + k]); c.push(['31', '31' + mm + k], ['r01', '01' + mm + k]); }
  else if (y == 2020) c.push(['r02', '02' + mm + k]);
  else { const rr = 'r' + String(y - 2018).padStart(2, '0'); c.push([rr, String(y - 2000) + mm + k], [rr, String(y - 2018).padStart(2, '0') + mm + k]); }
  return c;
}
const W = {};
for (let y = 2013; y <= 2026; y++) for (let m = 1; m <= 12; m++) {
  if (y == 2026 && m > 8) break;
  for (const k of ['p', 'r']) {
    const key = y + '-' + String(m).padStart(2, '0') + k;
    for (const [dir, id] of cands(y, m, k)) {
      const base = '/toukei/itiran/roudou/monthly/' + dir + '/' + id + '/';
      const r = await fetch(base + id + '.html'); if (!r.ok) continue;
      const s = new TextDecoder('shift_jis').decode(await r.arrayBuffer());
      const d = new DOMParser().parseFromString(s, 'text/html');
      const links = [...d.querySelectorAll('a')].map(a => a.getAttribute('href') || '').filter(h => /c0[123][pr]?\.xlsx?$/.test(h));
      const tabs = {};
      for (const l of links) {
        const t = l.match(/c0([123])/)[1]; if (tabs[t]) continue;
        const rr = await fetch(new URL(l, location.origin + base).href); if (!rr.ok) continue;
        const wb = XLSX.read(new Uint8Array(await rr.arrayBuffer()), { type: 'array' });
        const csv = wb.SheetNames.map(n => '##' + n + '\n' + XLSX.utils.sheet_to_csv(wb.Sheets[n])).join('\n');
        tabs[t] = csv.split('\n').filter(l => { const z = l.replace(/[\s　]/g, ''); return z.startsWith('##') || /事業所規模/.test(z) || /^(就業形態計|一般労働者|パートタイム労働者)/.test(z) || /^調査産業計/.test(z); }).join('\n');
      }
      const pub = (s.match(/(令和|平成)\s*(\d+|元)年\s*(\d+)月\s*(\d+)日/) || [''])[0];
      W[key] = { dir, id, pub, tabs }; break;
    }
  }
}
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([JSON.stringify(W)], { type: 'application/json' }));
a.download = 'f152_maikin_releases.json'; a.click();
