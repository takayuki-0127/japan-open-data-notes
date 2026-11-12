-- 413 途中で解約した契約に返す額を、日割り・月割り・短期率で出す（T-SQL。SQL Server 本体では動かしていません＝未検証。同じ形を DuckDB で実行して確かめました）
-- cancellations(契約ID, 始期 date, 解約日 date, 年間保険料 int)
-- short_rate(経過日数まで int, 短期率 int)：説明用に作った架空の表。実在の約款の表ではない

WITH a AS (
  SELECT 契約ID, 年間保険料 AS p,
         DATEDIFF(day, 始期, 解約日) AS 経過日数,
         -- 経過月数：始期の応当日を過ぎていれば、1か月に満たない端数を切り上げる
         DATEDIFF(month, 始期, 解約日)
         + CASE WHEN 解約日 > DATEADD(month, DATEDIFF(month, 始期, 解約日), 始期) THEN 1 ELSE 0 END AS 経過月数0
  FROM cancellations
),
b AS (
  SELECT a.*,
         CASE WHEN 経過月数0 < 1 THEN 1 WHEN 経過月数0 > 12 THEN 12 ELSE 経過月数0 END AS 経過月数,
         (SELECT MIN(s.短期率) FROM short_rate AS s WHERE s.経過日数まで >= a.経過日数) AS 短期率
  FROM a
)
SELECT 契約ID,
       FLOOR(p * (365 - 経過日数) / 365.0)  AS 返す額_日割り,     -- 1円未満は切り捨て
       FLOOR(p * (12 - 経過月数) / 12.0)    AS 返す額_月割り,
       FLOOR(p * (100 - 短期率) / 100.0)    AS 返す額_短期率
FROM b;

-- 注意：DATEDIFF(month, …) は「月の数字の差」。1/31 → 2/1 は 1 になる。応当日を過ぎたかどうかは、上のように別に比べる
-- 注意：うるう年をまたぐ契約では、分母を 365 にするか 366 にするかを決めておく（ここでは 365 で固定）
