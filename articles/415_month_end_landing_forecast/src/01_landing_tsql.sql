-- 415 月の途中の実績から、月末の着地を見込む（T-SQL。SQL Server 本体では動かしていません＝未検証。同じ形を DuckDB で実行して確かめました）
-- daily_sales(系列 nvarchar, 日付 date, 売上 int)。@d：見込みを出す時点（その月の何日までの実績を使うか）
DECLARE @d int = 10;

WITH m AS (
  SELECT 系列,
         YEAR(日付) * 100 + MONTH(日付)                         AS ym,
         DAY(EOMONTH(MIN(日付)))                               AS 月の日数,
         SUM(CAST(売上 AS bigint))                             AS 月の合計,
         SUM(CASE WHEN DAY(日付) <= @d THEN CAST(売上 AS bigint) ELSE 0 END) AS 途中までの実績
  FROM daily_sales
  GROUP BY 系列, YEAR(日付) * 100 + MONTH(日付)
)
SELECT a.系列, a.ym,
       -- ① 日割りで延ばす：途中までの実績 × 月の日数 ÷ 経過した日数
       a.途中までの実績 * a.月の日数 / CAST(@d AS float)                            AS 見込み_日割り,
       -- ② 前年同月の進み方で延ばす：途中までの実績 ÷（前年の同じ月の、同じ日までの割合）
       a.途中までの実績 / (CAST(p.途中までの実績 AS float) / NULLIF(p.月の合計, 0))    AS 見込み_前年同月の進み方
FROM m AS a
JOIN m AS p ON p.系列 = a.系列 AND p.ym = a.ym - 100;

-- 注意：当月の「月の合計」は、月の途中ではまだ途中までの値。上の a.月の合計 は、見込みには使わない
-- 注意：前年の同じ月と、曜日の並び・祝日の位置は同じではない。②はその分だけ外れる
