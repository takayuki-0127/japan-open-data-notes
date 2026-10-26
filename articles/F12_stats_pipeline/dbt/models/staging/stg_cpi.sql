-- 消費者物価指数を横持ちにする（1か月1行）
select
    month,
    max(case when series = 'cpi_all'       then value end) as cpi_all,
    max(case when series = 'cpi_core'      then value end) as cpi_core,
    max(case when series = 'cpi_core_core' then value end) as cpi_core_core,
    max(case when series = 'cpi_ex_rent'   then value end) as cpi_ex_rent,
    max(case when series = 'cpi_food'      then value end) as cpi_food,
    max(case when series = 'cpi_energy'    then value end) as cpi_energy
from {{ source('raw', 'raw_cpi') }}
group by month
