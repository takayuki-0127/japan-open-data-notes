-- 簡便式の材料を、会員の月次の表から出す（DuckDB 版）
-- member_month(member_id, ym, joined_ym, active, churned_this_month, spend)
-- 直近の月（2025-12）の、在籍している会員1人あたりの月の購入額と、その月の退会率
SELECT AVG(spend) AS arpu,
       AVG(CASE WHEN churned_this_month THEN 1.0 ELSE 0.0 END) AS churn
FROM member_month
WHERE ym = DATE '2025-12-01' AND active;
-- 入会から12か月の会員だけで出した、1か月あたりの購入額と退会率
SELECT AVG(spend) AS arpu_new,
       AVG(CASE WHEN churned_this_month THEN 1.0 ELSE 0.0 END) AS churn_new
FROM member_month
WHERE active AND date_diff('month', joined_ym, ym) < 12;
