-- 基準日時点の未入金の請求を、2つの起算日で区分に分ける（T-SQL 版。SQL Server では動かしていない：未検証）
DECLARE @asof DATE = '2025-12-31';
WITH open_inv AS (
  SELECT i.*, DATEDIFF(DAY, i.invoice_date, @asof) AS days_from_invoice,
              DATEDIFF(DAY, i.due_date, @asof)     AS days_past_due
  FROM dbo.invoices AS i
  WHERE i.invoice_date <= @asof AND (i.paid_date IS NULL OR i.paid_date > @asof))
SELECT
  CASE WHEN days_from_invoice <= 30 THEN N'1_30日以内' WHEN days_from_invoice <= 60 THEN N'2_31〜60日'
       WHEN days_from_invoice <= 90 THEN N'3_61〜90日' ELSE N'4_90日超' END AS bucket_invoice,
  CASE WHEN days_past_due <= 0 THEN N'0_期日前' WHEN days_past_due <= 30 THEN N'1_30日以内' WHEN days_past_due <= 60 THEN N'2_31〜60日'
       WHEN days_past_due <= 90 THEN N'3_61〜90日' ELSE N'4_90日超' END AS bucket_due,
  COUNT(*) AS n, SUM(amount) AS amount
FROM open_inv
GROUP BY
  CASE WHEN days_from_invoice <= 30 THEN N'1_30日以内' WHEN days_from_invoice <= 60 THEN N'2_31〜60日'
       WHEN days_from_invoice <= 90 THEN N'3_61〜90日' ELSE N'4_90日超' END,
  CASE WHEN days_past_due <= 0 THEN N'0_期日前' WHEN days_past_due <= 30 THEN N'1_30日以内' WHEN days_past_due <= 60 THEN N'2_31〜60日'
       WHEN days_past_due <= 90 THEN N'3_61〜90日' ELSE N'4_90日超' END;
