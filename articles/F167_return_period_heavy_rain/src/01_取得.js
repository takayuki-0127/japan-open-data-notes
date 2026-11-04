// 01 取得：気象庁「過去の気象データ検索」から、日降水量の最大値を取る。
// ブラウザで https://www.data.jma.go.jp/stats/etrn/index.php を開き、開発者ツールのコンソールで実行する。
// （この作業環境のコンテナからは気象庁のサイトにつながらないため、ブラウザから取った。2026年11月4日取得）
// 1ページずつ間をあけて取る。結果は CSV でダウンロードされるので、data/ に置く。
//
//   年ごとの値   annually_s.php  → data/jma_annual_raw.csv   （28地点、列4＝日降水量の最大）
//   月ごとの値   monthly_s1.php  → data/jma_monthly_raw.csv  （8地点×1901〜2025年、列4＝日降水量の最大）

const ANNUAL = [[14,47412],[23,47430],[33,47585],[32,47582],[34,47590],[34,47592],[54,47604],[56,47605],
  [44,47662],[45,47648],[50,47654],[51,47636],[62,47772],[67,47765],[73,47887],[74,47893],[82,47807],
  [84,47817],[87,47830],[88,47827],[91,47936],[61,47759],[63,47770],[57,47616],[55,47607],[35,47588],
  [31,47575],[12,47407]];
// 試したが表が取れなかった地点：[65,47755]、[48,47626]（地点番号の組み合わせが違ったため使わない）
const MONTHLY = [[44,47662,'東京'],[62,47772,'大阪'],[51,47636,'名古屋'],[82,47807,'福岡'],
  [14,47412,'札幌'],[74,47893,'高知'],[88,47827,'鹿児島'],[54,47604,'新潟']];
const BASE = 'https://www.data.jma.go.jp/stats/etrn/view/';
const sleep = ms => new Promise(r => setTimeout(r, ms));

function save(name, lines) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob(['﻿' + lines.join('\n')], {type: 'text/csv'}));
  a.download = name; document.body.appendChild(a); a.click();
}

async function annual() {
  const L = ['prec_no,block_no,station,year,annual_total_raw,daily_max_raw'];
  for (const [p, b] of ANNUAL) {
    const h = await (await fetch(`${BASE}annually_s.php?prec_no=${p}&block_no=${b}&year=&month=&day=&view=`)).text();
    const d = new DOMParser().parseFromString(h, 'text/html');
    const name = (h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').match(/(\S+（\S+）)\s*年ごとの値/) || [])[1];
    const t = d.querySelector('table#tablefix1');
    if (t) for (const r of [...t.querySelectorAll('tr')].slice(3)) {
      const c = [...r.cells].map(x => x.textContent.trim());
      L.push([p, b, name, c[0], JSON.stringify(c[3] || ''), JSON.stringify(c[4] || '')].join(','));
    }
    await sleep(1500);
  }
  save('jma_annual_raw.csv', L);
}

async function monthly() {
  const L = ['block_no,station,year,month,total_raw,daily_max_raw'];
  for (const [p, b, n] of MONTHLY) for (let y = 1901; y <= 2025; y++) {
    const h = await (await fetch(`${BASE}monthly_s1.php?prec_no=${p}&block_no=${b}&year=${y}&month=&day=&view=`)).text();
    const t = new DOMParser().parseFromString(h, 'text/html').querySelector('table#tablefix1');
    if (t) for (const r of [...t.querySelectorAll('tr')].slice(3)) {
      const c = [...r.cells].map(x => x.textContent.trim());
      if (/^\d+$/.test(c[0])) L.push([b, n, y, c[0], JSON.stringify(c[3]), JSON.stringify(c[4])].join(','));
    }
    await sleep(300);
  }
  save('jma_monthly_raw.csv', L);  // Chrome は同じタブで2回目の自動ダウンロードを止めることがあるので、別のタブで実行する
}

// await annual();
// await monthly();
