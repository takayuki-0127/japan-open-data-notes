// e-Stat のページ（https://www.e-stat.go.jp/）を開き、開発者ツールのコンソールで実行する。
// 令和2年賃金構造基本統計調査 一般労働者 都道府県別第1表（24ファイル、各2都道府県）から、産業計シートの男女・年齢階級別の値を抜き出す。
(async () => {
  if (!window.XLSX) await new Promise((res, rej) => { const s = document.createElement('script'); s.src = 'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js'; s.onload = res; s.onerror = rej; document.head.appendChild(s); });
  const out = [];
  for (let i = 501; i <= 524; i++) {
    const id = '000032069' + i;
    const b = await fetch('https://www.e-stat.go.jp/stat-search/file-download?statInfId=' + id + '&fileKind=0').then(r => r.arrayBuffer());
    const wb = XLSX.read(b);
    for (const n of wb.SheetNames) {
      if (!/産業計$/.test(n)) continue;
      const a = XLSX.utils.sheet_to_json(wb.Sheets[n], { header: 1 });
      const pref = a[4] && a[4][3]; let sex = null;
      for (const r of a.slice(11)) {
        const lab = (r[2] || '').toString().replace(/\s|　/g, ''); if (!lab) continue;
        if (lab === '男女計') sex = '計'; else if (lab === '男') sex = '男'; else if (lab === '女') sex = '女';
        out.push([id, pref, sex, lab, r[3], r[7], r[8], r[10]].join('\t'));   // 年齢, きまって支給する現金給与額, 所定内給与額, 労働者数（十人）
      }
    }
    await new Promise(r => setTimeout(r, 800));
  }
  const txt = 'statInfId\tpref\tsex\tage\tavg_age\tkimatte_kyuyo_k\tshoteinai_kyuyo_k\tworkers_10\n' + out.join('\n');
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([txt])); a.download = 'wage2020_pref.tsv'; a.click();
})();
