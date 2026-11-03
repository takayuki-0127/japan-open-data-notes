// note.com の公開ページ上（https://note.com/takayukimatsuura）でブラウザのコンソールから実行する。
// 公開 API で見える数字だけを使う（スキ・コメント数・本文の構成）。閲覧数は公開ページに出ないので取らない。
// スキを付けた人の一覧（likes）は保存しない。
(async () => {
  let pub = [], q = 1;
  while (true) {
    const j = await fetch('/api/v2/creators/takayukimatsuura/contents?kind=note&page=' + q).then(r => r.json());
    const c = j.data.contents || []; pub.push(...c);
    if (j.data.isLastPage || !c.length) break; q++;
  }
  const rows = [];
  for (const x of pub) {
    const d = (await fetch('/api/v3/notes/' + x.key).then(r => r.json())).data;
    const dv = document.createElement('div'); dv.innerHTML = d.body || '';
    const imgs = [...dv.querySelectorAll('img')];
    rows.push({ key: x.key, title: d.name, publishAt: d.publish_at || x.publishAt,
      like: d.like_count ?? x.likeCount, comment: d.comment_count ?? x.commentCount, anon: x.anonymousLikeCount,
      chars: dv.textContent.length, n_img: imgs.length, n_fig: dv.querySelectorAll('figure').length,
      n_h2: dv.querySelectorAll('h2').length, n_h3: dv.querySelectorAll('h3').length, n_table: dv.querySelectorAll('table').length,
      n_code: dv.querySelectorAll('pre').length, n_link: dv.querySelectorAll('a').length, eyecatch: !!(d.eyecatch || x.eyecatch),
      hashtags: (d.hashtag_notes || x.hashtags || []).map(h => (h.hashtag && h.hashtag.name) || h.name || '').join(' '),
      github: /github\.com/.test(d.body || ''), imgsrc: imgs.map(i => i.src.split('?')[0].split('/').pop()).join(' ') });
    await new Promise(r => setTimeout(r, 400));
  }
  const b = new Blob([JSON.stringify({ fetched_at: new Date().toISOString(), source: 'note public API', rows })], { type: 'application/json' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'f164_note_public.json'; a.click();
})();
