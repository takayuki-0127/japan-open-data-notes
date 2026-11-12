-- 412 月ごとの応当日を出す（T-SQL。SQL Server 本体では動かしていません＝未検証。同じ形を DuckDB で実行して確かめました）
-- contracts(契約ID, 始期 date)、 ks(n)：1〜12 の数の表

-- ① 始期に n か月を足す：その日がない月は月末に切り詰められ、ある月では元の日に戻る
SELECT c.契約ID, ks.n, DATEADD(month, ks.n, c.始期) AS 応当日
FROM contracts AS c CROSS JOIN ks;

-- ② 落とし穴：前の応当日に1か月ずつ足す。1/31 → 2/28 → 3/28 → 4/28 …と、一度切り詰められた日は戻らない
WITH chain AS (
  SELECT 契約ID, 1 AS n, DATEADD(month, 1, 始期) AS 応当日 FROM contracts
  UNION ALL
  SELECT 契約ID, n + 1, DATEADD(month, 1, 応当日) FROM chain WHERE n < 12
)
SELECT * FROM chain;

-- ③ 月末合わせ：始期が月の最終日なら、いつも月の最終日にする（2/28始期 → 3/31、4/30 …）
SELECT c.契約ID, ks.n,
       CASE WHEN c.始期 = EOMONTH(c.始期) THEN EOMONTH(DATEADD(month, ks.n, c.始期))
            ELSE DATEADD(month, ks.n, c.始期) END AS 応当日
FROM contracts AS c CROSS JOIN ks;

-- ④ 日数で決める：30日ごと（12回で360日。1年で5日早くなる）
SELECT c.契約ID, ks.n, DATEADD(day, 30 * ks.n, c.始期) AS 応当日
FROM contracts AS c CROSS JOIN ks;

-- 確かめる：①と②で日付が違う契約（1行も返らなければ、②の書き方でも同じ）
-- 始期が 29〜31 日の契約を必ずテストに入れる。うるう年の 1/29・1/30・1/31 と、2/28・2/29 も入れる
