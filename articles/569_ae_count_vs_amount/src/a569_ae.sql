-- 実績と予定の比（A/E）を、件数と保険金額の2通りで出す（DuckDB）
-- 入力 policies(age, sum_insured, q_expected, death)。death は 1=死亡、0=生存
SELECT
  SUM(death)                                   AS deaths,
  SUM(q_expected)                              AS expected_count,
  SUM(death) / SUM(q_expected)                 AS ae_count,
  SUM(sum_insured * death) / SUM(sum_insured * q_expected) AS ae_amount,
  -- 95% 区間の半分の幅（正規近似）
  1.96 * SQRT(SUM(q_expected * (1 - q_expected))) / SUM(q_expected) AS half_count,
  1.96 * SQRT(SUM(sum_insured * sum_insured * q_expected * (1 - q_expected)))
       / SUM(sum_insured * q_expected)         AS half_amount
FROM policies;
