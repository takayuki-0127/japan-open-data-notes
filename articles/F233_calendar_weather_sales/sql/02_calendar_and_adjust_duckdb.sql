-- 01_calendar_and_adjust_sqlserver.sql と同じ計算を DuckDB で行い、Python の結果と照合する
CREATE TABLE holidays AS SELECT CAST(date AS DATE) AS date FROM read_csv_auto('sql/holidays.csv');
CREATE TABLE sales_monthly AS SELECT * FROM read_csv_auto('sql/sales_monthly.csv');
CREATE TABLE calendar_coef AS SELECT * FROM read_csv_auto('sql/calendar_coef.csv');
CREATE TABLE dim_day AS
WITH RECURSIVE d(dt) AS (SELECT DATE '2011-01-01' UNION ALL SELECT CAST(dt + INTERVAL 1 DAY AS DATE) FROM d WHERE dt < DATE '2027-12-31')
SELECT d.dt, (isodow(d.dt) - 1) AS dow, CASE WHEN h.date IS NOT NULL THEN 1 ELSE 0 END AS is_hol,
       CASE WHEN isodow(d.dt) >= 6 OR h.date IS NOT NULL OR strftime(d.dt, '%m-%d') IN ('12-31','01-01','01-02','01-03') THEN 1 ELSE 0 END AS is_off
FROM d LEFT JOIN holidays h ON h.date = d.dt;
CREATE TABLE dim_day2 AS
WITH g AS (SELECT dt, is_off, ROW_NUMBER() OVER (ORDER BY dt) - ROW_NUMBER() OVER (PARTITION BY is_off ORDER BY dt) AS grp FROM dim_day),
     r AS (SELECT dt, is_off, COUNT(*) OVER (PARTITION BY is_off, grp) AS run_len FROM g)
SELECT d.*, CASE WHEN r.is_off = 1 AND r.run_len >= 3 THEN 1 ELSE 0 END AS is_renkyu FROM dim_day d JOIN r ON r.dt = d.dt;
CREATE TABLE dim_month AS
SELECT strftime(dt, '%Y-%m') AS ym, COUNT(*) AS n_days,
       SUM(CASE WHEN dow = 5 AND is_hol = 0 THEN 1 ELSE 0 END) AS n_sat,
       SUM(CASE WHEN dow = 6 OR (dow = 5 AND is_hol = 1) THEN 1 ELSE 0 END) AS n_sun,
       SUM(CASE WHEN is_hol = 1 AND dow < 5 THEN 1 ELSE 0 END) AS n_hol_wd, SUM(is_renkyu) AS n_renkyu
FROM dim_day2 GROUP BY 1;
COPY (SELECT * FROM dim_month ORDER BY ym) TO 'results/H_sql_dim_month.csv' (HEADER);
COPY (
WITH m AS (SELECT *, LAG(n_days,12) OVER (ORDER BY ym) p_days, LAG(n_sat,12) OVER (ORDER BY ym) p_sat, LAG(n_sun,12) OVER (ORDER BY ym) p_sun,
                     LAG(n_hol_wd,12) OVER (ORDER BY ym) p_hol, LAG(n_renkyu,12) OVER (ORDER BY ym) p_ren FROM dim_month),
dm AS (SELECT ym, n_sat-p_sat d_n_sat, n_sun-p_sun d_n_sun, n_hol_wd-p_hol d_n_hol_wd, n_renkyu-p_ren d_n_renkyu, n_days-p_days d_n_days FROM m WHERE p_days IS NOT NULL),
cf AS (SELECT 業態, MAX(CASE WHEN 変数='d_n_sat' THEN 係数 END) b_sat, MAX(CASE WHEN 変数='d_n_sun' THEN 係数 END) b_sun,
              MAX(CASE WHEN 変数='d_n_hol_wd' THEN 係数 END) b_hol, MAX(CASE WHEN 変数='d_n_renkyu' THEN 係数 END) b_ren,
              MAX(CASE WHEN 変数='d_n_days' THEN 係数 END) b_days FROM calendar_coef GROUP BY 業態),
yoy AS (SELECT ym, 業態, CASE WHEN 指標='既存店' THEN 100*ln(値/100.0) ELSE 100*ln(値/LAG(値,12) OVER (PARTITION BY 業態 ORDER BY ym)) END yoy FROM sales_monthly)
SELECT y.ym, y.業態, y.yoy,
       dm.d_n_sat*cf.b_sat + dm.d_n_sun*cf.b_sun + dm.d_n_hol_wd*cf.b_hol + dm.d_n_renkyu*cf.b_ren + dm.d_n_days*cf.b_days AS calendar_contrib,
       y.yoy - (dm.d_n_sat*cf.b_sat + dm.d_n_sun*cf.b_sun + dm.d_n_hol_wd*cf.b_hol + dm.d_n_renkyu*cf.b_ren + dm.d_n_days*cf.b_days) AS yoy_calendar_adjusted
FROM yoy y JOIN dm ON dm.ym=y.ym JOIN cf ON cf.業態=y.業態 WHERE y.yoy IS NOT NULL ORDER BY y.業態, y.ym
) TO 'results/H_sql_adjusted.csv' (HEADER);
