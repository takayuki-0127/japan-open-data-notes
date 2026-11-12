-- M01
SELECT COALESCE(SUM(amount),0) FROM f WHERE year=2025 AND region='関東' AND category='日用品';
-- M02
SELECT COALESCE(SUM(amount),0) FROM f WHERE year=2025 AND region='関東' AND category='食品';
-- M03
SELECT COALESCE(SUM(amount),0) FROM f WHERE year=2025 AND region='関東' AND category='日用品' AND category='食品';
-- M04
SELECT COALESCE(SUM(amount),0) FROM f WHERE year=2025 AND region='関西' AND category='日用品';
-- M05
SELECT COALESCE(SUM(amount),0) FROM f WHERE year=2024 AND region='関東' AND category='日用品';
-- M06
SELECT COALESCE(SUM(amount),0) FROM f WHERE year=2025 AND region='関東';
-- M07
SELECT ROUND(SUM(CASE WHEN category='日用品' THEN amount END)*1.0/SUM(amount),4) FROM f WHERE year=2025 AND region='関東';
-- M08
SELECT SUM(amount) FROM f;
-- M09
SELECT COALESCE(SUM(amount),0) FROM f WHERE year=2025 AND region='関東' AND category='日用品' AND amount>20000;
-- M10
SELECT COALESCE(SUM(amount),0) FROM f WHERE year=2025 AND store='S02' AND region='関西' AND category='日用品';
-- M11
SELECT CAST(ROUND(AVG(s)) AS BIGINT) FROM (SELECT store, SUM(amount) s FROM f WHERE year=2025 AND region='関東' AND category='日用品' GROUP BY store);
-- M12
SELECT COALESCE(SUM(amount),0) FROM f WHERE year=2025 AND region='関東' AND category='日用品';
