// A193 抽出：e-Stat の第2-2表（statInfId=000040067943）をブラウザ上で SheetJS で読み、市区町村ごとの指標を集計する
// 使い方：e-Stat のページで SheetJS（xlsx 0.18.5）を読み込んだ状態で実行する
const L = ['AB','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R'];   // 産業大分類（公務を除く）
const buf = await fetch('/stat-search/file-download?statInfId=000040067943&fileKind=4').then(r => r.arrayBuffer());
const wb = XLSX.read(buf, {type: 'array'});
const a = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], {header: 1});
const M = {};  // code -> {nm, d: {産業: [事業所数, 事業従事者数, 純付加価値額(百万円) or null(秘匿)]}}
for (const r of a) {
  if (typeof r[1] !== 'string' || !/^\d{5}_/.test(r[1]) || r[3] !== '0_総数') continue;   // 経営組織=総数のみ
  const c = r[1].slice(0, 5), ind = String(r[2]).split('_')[0];
  (M[c] = M[c] || {nm: r[1].slice(6), d: {}}).d[ind] = [+r[4] || 0, +r[5] || 0, typeof r[6] === 'number' ? r[6] : null];
}
const N = M['00000'].d, natVA = L.reduce((s, k) => s + N[k][2], 0), ns = {};
L.forEach(k => ns[k] = N[k][2] / natVA);
// 市区町村：都道府県計・全国・特別区部計・境界未定地域・政令市の区を除く（政令市は市の計を使う）
const mun = Object.keys(M).filter(c => c.slice(2) !== '000' && c !== '13100' && c !== '13199' && !(/区$/.test(M[c].nm) && !c.startsWith('131')));
const rows = mun.map(c => {
  const d = M[c].d; let va = 0, w = 0, ws = 0, vpos = 0; const sh = {};
  for (const k of L) { if (!d[k]) continue; if (d[k][2] == null) { ws += d[k][1]; continue } va += d[k][2]; w += d[k][1]; }
  L.forEach(k => vpos += Math.max(d[k]?.[2] || 0, 0));
  L.forEach(k => sh[k] = Math.max(d[k]?.[2] || 0, 0) / vpos);            // 秘匿は0として構成比
  const top = L.slice().sort((x, y) => sh[y] - sh[x]);
  const lq = L.filter(k => sh[k] >= 0.05).map(k => [k, sh[k] / ns[k]]).sort((x, y) => y[1] - x[1]);   // 構成比5%以上で特化係数最大
  return {c, nm: M[c].nm, w: d.AR[1], v: Math.round(va / w * 100), sw: ws / d.AR[1] * 100, t: top[0], tp: sh[top[0]] * 100, q: lq[0]?.[0], lq: lq[0]?.[1], e: sh.E * 100};
});
// rows から data/ の各集計（産業別・規模別・製造業比率別の件数と中央値）を作った
