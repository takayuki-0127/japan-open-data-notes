-- 「ある月の売上」を出す9つの書き方。T-SQL の書き方。DuckDB で実行して確かめた（SQL Server 本体では未検証）
-- {M0}＝月の初日、{ML}＝月の最終日、{M1}＝翌月の初日。ts_jst は日本時間の日時、ts_utc は UTC の日時
-- name: W1_BETWEEN 初日 AND 最終日
SELECT COUNT(*) AS n, SUM(amount) AS total FROM dbo.tx
WHERE ts_jst BETWEEN '{M0}' AND '{ML}';

-- name: W2_BETWEEN 初日 AND 最終日 23:59:59
SELECT COUNT(*) AS n, SUM(amount) AS total FROM dbo.tx
WHERE ts_jst BETWEEN '{M0}' AND '{ML} 23:59:59';

-- name: W3_BETWEEN 初日 AND 翌月の初日
SELECT COUNT(*) AS n, SUM(amount) AS total FROM dbo.tx
WHERE ts_jst BETWEEN '{M0}' AND '{M1}';

-- name: W4_最終日を EOMONTH で出して <=
SELECT COUNT(*) AS n, SUM(amount) AS total FROM dbo.tx
WHERE ts_jst >= '{M0}' AND ts_jst <= EOMONTH('{M0}');

-- name: W5_半開区間（>= 初日 AND < 翌月の初日）
SELECT COUNT(*) AS n, SUM(amount) AS total FROM dbo.tx
WHERE ts_jst >= '{M0}' AND ts_jst < '{M1}';

-- name: W6_日付に直してから BETWEEN
SELECT COUNT(*) AS n, SUM(amount) AS total FROM dbo.tx
WHERE CAST(ts_jst AS DATE) BETWEEN '{M0}' AND '{ML}';

-- name: W7_YEAR と MONTH で絞る
SELECT COUNT(*) AS n, SUM(amount) AS total FROM dbo.tx
WHERE YEAR(ts_jst) = YEAR(CAST('{M0}' AS DATE)) AND MONTH(ts_jst) = MONTH(CAST('{M0}' AS DATE));

-- name: W8_半開区間を UTC の列にそのまま当てる
SELECT COUNT(*) AS n, SUM(amount) AS total FROM dbo.tx
WHERE ts_utc >= '{M0}' AND ts_utc < '{M1}';

-- name: W9_UTC の列を日本時間に直してから半開区間
SELECT COUNT(*) AS n, SUM(amount) AS total FROM dbo.tx
WHERE DATEADD(hour, 9, ts_utc) >= '{M0}' AND DATEADD(hour, 9, ts_utc) < '{M1}';
