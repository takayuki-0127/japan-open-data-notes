-- 462 2つの期間が重なるかどうかの条件（T-SQL 版）
-- ※ SQL Server 本体では動かしていません（未検証）。同じ条件を DuckDB で実行して確かめています（a462_overlap.py）。
-- 表：dbo.contracts(contract_id INT, start_date DATE, end_date DATE NULL)  … end_date が NULL は続行中
--     dbo.campaigns(campaign_id INT, start_date DATE, end_date DATE)
-- 期間は両端を含む（終了日もその期間の中）

-- 正しい条件：相手の終了日までに始まり、相手の開始日以降に終わる
SELECT c.contract_id, k.campaign_id
FROM dbo.contracts AS c
JOIN dbo.campaigns AS k
  ON c.start_date <= k.end_date
 AND ISNULL(c.end_date, '9999-12-31') >= k.start_date;

-- ① 開始日が期間の中かだけを見る（前から続いている契約が漏れる）
--   ON c.start_date BETWEEN k.start_date AND k.end_date
-- ② 開始日か終了日が期間の中（キャンペーンをすっぽり含む契約が漏れる）
--   ON (c.start_date BETWEEN k.start_date AND k.end_date)
--   OR (ISNULL(c.end_date, '9999-12-31') BETWEEN k.start_date AND k.end_date)
-- ③ 端を含めない（端が同じ日の組と、1日だけの期間が漏れる）
--   ON c.start_date < k.end_date AND ISNULL(c.end_date, '9999-12-31') > k.start_date
-- ④ 終了日の空を考えない（NULL との比べは真にならないので、続行中の契約が全部漏れる）
--   ON c.start_date <= k.end_date AND c.end_date >= k.start_date
-- ⑤ AND を OR にする（ほとんど全部の組が返る）
--   ON c.start_date <= k.end_date OR ISNULL(c.end_date, '9999-12-31') >= k.start_date
-- ⑥ キャンペーンの開始の時点で有効かだけを見る（期間の途中で始まった契約が漏れる）
--   ON c.start_date <= k.start_date AND ISNULL(c.end_date, '9999-12-31') >= k.start_date

-- 端の値を並べたテスト用の12組は、a462_overlap.py の hand にあります。
