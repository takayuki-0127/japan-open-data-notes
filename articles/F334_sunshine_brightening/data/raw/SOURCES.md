# data/raw の出典

取得日：2026-11-16（`src/01_fetch.py` と同じ手順で取得。F331 の作業で同じ日に取ったページを、そのまま写して使っている）

| ファイル | 内容 | URL |
|---|---|---|
| annual/47xxx.html.gz | 気象庁「過去の気象データ検索」地点ごとの「年ごとの値 主な要素」（気象台・測候所など、地点番号 47xxx の157地点）。ページの HTML をそのまま gzip で圧縮 | https://www.data.jma.go.jp/stats/etrn/view/annually_s.php?prec_no=（府県番号）&block_no=47xxx&year=&month=&day=&view= |
| station_prec.csv | 地点番号と府県番号の対応（府県ごとの地点選択ページ https://www.data.jma.go.jp/stats/etrn/select/prefecture.php?prec_no=NN から作成） | — |

- 使った列：日照時間（年合計、時間）、全天日射量（日合計の年平均、MJ/㎡）。
- 「)」（準正常値）はそのまま使い、「]」（資料不足値）・「×」・「///」・空欄は欠測にした。
- 2026年は途中のため使っていない（分析は1961〜2025年）。
