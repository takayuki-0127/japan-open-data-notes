-- F240 前年比と「ほかの県の伸びで補正した前年」ベースライン（SQL Server 互換の書き方）
-- 入力テーブル lodging(pref NVARCHAR, ym INT, japanese BIGINT)  ※ ym = 年*12 + 月
-- 期間中：2025年4月〜10月（ym 24304〜24310）
WITH osaka AS (
    SELECT ym, CAST(japanese AS FLOAT) AS y
    FROM lodging WHERE pref = N'27大阪府'
),
others AS (
    -- 対照：大阪と関西の5府県（滋賀・京都・兵庫・奈良・和歌山）を除く41都道県の合計
    SELECT ym, SUM(CAST(japanese AS FLOAT)) AS y
    FROM lodging
    WHERE pref NOT IN (N'27大阪府', N'25滋賀県', N'26京都府', N'28兵庫県', N'29奈良県', N'30和歌山県')
    GROUP BY ym
),
monthly AS (
    SELECT o.ym,
           o.y                          AS osaka_now,
           o1.y                         AS osaka_prev,
           t.y                          AS others_now,
           t1.y                         AS others_prev,
           -- 前年同月 × ほかの県の前年比 ＝ 「万博がなければ」の素朴な見込み
           o1.y * (t.y / t1.y)          AS baseline
    FROM osaka o
    JOIN osaka  o1 ON o1.ym = o.ym - 12
    JOIN others t  ON t.ym  = o.ym
    JOIN others t1 ON t1.ym = o.ym - 12
    WHERE o.ym BETWEEN 24304 AND 24310
)
SELECT ym,
       osaka_now, osaka_prev, baseline,
       osaka_now / osaka_prev - 1.0       AS osaka_yoy,
       others_now / others_prev - 1.0     AS others_yoy,
       osaka_now / baseline - 1.0         AS eff_vs_baseline,
       osaka_now - baseline               AS persons_vs_baseline
FROM monthly
UNION ALL
SELECT 99999 AS ym,
       SUM(osaka_now), SUM(osaka_prev), SUM(baseline),
       SUM(osaka_now) / SUM(osaka_prev) - 1.0,
       SUM(others_now) / SUM(others_prev) - 1.0,
       SUM(osaka_now) / SUM(baseline) - 1.0,
       SUM(osaka_now) - SUM(baseline)
FROM monthly
ORDER BY ym;
