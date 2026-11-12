-- 414 「期首＋増加−減少＝期末」の照合（T-SQL。SQL Server 本体では動かしていません＝未検証。同じ形を DuckDB で実行して確かめました）
-- movements(月 int, 契約ID int, 種類 nvarchar, 金額 int)：種類は 新規・復活・解約・満期・中途変更。中途変更の金額は増減
-- snapshots(月 int, 契約ID int, 保険料 int)：その月末に有効な契約の一覧

-- 件数と保険料の照合：差が 0 でない月を返す（1行も返らなければ合格）
WITH mv AS (
  SELECT 月,
         SUM(CASE WHEN 種類 = N'新規' THEN 1 ELSE 0 END) AS 新規,
         SUM(CASE WHEN 種類 = N'復活' THEN 1 ELSE 0 END) AS 復活,
         SUM(CASE WHEN 種類 = N'解約' THEN 1 ELSE 0 END) AS 解約,
         SUM(CASE WHEN 種類 = N'満期' THEN 1 ELSE 0 END) AS 満期,
         SUM(CASE WHEN 種類 IN (N'新規', N'復活') THEN 金額
                  WHEN 種類 IN (N'解約', N'満期') THEN -金額
                  ELSE 金額 END) AS 保険料の増減
  FROM movements GROUP BY 月
),
st AS (SELECT 月, COUNT(*) AS 件数, SUM(CAST(保険料 AS bigint)) AS 保険料 FROM snapshots GROUP BY 月)
SELECT mv.月,
       b.件数 + mv.新規 + mv.復活 - mv.解約 - mv.満期 - t.件数 AS 件数の差,
       b.保険料 + mv.保険料の増減 - t.保険料               AS 保険料の差
FROM mv
JOIN st AS b ON b.月 = mv.月 - 1
JOIN st AS t ON t.月 = mv.月
WHERE b.件数 + mv.新規 + mv.復活 - mv.解約 - mv.満期 <> t.件数
   OR b.保険料 + mv.保険料の増減 <> t.保険料;

-- 契約ごとの照合：期首の一覧に異動を足したものが、期末の一覧と契約ごとに合うか（1行も返らなければ合格）
WITH ev AS (
  SELECT 月, 契約ID,
         SUM(CASE WHEN 種類 IN (N'新規', N'復活') THEN 1 WHEN 種類 IN (N'解約', N'満期') THEN -1 ELSE 0 END) AS 件数の増減,
         SUM(CASE WHEN 種類 IN (N'解約', N'満期') THEN -金額 ELSE 金額 END) AS 保険料の増減
  FROM movements GROUP BY 月, 契約ID
),
k AS (   -- その月に関係する契約：期首にある、期末にある、異動がある
  SELECT 月 + 1 AS 月, 契約ID FROM snapshots
  UNION SELECT 月, 契約ID FROM snapshots
  UNION SELECT 月, 契約ID FROM ev
)
SELECT k.月, k.契約ID
FROM k
LEFT JOIN snapshots AS b ON b.月 = k.月 - 1 AND b.契約ID = k.契約ID
LEFT JOIN snapshots AS t ON t.月 = k.月     AND t.契約ID = k.契約ID
LEFT JOIN ev              ON ev.月 = k.月    AND ev.契約ID = k.契約ID
WHERE k.月 BETWEEN 1 AND 24
  AND ( (CASE WHEN b.契約ID IS NULL THEN 0 ELSE 1 END) + COALESCE(ev.件数の増減, 0) <> (CASE WHEN t.契約ID IS NULL THEN 0 ELSE 1 END)
     OR COALESCE(b.保険料, 0) + COALESCE(ev.保険料の増減, 0) <> COALESCE(t.保険料, 0) );

-- 注意：種類の書き間違い（解約を満期と書く、復活を新規と書く）は、上のどちらの照合でも見つからない
