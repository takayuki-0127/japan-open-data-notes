-- 店ごとの「1日あたりの売上」（T-SQL。SQL Server 本体では動かしていません：未検証）
-- sales(store_id, d, amount)：売上のあった日だけ行がある　　store_days(store_id, d)：店が開いていた日

-- A：売上の表だけで平均（売上0の日が入らないので高く出る）
SELECT store_id, AVG(amount) AS avg_a FROM sales GROUP BY store_id;

-- C：開いていた日を並べて、売上のない日を0で埋めてから平均
SELECT sd.store_id, AVG(COALESCE(s.amount, 0)) AS avg_c
FROM store_days AS sd
LEFT JOIN sales AS s ON s.store_id = sd.store_id AND s.d = sd.d
GROUP BY sd.store_id;

-- 7日の移動平均：行で数える枠（ROWS）は、日が抜けていると7日より長い期間をまたぐ
SELECT store_id, d,
       AVG(amount) OVER (PARTITION BY store_id ORDER BY d
                         ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma7_rows
FROM sales;
-- 0で埋めた表（上の C の中身）に同じ枠を当てれば、暦の7日になる
