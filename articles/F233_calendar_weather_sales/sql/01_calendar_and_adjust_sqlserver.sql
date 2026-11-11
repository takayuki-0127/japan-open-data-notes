-- F233：カレンダーの表を作り、前年同月比からカレンダーの寄与を引く（SQL Server 用）
-- 前提：holidays(date) に祝日（振替休日・国民の休日を含む）、sales_monthly(ym, 値, 業態, 指標)、
--       calendar_coef(業態, 変数, 係数) を入れておく（同じフォルダの CSV を BULK INSERT などで取り込む）
-- 注：この作業環境には SQL Server がないため、同じ考え方の DuckDB 版（02_..._duckdb.sql）で数字を確かめた。

-- 1) 日の表（2011-01-01〜2027-12-31）
WITH d AS (
    SELECT CAST('2011-01-01' AS date) AS dt
    UNION ALL
    SELECT DATEADD(day, 1, dt) FROM d WHERE dt < '2027-12-31'
)
SELECT
    d.dt,
    (DATEDIFF(day, '19000101', d.dt) % 7)                        AS dow,      -- 0=月 … 6=日（1900-01-01 は月曜）
    CASE WHEN h.[date] IS NOT NULL THEN 1 ELSE 0 END             AS is_hol,
    CASE WHEN (DATEDIFF(day, '19000101', d.dt) % 7) >= 5
           OR h.[date] IS NOT NULL
           OR FORMAT(d.dt, 'MM-dd') IN ('12-31','01-01','01-02','01-03') THEN 1 ELSE 0 END AS is_off
INTO dim_day
FROM d LEFT JOIN holidays h ON h.[date] = d.dt
OPTION (MAXRECURSION 0);

-- 2) 3日以上続く休み（連休）の印：休みの日のかたまりごとに長さを数える（ギャップと島）
WITH g AS (
    SELECT dt, is_off,
           ROW_NUMBER() OVER (ORDER BY dt)
         - ROW_NUMBER() OVER (PARTITION BY is_off ORDER BY dt) AS grp
    FROM dim_day
), r AS (
    SELECT dt, is_off, COUNT(*) OVER (PARTITION BY is_off, grp) AS run_len FROM g
)
SELECT d.*, CASE WHEN r.is_off = 1 AND r.run_len >= 3 THEN 1 ELSE 0 END AS is_renkyu
INTO dim_day2
FROM dim_day d JOIN r ON r.dt = d.dt;

-- 3) 月の表（土曜・日曜（土曜の祝日を含む）・平日の祝日・連休の日数・月の日数）
SELECT
    FORMAT(dt, 'yyyy-MM') AS ym,
    COUNT(*)                                                     AS n_days,
    SUM(CASE WHEN dow = 5 AND is_hol = 0 THEN 1 ELSE 0 END)      AS n_sat,
    SUM(CASE WHEN dow = 6 OR (dow = 5 AND is_hol = 1) THEN 1 ELSE 0 END) AS n_sun,
    SUM(CASE WHEN is_hol = 1 AND dow < 5 THEN 1 ELSE 0 END)      AS n_hol_wd,
    SUM(is_renkyu)                                               AS n_renkyu
INTO dim_month
FROM dim_day2
GROUP BY FORMAT(dt, 'yyyy-MM');

-- 4) 前年同月との差 → 係数を掛けてカレンダーの寄与 → 前年同月比から引く
WITH m AS (
    SELECT ym, n_days, n_sat, n_sun, n_hol_wd, n_renkyu,
           LAG(n_days,  12) OVER (ORDER BY ym) AS p_days,
           LAG(n_sat,   12) OVER (ORDER BY ym) AS p_sat,
           LAG(n_sun,   12) OVER (ORDER BY ym) AS p_sun,
           LAG(n_hol_wd,12) OVER (ORDER BY ym) AS p_hol,
           LAG(n_renkyu,12) OVER (ORDER BY ym) AS p_ren
    FROM dim_month
), dm AS (
    SELECT ym, n_sat - p_sat AS d_n_sat, n_sun - p_sun AS d_n_sun, n_hol_wd - p_hol AS d_n_hol_wd,
           n_renkyu - p_ren AS d_n_renkyu, n_days - p_days AS d_n_days
    FROM m WHERE p_days IS NOT NULL
), cf AS (   -- 係数を横に並べる
    SELECT 業態,
           MAX(CASE WHEN 変数 = 'd_n_sat'    THEN 係数 END) AS b_sat,
           MAX(CASE WHEN 変数 = 'd_n_sun'    THEN 係数 END) AS b_sun,
           MAX(CASE WHEN 変数 = 'd_n_hol_wd' THEN 係数 END) AS b_hol,
           MAX(CASE WHEN 変数 = 'd_n_renkyu' THEN 係数 END) AS b_ren,
           MAX(CASE WHEN 変数 = 'd_n_days'   THEN 係数 END) AS b_days
    FROM calendar_coef GROUP BY 業態
), yoy AS (  -- 既存店はそのまま前年同月比、それ以外は販売額から作る（対数差×100）
    SELECT s.ym, s.業態,
           CASE WHEN s.指標 = '既存店' THEN 100 * LOG(s.値 / 100.0)
                ELSE 100 * LOG(s.値 / LAG(s.値, 12) OVER (PARTITION BY s.業態 ORDER BY s.ym)) END AS yoy
    FROM sales_monthly s
)
SELECT y.ym, y.業態, y.yoy,
       dm.d_n_sat*cf.b_sat + dm.d_n_sun*cf.b_sun + dm.d_n_hol_wd*cf.b_hol
     + dm.d_n_renkyu*cf.b_ren + dm.d_n_days*cf.b_days               AS calendar_contrib,
       y.yoy - (dm.d_n_sat*cf.b_sat + dm.d_n_sun*cf.b_sun + dm.d_n_hol_wd*cf.b_hol
     + dm.d_n_renkyu*cf.b_ren + dm.d_n_days*cf.b_days)              AS yoy_calendar_adjusted
FROM yoy y JOIN dm ON dm.ym = y.ym JOIN cf ON cf.業態 = y.業態
WHERE y.yoy IS NOT NULL
ORDER BY y.業態, y.ym;
