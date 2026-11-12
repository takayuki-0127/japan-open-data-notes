-- 474 「上と同じなら省略」された見出しを、部門の中だけで下方向に埋める（T-SQL の書き方）
-- sheet_rows(row_no, dept, cat, item, region)：Excel を上から順に読んだままの行。dept は結合セルの先頭行だけ、cat は変わった行だけに値がある
-- SQL Server 2022 以降なら LAST_VALUE(...) IGNORE NULLS でも書けるが、ここでは古い版でも動く「値のある行を数えて組にする」書き方にした
-- 記事では DuckDB で実行して pandas の結果と一致を確かめた。SQL Server での実行は未検証
WITH d AS (            -- ① 明細の行だけ残す（空行・小計・合計を落とす）
    SELECT row_no, dept, cat, item, region,
           COUNT(dept) OVER (ORDER BY row_no ROWS UNBOUNDED PRECEDING) AS dept_grp
    FROM sheet_rows
    WHERE item IS NOT NULL AND item <> '小計'
),
d2 AS (                -- ② 部門：同じ組の中の、値のある1行を全体に広げる
    SELECT row_no, item, region, cat,
           MAX(dept) OVER (PARTITION BY dept_grp) AS dept
    FROM d
),
d3 AS (                -- ③ 商品区分：部門の中だけで組を作る（部門をまたいで埋めない）
    SELECT row_no, dept, cat, item, region,
           COUNT(cat) OVER (PARTITION BY dept ORDER BY row_no ROWS UNBOUNDED PRECEDING) AS cat_grp
    FROM d2
)
SELECT row_no, dept,
       MAX(cat) OVER (PARTITION BY dept, cat_grp) AS cat,
       item,
       region          -- 地域は埋めない（空は「不明」のまま）
FROM d3
ORDER BY row_no;
