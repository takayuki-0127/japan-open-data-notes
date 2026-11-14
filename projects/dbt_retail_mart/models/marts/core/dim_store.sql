-- 店の次元。open_mi は開店した月の通し番号（既存店の判定に使う）
select s.store_id, s.open_date_key, m.mi as open_mi, s.is_test
from {{ ref('stg_store') }} s
join {{ ref('int_month') }} m on m.date_key = s.open_date_key
