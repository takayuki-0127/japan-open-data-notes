# 286 予測モデルは、線形回帰と勾配ブースティングのどちらから始めるか（④ 振り返り R010）

このシリーズで予測モデルを作った記事のうち、線形のモデル（リッジ回帰・ElasticNet・Cox など）と勾配ブースティング（LightGBM など）の成績を両方書いた記事を並べ、どんなときにどちらが良かったかを数えたフォルダです。場所で分けた検証を記事をまたいで比べた [F123](https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F123_spatial_block_cv_review) とは、モデルの選び方に絞る点が違います。

## 問い

- 勾配ブースティングを使った記事のうち、線形のモデルと並べた記事はどれだけあるか
- 両方の成績がある組で、どちらが良かったか。差はどれくらいか
- 見ていない場所で確かめると、差はどう変わったか

## 手法

| 手順 | 中身 |
|---|---|
| README を数える | 268 と同じ（共有している README は1本に数え、480本）。LightGBM・XGBoost・勾配ブースティング・GBM などを書いた記事を拾い、線形回帰・リッジ・ElasticNet・ロジスティック回帰・Cox なども書いているかを見た |
| 成績を写す | 両方の成績を README に書いた10本・19組を手で写した（`data/cases.csv`）。同じデータ・同じ分け方の組だけ |
| 比 | 勾配ブースティング ÷ 線形（外れ・誤差は小さいほど良い。R²・C は大きいほど良いので 1−値 の比にした）。0.97 未満を「勾配ブースティングが良い」、1.03 超を「線形が良い」、その間を「ほぼ同じ」とした |

## 主な結果

- 勾配ブースティングの名前がある README は31本、うち線形のモデルも書いていたのは22本（`data/gbm_articles.csv`。言葉で拾ったので、本文で触れただけの記事を含む）
- 19組のうち、勾配ブースティングが良かったのは11組、ほぼ同じ4組、線形が良かった4組（図1、`results/cases_ratio.csv`）
- 勾配ブースティングが良かったのは地価（[F03](https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F03_land_price_ml)・[F75](https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F75_gp_land_price)・[F158](https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F158_land_price_update)・[F123](https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F123_spatial_block_cv_review)）と電力需要（[F22](https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F22_power_demand_forecast)・[F119](https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F119_forecast_scorecard)）。比は 0.39〜0.65 で、外れが3.5〜6割減った（F123 の出生率はランダムに分けたときだけ 0.89）
- 線形と同じか線形が良かったのは、気温（[F74](https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F74_temperature_kriging)：0.73℃ と 0.74℃、予報区で分けると 0.75℃ と 0.89℃）、失業率（[F13](https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F13_unemployment_forecast)：3か月先 0.109 と 0.114）、水道料金（[F144](https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F144_water_tariff_density)：R² 0.37 と 0.32）、法人の閉鎖（[F149](https://github.com/takayuki-0127/japan-open-data-notes/tree/main/articles/F149_ml_survival)：C 0.593 と 0.592）
- 場所で分けて確かめると、6組すべてで比が大きくなった（勾配ブースティングに不利な向き）。F03 は 0.46 → 0.62（20km）・0.79（都道府県）、F75 は 0.39 → 0.60、F123 の出生率は 0.89 → 1.02、F74 の気温は 1.01 → 1.19（図2、`results/random_vs_block.csv`）
- 状況ごとの整理（図3、記録を見て後から整理したもの。推測を含む）

## 動かし方

```
cd japan-open-data-notes/articles/286_linear_vs_gbm_first/src
pip install -r ../requirements.txt
python a286.py ../../..
```

数えた時点のリポジトリは 35dc628（2026年11月12日）。

## データ

- `data/cases.csv`：19組の成績（README から手で写した。出どころの表を note に書いた）
- `data/gbm_articles.csv`：勾配ブースティングの名前がある記事と、線形のモデルも書いていたか

## 言えないこと

- 19組は、両方の成績を README に書いた組だけ。線形を試さなかった記事、成績を書かなかった記事は入っていない
- 比べた勾配ブースティングは、記事ごとに設定を固定したもの。作り込めば差は変わりうる。線形も特徴量の作り方で変わる
- 指標は記事ごとに違う（外れの%・RMSE・MAE・R²・C）。比の大きさを記事の間で厳密に比べられるわけではない
- 図3の状況の分け方は、10本を見て後から付けたもの。ほかのデータで同じになるとは限らない（推測）

## 出典

- takayuki-0127/japan-open-data-notes の各記事の README（2026年11月12日時点、コミット 35dc628）
