# 308　Kaggle：最終提出の2本を、どう選んだか

## 問い
最終提出の2本を「CV で選ぶ」と決めていた。終了後の Private で見て、選び方による差はどれだけあったか。

## 手法
| 手順 | 内容 |
|---|---|
| 1 | 提出21回の CV・Public・Private を1つの表にする |
| 2 | 選び方5通り（CV で選ぶ／Public の上位2本／途中の案2つ）について、2本のうち高い方の Private を出す |
| 3 | 全データで学び直した版10本から2本を選ぶ45通りの最終点の幅を出す |
| 4 | Public と Private、CV と Private の順位相関（Spearman）を、全体と学び直した版だけで出す |

## 主な結果
- CV で選んだ2本の Private：v25 ブレンド 0.96169（全提出の最高に並ぶ）、v25 単体 0.96163
- Public の上位2本（v22 と、0.96078 で並ぶ v25 または v17b）でも最終点は 0.96169。途中の案（v22＋v9）は 0.96168、fold 版だけの案（v9＋v3）は 0.96160
- 学び直した版から2本を選ぶ45通りの最終点は 0.96163〜0.96169
- Public と Private の順位相関：0.96 以上の19回で 0.88、学び直した版10本だけで 0.65。Public の幅 0.00016、Private の幅 0.00008
- 学び直した版は fold 平均の版より Private で平均 +0.00009（Public で +0.00012）
- CV と Private の順位相関（学び直した版のうち CV を当てられる7本）：0.29
- ブレンド − 単体：CV +0.00013、Public +0.00012、Private +0.00006
- 終了後の提出画面は「2本中0本を選択」で、Public の上位2本が自動で評価されていた（記録では 10/19 に選択済み）

## データ
- Kaggle Playground Series S6E10「Predicting Airline Satisfaction」（2値分類・AUC、2026-10-31 終了）の、自分の提出の記録
- `data/submissions.csv`：版ごとの CV・Public・Private（自分でまとめた表。Private は 2026-11-12 に提出画面で確認）。コンペのデータそのものは置いていない
- CV の種類：`sweet`＝早期打ち切りに検証分割を使っていた版（v1〜v9）、`honest`＝早期打ち切りを学習側の10%で行った版、`honest_fold_equiv`＝全データで学び直した版に、同じ設定の fold 版の CV を当てたもの
- 使ったのは自分のモデルの予測だけ

## 動かし方
```
pip install -r requirements.txt
python src/a308.py
```
`results/` と `figures/` が作り直される。

## 注意・言えないこと
- 1つのコンペ・21回の提出だけ。0.00001 は点数の表示の刻みで、選び方の優劣は決められない
- 最終の順位は確かめていない。記録の提出回数は22、提出画面で数えたのは21
- 学び直した版の CV は fold 版の CV を当てたもの
- Public の上位2本の同点（v25 と v17b）のどちらが自動で選ばれたかは確かめていない

## 出典
- Kaggle Playground Series S6E10（https://www.kaggle.com/competitions/playground-series-s6e10）の自分の提出画面と、期間中の自分の記録

note 記事：（公開後に記入）
