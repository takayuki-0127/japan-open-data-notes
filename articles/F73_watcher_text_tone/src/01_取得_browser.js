// 01_取得（ブラウザで実行）：内閣府「景気ウォッチャー調査」の各月のページから、
// 景気判断理由集（現状 watcher4.csv・先行き watcher5.csv）と、DI の長期系列（Excel）を集めて
// f73_watcher.json.gz として保存する。
// 使い方：https://www5.cao.go.jp/keizai3/watcher_index.html を開き、開発者ツールのコンソールに貼り付けて実行する。
// 依存：SheetJS（xlsx@0.18.5、jsDelivr から読み込む）。アクセスの間隔は 0.12〜0.15 秒あけている。
(async () => {
  if (!window.XLSX) await new Promise((ok, ng) => { const s = document.createElement('script'); s.src = 'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js'; s.onload = ok; s.onerror = ng; document.head.appendChild(s); });
  const sleep = t => new Promise(r => setTimeout(r, t));
  const links = async u => { const t = await (await fetch(u)).text(); const d = new DOMParser().parseFromString(t, 'text/html'); return [...d.querySelectorAll('a')].map(a => new URL(a.getAttribute('href') || '', u).href); };
  const A = (await links('https://www5.cao.go.jp/keizai3/watcher_index.html')).concat(await links('https://www5.cao.go.jp/keizai3/kako_watcher.html'));
  const menus = [...new Set(A.filter(h => /watcher\/(menu|index)\.html?$|\d{4}\/\d{4}watcher/.test(h)))];
  const csv = [];
  for (const u of menus) {
    const hs = await links(u);
    const c4 = hs.find(h => /watcher4\.csv$/i.test(h)), c5 = hs.find(h => /watcher5\.csv$/i.test(h));
    csv.push([u, c4 || '', c5 || '', '']); await sleep(150);
  }
  // ほとんどの月は Shift_JIS だが、UTF-8 の月（2025年10月・2026年4月の先行きなど）もあるので、UTF-8 で読めればそちらを使う
  const dec = b => { try { return new TextDecoder('utf-8', { fatal: true }).decode(b); } catch (e) { return new TextDecoder('shift_jis').decode(b); } };
  const rows = [];
  const parse = (t, ym, kind) => {
    const wb = XLSX.read(t, { type: 'string', raw: true });
    const a = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, defval: '' });
    let reg = '', fld = '';
    for (const r of a) {
      const c0 = String(r[0] || '').trim(), c1 = String(r[1] || '').trim();
      const m = (c1 + c0).match(/^[　\s]*[０-９0-9]+[．.]\s*([^（(]+)/);
      if (m && !r[2]) { reg = m[1].trim(); continue; }
      if (c0 && !/分野/.test(c0)) fld = c0.replace(/\s+/g, '');
      const mk = String(r[2] || '').trim();
      if (!/^[◎○□▲×]$/.test(mk)) continue;
      rows.push([ym, kind, reg, fld, mk, String(r[3] || '').trim(), String(r[4] || '').trim(), String(r[5] || '').trim()]);
    }
  };
  for (const [u, c4, c5] of csv.filter(r => r[1])) {
    const mm = u.match(/keizai3\/(\d{4})\/(\d{2})(\d{2})watcher/); let y = +mm[1], mo = +mm[2] - 1; if (mo === 0) { mo = 12; y -= 1; }
    const ym = y + '-' + String(mo).padStart(2, '0');   // 公表月の前月が調査月
    for (const [cu, k] of [[c4, 'gen'], [c5, 'saki']]) {
      parse(dec(await (await fetch(cu)).arrayBuffer()), ym, k); await sleep(120);
    }
  }
  // DI：原数値（watcher2-1 現状・watcher2-4 先行き の全国合計）と季節調整値（watcher5 の分野別）
  const ser = d => { const t = new Date(Math.round((d - 25569) * 864e5)); return t.getUTCFullYear() + '-' + String(t.getUTCMonth() + 1).padStart(2, '0'); };
  const blk = wb => { const a = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1 }); const o = []; let st = false; for (const r of a) { if (typeof r[0] == 'number' && r[0] > 30000) { st = true; o.push([ser(r[0]), r[1], r[2], r[3], r[4], r[5], r[6], r[13]]); } else if (st) break; } return o; };
  const X = async u => XLSX.read(await (await fetch(u)).arrayBuffer());
  const w21 = await X('https://www5.cao.go.jp/keizai3/watcher/watcher2-1.xls'), w24 = await X('https://www5.cao.go.jp/keizai3/watcher/watcher2-4.xls'), w5 = await X('https://www5.cao.go.jp/keizai3/watcher/watcher5.xls');
  const sa = n => { const a = XLSX.utils.sheet_to_json(w5.Sheets[n], { header: 1 }); let y = null; const o = []; for (const r of a) { if (r[1] && /年/.test(r[1])) y = parseInt(r[1]); if (y && typeof r[2] == 'number' && typeof r[3] == 'number') o.push([y + '-' + String(r[2]).padStart(2, '0'), r[3], r[4], r[9], r[12]]); } return o; };
  const di = { raw_gen: blk(w21), raw_saki: blk(w24), sa_gen: sa(w5.SheetNames[0]), sa_saki: sa(w5.SheetNames[1]) };
  const blob = await new Response(new Blob([JSON.stringify({ rows, di, csv })]).stream().pipeThrough(new CompressionStream('gzip'))).blob();
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'f73_watcher.json.gz'; document.body.appendChild(a); a.click();
})();
