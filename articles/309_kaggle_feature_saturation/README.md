# 309　Kaggle Playground：特徴量を足し続けて、どこで伸びが止まったか

## 問い
特徴量を足していったとき、点数の伸びはどこで止まったか。

## 手法
| 手順 | 内容 |
|---|---|
| 1 | 特徴量を変えた5つの場面（v1→v3、v3→v4、v3→v5、v11 擬似ラベルなし→v15、v12→v18）の CV・Public・Private の差を出す |
| 2 | v1 から最良までの伸びのうち、v1→v3 が占める割合を出す |
| 3 | fold ごとの差（足した後 − 足す前）を、特徴量3つ（v15）と擬似ラベル（v11）で並べる |
| 4 | 採用の基準（5 fold 中4つ以上で上昇・全体で +0.00005 以上）に照らす |

## 主な結果
- v1→v3（路線の集計・TE・元データ teacher・評価×背景の組み合わせ）：CV +0.00252、Public +0.00253、Private +0.00223
- v1 から最良までの伸び（Public +0.00265、Private +0.00233）のうち、v1→v3 が Public で95%、Private で96%
- そのあと：TE キー2つ（v4）CV −0.00001／評価の期待値との差（v5）CV −0.00008／特徴量3つ（v15）CV +0.00003／同じ3つで学び直し（v18）Public −0.00003・Private +0.00002
- v15 の fold ごとの差：LightGBM は4/5で上昇・平均 +0.00004、CatBoost は2/5で上昇・平均 +0.00001。差の幅は −0.00011〜+0.00011
- XGBoost の fold ごとの AUC は 0.95950〜0.96140（幅 0.0019）。fold の間の水準の差は、足し算の効果より1桁大きい

## データ
- Kaggle Playground Series S6E10「Predicting Airline Satisfaction」（2値分類・AUC、2026-10-31 終了）の、自分の提出の記録
- `data/submissions.csv`：版ごとの CV・Public・Private（自分でまとめた表。Private は 2026-11-12 に提出画面で確認）。コンペのデータそのものは置いていない
- CV の種類：`sweet`＝早期打ち切りに検証分割を使っていた版（v1〜v9）、`honest`＝早期打ち切りを学習側の10%で行った版、`honest_fold_equiv`＝全データで学び直した版に、同じ設定の fold 版の CV を当てたもの
- 使ったのは自分のモデルの予測だけ

## 動かし方
```
pip install -r requirements.txt
python src/a309.py
```
`results/` と `figures/` が作り直される。

`data/folds.csv`：期間中の記録にある fold ごとの差。

## 注意・言えないこと
- 1つのコンペだけ。95%という割合は最初の版の作りで変わる
- v1〜v9 の CV は甘い CV（早期打ち切りに検証分割を使用）
- 止まったと言えるのは自分が試した範囲だけ
- 0.00003 以下の差は誤差と区別できない

## 出典
- Kaggle Playground Series S6E10（https://www.kaggle.com/competitions/playground-series-s6e10）の自分の提出画面と、期間中の自分の記録

note 記事：（公開後に記入）
