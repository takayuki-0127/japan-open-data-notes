-- 店別の NPS（推奨者 9〜10点の割合 − 批判者 0〜6点の割合、ポイント）（DuckDB で実行）
-- resp(n_per_store, store, score)
SELECT n_per_store, store,
       COUNT(*) AS n,
       100.0 * (AVG(CASE WHEN score >= 9 THEN 1.0 ELSE 0.0 END)
              - AVG(CASE WHEN score <= 6 THEN 1.0 ELSE 0.0 END)) AS nps
FROM resp
GROUP BY n_per_store, store
ORDER BY n_per_store, store;
