// 内閣府「四半期別GDP速報」の過去の公表回（2001〜2026年）から、
// 実質・名目の季節調整系列（前期比）と実質の原系列（前年同期比）の CSV を集める。
// https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/files_sokuhou.html を開いたタブの
// 開発者ツールで実行する（コンテナからは内閣府のサイトに届かないため、ブラウザで取った）。
// CSV は Shift_JIS なので TextDecoder で読む。結果は f50_qe_releases.json としてダウンロードされる。
(async () => {
  const base = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/";
  const menus = [];
  for (let y = 2001; y <= 2026; y++) {
    const u = `${base}${y}/toukei_${y}.html`;
    const d = new DOMParser().parseFromString(await fetch(u).then(r => r.text()), "text/html");
    for (const a of d.querySelectorAll("a")) {
      const h = a.getAttribute("href");
      if (h && /gdemenuja/.test(h)) menus.push(new URL(h, u).href);
    }
  }
  const dec = new TextDecoder("shift_jis");
  const out = [];
  for (const m of menus) {
    const rec = { menu: m };
    const d = new DOMParser().parseFromString(await fetch(m).then(r => r.text()), "text/html");
    for (const h of [...d.querySelectorAll("a")].map(a => a.getAttribute("href"))
        .filter(h => h && /ritu[-_](jk|mk|jg)\d+[^/]*\.csv/i.test(h))) {
      const k = h.match(/ritu[-_](jk|mk|jg)/i)[1].toLowerCase();
      if (rec[k]) continue;
      const u = new URL(h, m).href;
      rec[k] = dec.decode(await fetch(u).then(r => r.arrayBuffer()));
      rec[k + "_url"] = u;
    }
    out.push(rec);
    await new Promise(r => setTimeout(r, 150));
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out)], { type: "application/json" }));
  a.download = "f50_qe_releases.json";
  a.click();
})();
// 注：今回の実行では、最初は CSV の名前が「…_1.csv」「…r.csv」の3回分（qe133_2・qe201_2r・
// qe241_2 の訂正版）を取りこぼしたので、あとから同じ方法で取り直して f50_qe_extra.json に分けて置いた。
// 上の正規表現はその取り直し後のもの（この1本で全部取れる）。
