-- 日付の次元。ym・mi は vars の month_basis（暦の月／会計月）に従う
select
    c.date_key,
    strptime(cast(c.date_key as varchar), '%Y%m%d')::date as calendar_date,
    c.cal_ym, c.fis_ym,
    m.ym, m.mi,
    dayofweek(strptime(cast(c.date_key as varchar), '%Y%m%d')) in (0, 6) as is_weekend
from {{ ref('stg_calendar') }} c
join {{ ref('int_month') }} m on m.date_key = c.date_key
