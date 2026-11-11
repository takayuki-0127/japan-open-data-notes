# 引き継ぎ資料：サンプルマート（架空）の分析

架空の食品スーパー「サンプルマート（架空）」で、分析担当が1年かけて作ったもの（F246〜F251）を、次の人が同じ数字で作り直せるようにまとめた資料。
**会社も数字もすべて架空（乱数で合成したデータ）。** 実在の会社・顧客のデータは使っていない。

## まず、これだけ

```bash
git clone --filter=blob:none --sparse https://github.com/takayuki-0127/japan-open-data-notes.git
cd japan-open-data-notes
git sparse-checkout set articles/F254_handover_package_fictional_retail
cd articles/F254_handover_package_fictional_retail/handover
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python run_all.py
.venv/bin/python tests/test_rules.py
```

- Windows では `.venv/bin/python` を `.venv\Scripts\python` に読み替える（筆者は Linux でしか試していない）。
- 最後に `[照合] 基準と：数字のファイル 88 のうち 同じ 88、違う 0、作られなかった 0` と出て、テストが `結果： OK` なら、引き継ぎはできている。
- かかる時間：ライブラリを入れるのに約30秒、`run_all.py` が約3分（Linux・2コアで、ほかの処理と並べて測った値。ほとんどは偶然の幅を測る20通りの作り直し）。

## 前提

| 要るもの | 版 | なぜ |
|---|---|---|
| Python | 3.11 以上（試したのは 3.13） | 設定の読み込みに tomllib を使う |
| git | どれでも | 決めたコミットの F246〜F251 を取る。照合で元のファイルと比べる |
| ネットワーク | github.com と pypi.org に出られること | コードとライブラリを取る |
| ライブラリ | `requirements.lock` のとおり | 各回の requirements.txt は下限だけなので、そのまま入れると版が変わる（docs/troubleshooting.md の T1） |
| Chromium（任意） | `--target all` のときだけ | 図の一部と PDF。`requirements-browser.lock` を入れてから `python -m playwright install chromium` |
| 日本語フォント（任意） | Noto Sans CJK JP | 図の文字。無くても数字のファイルは同じになる |

## 全体の流れ

`run_all.py` は、次の順に流す。どの段も、各回の `src/` のスクリプトをそのまま流す（書き換えていない）。

1. **準備**：`config.toml` のコミットの F246〜F251 を `work/repo/` に取る
2. **F246** 合成データ（seed 0）→ 偶然の幅（20通り）
3. **F247** F246 のデータを正解として写す → 現場から届くファイル（汚れ入り）→ SQL で mart
4. **F248** mart を写す → 締めの日ごとの店×月と計画 → 12か月 × 速報・確定の月次レポート
5. **照合**：作った数字のファイル88個を、基準（`expected/manifest.json`）と比べる

前の回の成果物は、GitHub からではなく、この中で作り直したもの（隣のフォルダ）を使う。前の回を直したとき、その直しが後の回まで流れる。
回どうしのつながりは `docs/layout.md`。

## 出てくるもの

| 場所 | 中身 |
|---|---|
| `work/repo/articles/F247_data_mart_fictional_retail/mart/` | mart（店×日・店×日×部門・店×月・dim） |
| `work/repo/articles/F248_monthly_report_template_fictional_retail/reports/` | 月次レポート（`report_YYYYMM_v1`＝速報、`v2`＝確定。HTML・Markdown・JSON） |
| `work/logs/` | 段ごとのログ |
| `work/run_log.json` | 段ごとの成否・かかった時間 |
| `work/verify.csv` | ファイルごとの照合の結果（基準と／元のファイルと） |

## ほかの使い方

```bash
.venv/bin/python run_all.py --target all     # F246〜F251 の README の手順を全部（図・PDF を含む。約10分）
.venv/bin/python run_all.py --check-only     # 作り直さずに照合だけ
```

## 困ったとき

- 止まった段の名前とログの場所が出る。`docs/troubleshooting.md` に、試走で止まったところと直し方を書いた。
- 数字が基準と違うとき：まず `requirements.lock` で入れたか（`.venv/bin/python -m pip freeze`）を確かめる。
- 決めごと（既存店・締めの日など）の意味と、コードのどこにあるか：`docs/decisions.md`。
- 毎月の運用：`docs/monthly_runbook.md`。引き継ぎのときに確かめること：`docs/checklist.md`。

## この資料で、まだやっていないこと

- 各回のコードの整理（同じ決めごとを1か所にまとめる、など）。先に「数字が同じか」を確かめる仕組みを置いた。整理はこの後、テストを通しながら進める。
- F252（来期の予算）・F253（データの品質チェック）は、この資料を作った後に足す回。`config.toml` に足して、`stages.py` に段を書く。
- Windows・Mac での試走。
