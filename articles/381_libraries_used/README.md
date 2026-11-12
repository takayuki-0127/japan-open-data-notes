# 381 どのライブラリを、何本の記事で使ったか（④ 振り返り R111）

GitHub に置いた記事639本のコード（.py 2,200個）の import 文と requirements.txt を数えた

## 問い

- 外部のライブラリを、何種類、何本の記事で使ったか
- 1本の記事はいくつのライブラリを使うか。記事のまとまりで違うか
- requirements.txt に版（バージョン）は書いてあるか

## 手法

| 手順 | 中身 |
|---|---|
| 拾う（`src/a381_extract.py`） | `articles/*/` の .py を ast で読み、import のいちばん上のモジュール名を記事ごとに集める。Python に付属するものは「標準」、記事のフォルダ（またはほかの記事のフォルダ）に同じ名前の .py があるものは「自作」、それ以外を「外部」とした |
| requirements.txt | 1行ずつ、名前と版の書き方（==・>=・なし）に分けた |
| まとめ方（`src/a381.py`） | ライブラリごとの記事数、1本あたりの数、版の書き方の割合、import と requirements.txt の突き合わせ（sklearn → scikit-learn などは名前を直した） |

F200（データと手法のつながり）はデータと手法を数えた。ここではコードの道具だけを数える

## 主な結果（`results/summary.json`、`results/external_libraries.csv`）

- 外部のライブラリは62種類。matplotlib 639本、pandas 637本、numpy 621本、statsmodels 197本（31%）、scipy 144本（23%）、duckdb 58本、openpyxl 51本、scikit-learn 50本、requests 45本、lightgbm 24本
- 10本以上の記事で使ったのは12種類、1本だけは22種類
- 1本あたりの外部ライブラリは中央値4種類（最大10）。3種類以下が219本（34%）
- requirements.txt の2,968行：版なし53.0%、>= で下限37.2%、== で固定9.8%
- 全部の行を == で固定した記事は57本（うち精選が34本）。版をまったく書いていない記事は306本

| まとまり | 記事 | 外部（中央値） | == で固定 | >= で下限 | 版なし |
|---|---|---|---|---|---|
| 000–099 | 92 | 4 | 0% | 20% | 80% |
| 100–226 | 127 | 3 | 0% | 0% | 100% |
| F01–F99 | 97 | 5 | 3% | 46% | 51% |
| F100–F199 | 100 | 4 | 19% | 48% | 32% |
| F200–F255 | 36 | 5 | 14% | 73% | 12% |
| F256–F295（精選） | 40 | 4 | 88% | 10% | 1% |
| 227–・T（1000本計画） | 147 | 4 | 0% | 61% | 39% |

- 使っているのに requirements.txt にないライブラリがある記事は15本（scipy 8本、numpy 3本）
- requirements.txt にあるのに import していないライブラリがある記事は232本（openpyxl 99本、xlrd 74本、statsmodels 52本）。openpyxl と xlrd は pandas が Excel を読むときに使うので import に出ない

## 確かめたこと

- import した外部ライブラリのうち、1〜2本でしか使っていない名前を目で見て、自作のファイルが混じっていないか確かめた（ほかの記事の .py を読み込む形は「自作」に直した）
- `src/a381_extract.py` と `src/a381.py` を空のフォルダで流し直し、data・results・figures が一致することを確かめた

## 動かし方

```
python src/a381_extract.py <japan-open-data-notes のルート>   # data/imports.csv・requirements.csv・articles.csv
python src/a381.py                                            # 集計と図
```

## データ

| ファイル | 中身 |
|---|---|
| data/imports.csv | 記事ごとの import（モジュール名、標準・自作・外部、そのモジュールを import したファイルの数） |
| data/requirements.csv | requirements.txt の1行（名前、版の書き方、版） |
| data/articles.csv | 記事ごとの .py の数と requirements.txt の行数 |

## 注意（言えないこと）

- 数えたのは import 文と requirements.txt の文字だけ。実際に動かしたときの版は分からない
- import していても使っていない場合がある。関数の中の import も同じ1本に数えた
- 外部か自作かは、同じ名前の .py があるかで分けた。分け方の誤りが少し残っている可能性がある（`samplemart` は自作のフォルダだが外部に数えている）
- 記事のまとまりは番号で分けたもので、作った順とは少しずれる

## 出典

- japan-open-data-notes の各記事フォルダのコードと requirements.txt（https://github.com/takayuki-0127/japan-open-data-notes の articles/、コミット 00b426f、2026年11月12日）
