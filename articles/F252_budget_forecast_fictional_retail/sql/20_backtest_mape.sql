-- 自社のバックテスト：1年分の合計の外れ（MAPE、%）を、単位・作り方・モデルごとに集計する。SQL Server 互換の書き方（DuckDB で実行）
-- 入力：backtest(seed, origin, level, unit, model, method, fc, act)
SELECT
    level,
    method,
    model,
    COUNT(*) AS n,
    100.0 * AVG(ABS(fc / act - 1.0)) AS mape_pct
FROM backtest
GROUP BY level, method, model
ORDER BY level, method, model;
