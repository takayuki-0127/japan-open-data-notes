{{ config(
    materialized='incremental',
    unique_key=['date_key', 'store_id'],
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}
-- 日×店の正味売上（増分で積み上げる）。返品は売上から最大10日後に来るので、
-- 増分の回では直近 incremental_lookback_days 日を読み直して置き換える。
-- 注意：vars の定義（ステータス・税・返品の計上日など）を変えたときは、過去の日も変わるので --full-refresh が要る
select date_key, store_id, sum(amt) as sales, count(*) as n_rows
from {{ ref('fct_sales_net') }}
{% if is_incremental() %}
where date_key >= (select {{ date_key_minus_days('max(date_key)', var('incremental_lookback_days')) }} from {{ this }})
{% endif %}
group by date_key, store_id
