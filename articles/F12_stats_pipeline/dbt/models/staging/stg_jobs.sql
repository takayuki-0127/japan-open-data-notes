select
    month,
    max(case when series = 'jobs_ratio_sa'  then value end) as jobs_ratio_sa,
    max(case when series = 'jobs_ratio_nsa' then value end) as jobs_ratio_nsa
from {{ source('raw', 'raw_jobs') }}
group by month
