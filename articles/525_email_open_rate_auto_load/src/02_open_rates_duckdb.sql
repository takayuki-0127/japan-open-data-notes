-- 開封の数え方を変えて開封率（%）を出す（DuckDB で実行）
-- sends(id, variant, auto_device, read_by_person, first_open_min, clicked)
-- first_open_min：配信から最初に開封が記録されるまでの分（記録がなければ NULL）
SELECT
    100.0 * AVG(CASE WHEN first_open_min IS NOT NULL THEN 1 ELSE 0 END)                         AS all_opens,
    100.0 * AVG(CASE WHEN first_open_min > 5 THEN 1 ELSE 0 END)                                AS excl_quick,
    100.0 * AVG(CASE WHEN clicked THEN 1 ELSE 0 END)                                           AS clickers,
    100.0 * AVG(CASE WHEN first_open_min > 5 OR clicked THEN 1 ELSE 0 END)                     AS excl_quick_or_click,
    100.0 * AVG(CASE WHEN first_open_min IS NOT NULL THEN 1 ELSE 0 END) FILTER (WHERE NOT auto_device) AS non_auto_only
FROM sends;
