-- 「その他」の自由記述をキーワードで既存の選択肢に振り直す（DuckDB で実行）
-- survey(resp_id, choice, other_text)。CASE は上から順に当てるので、キーワードの順番が結果を左右する
SELECT resp_id,
       CASE WHEN choice <> 'その他' THEN choice
            WHEN regexp_matches(other_text, '安|値段|価格|セール')   THEN '価格'
            WHEN regexp_matches(other_text, '品質|丈夫|長持ち')      THEN '品質'
            WHEN regexp_matches(other_text, 'デザイン|色|見た目')    THEN 'デザイン'
            WHEN regexp_matches(other_text, '口コミ|レビュー|評判')  THEN '口コミ'
            WHEN regexp_matches(other_text, '店員|接客')             THEN '店員の対応'
            ELSE 'その他' END AS kw_label
FROM survey
ORDER BY resp_id;
