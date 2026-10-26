select
    month,
    max(case when series = 'wage_total_idx'      then value end) as wage_total_idx,
    max(case when series = 'real_wage_total_idx' then value end) as real_wage_total_idx,
    max(case when series = 'wage_total_yoy'      then value end) as wage_total_yoy,
    max(case when series = 'real_wage_total_yoy' then value end) as real_wage_total_yoy,
    max(case when series = 'wage_scheduled_yoy'  then value end) as wage_scheduled_yoy
from {{ source('raw', 'raw_wage') }}
group by month
