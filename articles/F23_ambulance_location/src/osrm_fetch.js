// ブラウザのコンソールで実行：data/demand.csv と candidates.csv を読み、OSRM の table API で
// 需要点×候補地の道路距離（m）と所要時間（秒）を 50×50 ずつ取って JSON をダウンロードする。
(async () => {
  const base = 'https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/F23_ambulance_location/data/';
  const rd = async f => (await (await fetch(base + f)).text()).trim().split('\n');
  const pick = (rows) => { const h = rows[0].split(','); const la = h.indexOf('lat'), lo = h.indexOf('lon');
    return rows.slice(1).map(l => { const x = l.split(','); return [+x[lo], +x[la]]; }); };
  const D = pick(await rd('demand.csv')), C = pick(await rd('candidates.csv'));
  const N = D.length, M = C.length, W = t => new Promise(r => setTimeout(r, t));
  const DIST = Array.from({length: N}, () => new Array(M)), DUR = Array.from({length: N}, () => new Array(M));
  const SNAPD = new Array(N), SNAPC = new Array(M);
  for (let i = 0; i < N; i += 50) for (let j = 0; j < M; j += 50) {
    const s = D.slice(i, i + 50), d = C.slice(j, j + 50);
    const pts = s.concat(d).map(p => p[0] + ',' + p[1]).join(';');
    const url = 'https://router.project-osrm.org/table/v1/driving/' + pts + '?sources=' + s.map((_, k) => k).join(';') +
      '&destinations=' + d.map((_, k) => k + s.length).join(';') + '&annotations=distance,duration';
    for (let a = 0; a < 5; a++) {
      const r = await fetch(url); if (r.status !== 200) { await W(4000 * (a + 1)); continue; }
      const js = await r.json();
      for (let x = 0; x < s.length; x++) for (let y = 0; y < d.length; y++) { DIST[i + x][j + y] = js.distances[x][y]; DUR[i + x][j + y] = js.durations[x][y]; }
      js.sources.forEach((q, k) => SNAPD[i + k] = q.distance); js.destinations.forEach((q, k) => SNAPC[j + k] = q.distance);
      break;
    }
    await W(300);
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify({DIST, DUR, SNAPD, SNAPC})], {type: 'application/json'}));
  a.download = 'f23_osrm_matrix.json'; document.body.appendChild(a); a.click();
})();
