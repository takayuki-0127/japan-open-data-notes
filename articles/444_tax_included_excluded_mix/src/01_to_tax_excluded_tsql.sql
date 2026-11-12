-- 444 税込みと税抜きが混ざった金額を、税抜きにそろえる（T-SQL 版。SQL Server 本体では未検証。同じ考え方の SQL を DuckDB で実行して確かめた）
-- txn(txn_id INT, txn_date DATE, category NVARCHAR(10), amount INT, tax_type NVARCHAR(2) NULL)
--   tax_type は '込'・'抜'・NULL（分からない）。category が '食品' の行は軽減税率
WITH r AS (
  SELECT t.*,
         CASE WHEN txn_date < '2019-10-01' THEN 0.08
              WHEN category = N'食品'      THEN 0.08
              ELSE 0.10 END AS rate
  FROM txn t
)
SELECT txn_id, txn_date, category, amount, tax_type, rate,
       -- ② 税の列がある行だけ戻す（NULL は税抜きとみなす）
       CASE WHEN tax_type = N'込' THEN CEILING(amount / (1 + rate) - 0.0000001) ELSE amount END AS excl_by_flag,
       -- ③ 列が NULL の行は、端数から推し量る（10円の倍数でなければ税込みとみなす）
       CASE WHEN tax_type = N'込' OR (tax_type IS NULL AND amount % 10 <> 0)
            THEN CEILING(amount / (1 + rate) - 0.0000001) ELSE amount END AS excl_by_guess
FROM r;
