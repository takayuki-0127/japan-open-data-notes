# 元データの出典（取得日と URL）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| onsen_trend_table.pdf | 環境省「温泉利用状況経年変化表」（昭和32年度〜令和6年度、令和7年3月末現在） | https://www.env.go.jp/nature/onsen/pdf/6-7_p_3.pdf | b335ed3f8bed |

- 掲載ページ：環境省「温泉利用状況等について」https://www.env.go.jp/nature/onsen/data/index.html
- 表は PDF だけで公開されているため、src/01b_extract.py で文字を取り出して data/onsen_trend.csv を作った（pdftotext を使う。一度だけ流す）。
  run_all.sh は data/onsen_trend.csv から先を流す。取り出しの確かめ（源泉総数 = 利用源泉の計 + 未利用源泉の計 など）は 01b_extract.py の中で行っている。
