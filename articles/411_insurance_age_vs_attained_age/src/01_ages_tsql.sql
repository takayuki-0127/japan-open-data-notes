-- 411 満年齢・保険年齢・年度末の満年齢を出す（T-SQL。SQL Server 本体では動かしていません＝未検証。同じ形を DuckDB で実行して確かめました）
-- policyholders(契約者ID, 生年月日 date, 契約日 date)

-- 落とし穴：DATEDIFF(year, …) は「年の数字の差」で、誕生日を迎えたかどうかを見ない
--   DATEDIFF(year, '1980-12-31', '2025-01-01') は 45（満年齢は 44）
SELECT 契約者ID, DATEDIFF(year, 生年月日, 契約日) AS 年だけの差 FROM policyholders;

-- 満年齢：今年の誕生日がまだなら1引く。DATEADD は 2/29 をうるう年でない年に 2/28 にする
WITH a AS (
  SELECT 契約者ID, 生年月日, 契約日,
         DATEDIFF(year, 生年月日, 契約日)
         - CASE WHEN DATEADD(year, DATEDIFF(year, 生年月日, 契約日), 生年月日) > 契約日 THEN 1 ELSE 0 END AS 満年齢
  FROM policyholders
)
SELECT 契約者ID, 満年齢,
       -- 保険年齢：直近の誕生日から6か月を「超えた」ら1歳上げる（6か月ちょうどは上げない）
       満年齢 + CASE WHEN 契約日 > DATEADD(month, 6, DATEADD(year, 満年齢, 生年月日)) THEN 1 ELSE 0 END AS 保険年齢,
       -- 年度末の満年齢：契約日を含む年度の 3/31 時点の満年齢
       DATEDIFF(year, 生年月日, DATEFROMPARTS(YEAR(契約日) + CASE WHEN MONTH(契約日) >= 4 THEN 1 ELSE 0 END, 3, 31))
       - CASE WHEN DATEADD(year,
                DATEDIFF(year, 生年月日, DATEFROMPARTS(YEAR(契約日) + CASE WHEN MONTH(契約日) >= 4 THEN 1 ELSE 0 END, 3, 31)),
                生年月日) > DATEFROMPARTS(YEAR(契約日) + CASE WHEN MONTH(契約日) >= 4 THEN 1 ELSE 0 END, 3, 31)
              THEN 1 ELSE 0 END AS 年度末の満年齢
FROM a;

-- 境目のテスト：誕生日の前の日・当日、6か月後の当日・次の日、2/29生まれの 2/28 と 3/1 を1行ずつ入れて、期待する年齢と比べる
-- test(生年月日, 契約日, 期待する満年齢, 期待する保険年齢)
--   ('1980-06-15','2025-06-14',44,45) ('1980-06-15','2025-06-15',45,45)
--   ('1980-06-15','2025-12-15',45,45) ('1980-06-15','2025-12-16',45,46)
--   ('2000-02-29','2025-02-28',25,25) ('2000-02-29','2025-08-28',25,25) ('2000-02-29','2025-08-29',25,26)
