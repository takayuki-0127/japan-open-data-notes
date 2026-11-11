# 試走で止まったところと、直し方

新しい人の役で、きれいなフォルダから各回の README だけを見て流したとき（2026-11-11、Linux・Python 3.13）に起きたこと。
試走は2通り：**同じ版**（記事を作ったときのライブラリ）と、**最新版**（まっさらな venv に各回の requirements.txt のとおり入れた。pandas 3.1.1・DuckDB 2.0.0 など）。

| # | 起きたこと | どこで | 同じ版 | 最新版 | 直し方（この資料で） |
|---|---|---|---|---|---|
| T1 | 版が変わる。各回の requirements.txt は下限だけ（`pandas>=2.0` など）で、今入れると pandas 3 系・DuckDB 2 系が入る | 全部の回 | — | 止まりはしなかった。数字は小数の終わりの方で変わった（多くは相対 1e-8 以下） | `requirements.lock` で版を固定した |
| T2 | 生成物のフォルダが無いと止まる。`results/`・`dashboard/` を作らずに書こうとする | F247 `02_整形.py`・`05_図.py`、F249 `02_整形.py`・`04_図.py` | 止まった（4手順） | 止まった（4手順） | run_all.py は、生成物を消さずに git のコミットの状態から流す（フォルダが残る）。各回のコードに `mkdir` を足すのは次の段階 |
| T3 | 同じ版・同じデータでも、実行ごとに mart の数字が変わる。DuckDB が並列で足し算し、足す順番が変わる。人時を 0.1 の単位で書くので、四捨五入の境目にある値が 0.1 ずれ、F248 の人時粗利（相対 1e-5 ほど）まで動く | F247 `03_整える.py` → F248 | 起きた | 起きた | `samplemart/launch.py` で DuckDB を1本で足す（`SET threads TO 1`）。何回流しても同じバイトになる |
| T4 | `.csv.gz` は、中身が同じでもバイトが違う（gzip は書いた時刻を頭に入れる） | F246・F247・F249 | 起きた | 起きた | 照合は .gz の中身で比べる（`samplemart/verify.py`） |
| T5 | 図・PDF を作る手順で、ブラウザ（Chromium）が無いと止まる | F246 `06`、F248 `05`、F250 `05`、F251 `05`（F249 `04` も使う） | 止まらなかった（前から入っていた） | 止まった（4手順） | `--target all` のときだけ要ると README に書き、`requirements-browser.lock` を分けた |
| T6 | 手で書いたファイルが、作られるファイルと同じフォルダにある。生成物のつもりでフォルダごと消すと、手書きの3つも消える | F249 `powerbi/` の layout_spec.md・rls.md・build_steps.md | 消えた（試走で生成物を消したため） | 同じ | run_all.py はコミットにあるファイルを消さない。`docs/layout.md` に書いた |
| T7 | F248 だけを渡されると止まる。02・03 が、隣の F247・F246 のフォルダを直接読む（GitHub から取る逃げ道がない）。README には「F247 を先に流す」とだけ書いてある | F248 `02_整形.py`・`03_レポート.py` | （試走では隣にあったので起きなかった。コードを読んで見つけた） | 同じ | run_all.py は6回を同じ親フォルダに並べる。`docs/layout.md` に書いた |
| T8 | 速さを測った数字は、毎回変わる（ほかの処理と並べて流すと遅くなる） | F249 `results/main.json` の「速さ」 | 起きた | 起きた | 照合では、F249 の main.json の差は「速さ」の欄だけかを見る（基準は `--target all` のときだけ） |

## エラーの出方（見分け方）

- `OSError: Cannot save file into a non-existent directory: '.../results'` → T2。フォルダを作ってから流し直す（`mkdir results`）か、run_all.py を使う。
- `Executable doesn't exist at ...chromium...`（枠で囲んだ長いメッセージ）→ T5。`python -m playwright install chromium`。
- `FileNotFoundError: ... ../F247_data_mart_fictional_retail/...` → T7。F246・F247 のフォルダを、同じ親フォルダに並べる。
- 照合で `違う` が mart の `store_month.csv` だけに出る → T3。launch.py を通さずに流していないか。

## まだ直していないもの（次の段階）

- T2：各回のスクリプトの先頭で、書き出すフォルダを作る（1行ずつ）
- T3：mart の人時を 0.1 で丸める前に、SQL の中で足す順番を決める（ORDER BY をつけた集計、または整数の単位で持つ）
- T7：F248 の 02・03 にも、GitHub から取る逃げ道をつける
- これらを直したら、`expected/manifest.json` を作り直し（`--make-baseline`）、差が出たファイルを改訂履歴に書く
