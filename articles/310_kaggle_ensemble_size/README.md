# 310　Kaggle：アンサンブルは、何本混ぜると効かなくなるのか

## 問い
モデルを混ぜる本数を増やしたとき、何本目から効かなくなったか。

## 手法
| 手順 | 内容 |
|---|---|
| 1 | 強い順に1本ずつ足したときの正直な CV（OOF の順位ブレンド）を並べる |
| 2 | 比率の決め方まで含めた入れ子の CV、stacking（ロジスティック回帰・LightGBM）と比べる |
| 3 | 全データで学び直した版で、混ぜ方ごとの Public・Private を並べる |
| 4 | 予測の順位相関と、混ぜた結果を対応させる |

## 主な結果
- 単体の CV：CatBoost 0.96094、LightGBM 0.96068、XGBoost 0.96064、NN 0.96022
- CV：CatBoost だけ 0.96094 → ＋LightGBM 0.96103（+0.00009）→ ＋XGBoost 0.96104（+0.00001）→ ＋NN 0.96107（+0.00003）。伸び +0.00013 の69%が2本目
- 入れ子の CV 0.96106（−0.00001）。stacking はロジスティック回帰 0.96108（+0.00001）、LightGBM 0.96103（−0.00004）
- Private：CatBoost だけ 0.96163／2種類1回分 0.96165／3回分平均 0.96166／4回分平均 0.96169／＋XGBoost 0.96168／＋NN 0.96168／4種類を CV の比率で 0.96169
- XGBoost を足す：CV +0.00001、Public +0.00004、Private −0.00001。NN を足す：Public −0.00003、Private −0.00001
- 順位相関：同じ作り方の学び直しどうし 0.998〜0.999、XGBoost 0.9928、NN 0.9765
- 最初に3モデルを混ぜた v2：Public −0.00008、Private −0.00008（元データを行で足す変更も同時）

## データ
- Kaggle Playground Series S6E10「Predicting Airline Satisfaction」（2値分類・AUC、2026-10-31 終了）の、自分の提出の記録
- `data/submissions.csv`：版ごとの CV・Public・Private（自分でまとめた表。Private は 2026-11-12 に提出画面で確認）。コンペのデータそのものは置いていない
- CV の種類：`sweet`＝早期打ち切りに検証分割を使っていた版（v1〜v9）、`honest`＝早期打ち切りを学習側の10%で行った版、`honest_fold_equiv`＝全データで学び直した版に、同じ設定の fold 版の CV を当てたもの
- 使ったのは自分のモデルの予測だけ

## 動かし方
```
pip install -r requirements.txt
python src/a310.py
```
`results/` と `figures/` が作り直される。

`data/blend.csv`・`data/corr.csv`：期間中の記録にある、混ぜる本数ごとの CV と、予測の順位相関。

## 注意・言えないこと
- 1つのコンペ・4種類のモデルだけ
- 「2本目で7割」は強い順に足した場合
- 0.00001〜0.00003 の差は点数の刻みに近い
- NN は作り込んでいない
- v20 の NN の比率 0.15 は v13 の CV の重みから取ったもの

## 出典
- Kaggle Playground Series S6E10（https://www.kaggle.com/competitions/playground-series-s6e10）の自分の提出画面と、期間中の自分の記録

note 記事：（公開後に記入）
