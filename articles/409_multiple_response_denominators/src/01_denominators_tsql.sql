-- 409 複数回答の設問：選択肢ごとの割合を、4つの分母で出す
-- T-SQL の書き方。SQL Server 本体では動かしていません（未検証）。同じ SQL を DuckDB で実行しています（src/a409_multiple_response.py）
-- respondents(回答者ID, 年齢, 状態)   状態は N'選んだ'・N'特になし'・N'無回答'
-- answers(回答者ID, 選択肢)           1人が、選んだ数だけ行を持つ

WITH d AS (
  SELECT COUNT(*)                                             AS n_all,     -- ① 回答者全体
         SUM(CASE WHEN 状態 <> N'無回答' THEN 1 ELSE 0 END)   AS n_valid,   -- ② 無回答を除く
         SUM(CASE WHEN 状態 = N'選んだ' THEN 1 ELSE 0 END)    AS n_sel      -- ③ 1つ以上選んだ人
  FROM dbo.respondents
), r AS (SELECT COUNT(*) AS n_resp FROM dbo.answers)                         -- ④ 回答の数
SELECT a.選択肢, COUNT(*) AS 選んだ人,
       100.0 * COUNT(*) / MAX(d.n_all)   AS pct_all,
       100.0 * COUNT(*) / MAX(d.n_valid) AS pct_valid,
       100.0 * COUNT(*) / MAX(d.n_sel)   AS pct_selected,
       100.0 * COUNT(*) / MAX(r.n_resp)  AS pct_responses
FROM dbo.answers AS a CROSS JOIN d CROSS JOIN r
GROUP BY a.選択肢;

-- よくある書き方：回答の表だけで分母を数える。1つも選ばなかった人（特になし・無回答）が分母から落ち、③と同じになる
SELECT 選択肢,
       100.0 * COUNT(*) / (SELECT COUNT(DISTINCT 回答者ID) FROM dbo.answers) AS pct
FROM dbo.answers
GROUP BY 選択肢;
