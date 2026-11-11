-- 03 5つの照合ルールで「同じ人」のグループ番号をつける（T-SQL。DuckDB では文字列をつなぐ + を || に置き換えて検証）
-- グループ番号は、同じキーの中でいちばん小さい customer_id。
-- R4・R5 の「または」は、MIN をキーごとに2回かけて、つながった行を同じ番号にそろえる（2回で足りるかは結果で確かめる）
WITH r AS (
    SELECT *,
        MIN(customer_id) OVER (PARTITION BY name, birth, tel, email)                         AS g1,  -- R1 完全一致（tel の NULL どうしも同じとみなされる）
        MIN(customer_id) OVER (PARTITION BY name_n, birth)                                   AS g2,  -- R2 名前（空白なし）＋生年月日
        MIN(customer_id) OVER (PARTITION BY name_n, birth,
                               COALESCE(tel_n, 'NULL#' + CAST(customer_id AS VARCHAR(10)))) AS g3,  -- R3 ＋電話（空の電話は照合しない）
        MIN(customer_id) OVER (PARTITION BY name_n, birth, email_n)                          AS g4a
    FROM dbo.c_norm
), s AS (
    SELECT *, MIN(g3) OVER (PARTITION BY name_n, birth, email_n) AS g4b FROM r
), t AS (
    SELECT *, MIN(g4b) OVER (PARTITION BY g3) AS g4,                                      -- R4 名前＋生年月日＋（電話 または メール）
              MIN(g4b) OVER (PARTITION BY birth, email_n)       AS g5a FROM s
), u AS (
    SELECT *, MIN(g5a) OVER (PARTITION BY g4) AS g5b FROM t
)
SELECT customer_id, person_id, dup_type, updated_at, tel, g1, g2, g3, g4,
       MIN(g5b) OVER (PARTITION BY g5a) AS g5                                               -- R5 R4 ＋（生年月日＋メール）：姓が変わった人も拾う
FROM u;
