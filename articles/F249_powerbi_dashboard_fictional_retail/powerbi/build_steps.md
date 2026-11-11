# F249 Power BI で組み立てる手順（.pbix は自動では作っていない）

サンプルマート（架空）・合成データ。この記事の環境（Linux のコンテナ）では Power BI Desktop を動かせないので、.pbix は作っていない。
下の手順で、Power BI Desktop（Windows）を使える人が自分で組み立てる。**かかる時間の目安は 45〜60分**（慣れている人で。推測）。

| # | やること | 目安 |
|---|---|---|
| 1 | GitHub から `powerbi/` フォルダを丸ごとダウンロードし、例えば `C:\work\F249\powerbi\` に置く | 3分 |
| 2 | Power BI Desktop を開き、「データの変換」→「パラメーターの管理」→ 新規：`DataFolder`（テキスト）＝ `C:\work\F249\powerbi\data\` | 2分 |
| 3 | 「新しいソース」→「空のクエリ」を9つ作り、`powerquery.m` の各ブロックを「詳細エディター」に貼る。クエリ名は `// ==== 名前 ====` のとおり。「閉じて適用」 | 8分 |
| 4 | モデル ビューでリレーションシップを9本（下の表）。自動で作られたものは消して作り直す。`sec_user_area`・`ref_noise_band` はつながない | 5分 |
| 5 | `dim_date` を「日付テーブルとしてマーク」（列 date）。`dim_date[ym]` は ym で、`dim_store[store_name]` は store_id で、`dim_store[area]` は area_order で並べ替え。キーの列（store_id など）は非表示 | 4分 |
| 6 | 「DAX クエリ ビュー」を開き、`measures.dax` を全部貼る →「モデルの更新：新しいメジャーを追加」（95本）→「実行」で FY ごとの表が出る | 5分 |
| 7 | 出た表を `measures.md` の「全社 FY2025」と比べる（既存店売上の前年比 0.029133、曜日補正 0.029080、営業利益の前年比 −0.032215 など）。違ったら手順4・5を見直す | 5分 |
| 8 | 「表示」→「テーマ」→「テーマの参照」で `theme.json` | 1分 |
| 9 | `layout_spec.md` のとおり3ページを作り、条件付き書式（フィールド値＝`色_*`）をつける | 20分 |
| 10 | 「ロールの管理」で `rls.md` の役割を作り、「ロールとして表示」で確かめる値と比べる | 5分 |
| 11 | モバイルレイアウトを作り（KGI → カード → 地域の表）、`.pbix` で保存 | 3分 |

## リレーションシップ（多：1、単一方向、次元 → 事実）
| 事実の表 | 列 | 次元の表 | 列 |
|---|---|---|---|
| fact_store_day | biz_date | dim_date | date |
| fact_store_day | store_id | dim_store | store_id |
| fact_store_day_category | biz_date | dim_date | date |
| fact_store_day_category | store_id | dim_store | store_id |
| fact_store_day_category | category_id | dim_category | category_id |
| fact_store_month | month_start | dim_date | date |
| fact_store_month | store_id | dim_store | store_id |
| fact_member_month | month_start | dim_date | date |
| fact_member_month | store_id | dim_store | store_id |


## ウォーターフォール用の小さな表（任意）
```
橋の項目 = DATATABLE ( "順", INTEGER, "項目", STRING, { {1,"前年"},{2,"売上の伸び"},{3,"粗利率（廃棄前）"},{4,"廃棄"},{5,"人件費"},{6,"その他経費"},{7,"当年"} } )
橋の値 = SWITCH ( SELECTEDVALUE ( '橋の項目'[順] ), 1, [既存店営業利益_前年], 2, [橋_売上の伸び], 3, [橋_廃棄前の粗利率], 4, [橋_廃棄], 5, [橋_人件費], 6, [橋_その他経費], 7, [既存店営業利益] )
```
標準のウォーターフォールは合計を自分で足すので、「前年」と「当年」は別のカードにして、間の5つだけをウォーターフォールにするのが簡単。

## うまくいかないとき
- 既存店の値が全社の値と同じになる：`dim_date` を日付テーブルとしてマークしていない、または `fact_store_month[month_start]` → `dim_date[date]` がない。
- 前年の値が空：`dim_date` に 2022-04 からの日付が入っているか（FY2022 は前年の比較のためだけにある）。
- 幅（`幅_*`）が空：12か月か1か月以外の期間を選んでいる（たとえば四半期）。そのときは色をつけない設計。
- `.gz` が読めない：`Binary.Decompress` の行をそのまま使う。解凍した CSV を置くなら `File.Contents` だけにする。
