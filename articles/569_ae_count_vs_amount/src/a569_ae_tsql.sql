-- 件数と保険金額の A/E（T-SQL 版。SQL Server では動かしていない：未検証）
-- 入力 dbo.policies(age INT, sum_insured FLOAT, q_expected FLOAT, death INT)
SELECT
  SUM(death) AS deaths,
  SUM(q_expected) AS expected_count,
  SUM(CAST(death AS FLOAT)) / SUM(q_expected) AS ae_count,
  SUM(sum_insured * death) / SUM(sum_insured * q_expected) AS ae_amount,
  1.96 * SQRT(SUM(q_expected * (1 - q_expected))) / SUM(q_expected) AS half_count,
  1.96 * SQRT(SUM(sum_insured * sum_insured * q_expected * (1 - q_expected)))
       / SUM(sum_insured * q_expected) AS half_amount
FROM dbo.policies;
