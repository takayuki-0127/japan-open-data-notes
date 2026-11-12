-- 371：中央値・90%点を SQL で出す2つの関数（T-SQL。SQL Server 本体では動かしていない＝未検証）
-- PERCENTILE_CONT：順位 (n−1)×p+1 の位置を、前後の値で内分する（Hyndman & Fan の型7）
-- PERCENTILE_DISC：累積の割合が p 以上になる最初の値を、そのまま返す（型1）
-- SQL Server ではどちらもウィンドウ関数なので OVER () が要る。DISTINCT で1行にまとめる
SELECT DISTINCT
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY seconds) OVER () AS median_cont,
       PERCENTILE_DISC(0.5) WITHIN GROUP (ORDER BY seconds) OVER () AS median_disc,
       PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY seconds) OVER () AS p90_cont,
       PERCENTILE_DISC(0.9) WITHIN GROUP (ORDER BY seconds) OVER () AS p90_disc
FROM process_log;
