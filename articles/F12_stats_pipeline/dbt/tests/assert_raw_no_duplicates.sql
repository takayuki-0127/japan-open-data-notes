-- 生データで「同じ月・同じ系列」が2行以上ないか。
-- stg は group by で横持ちにするので、重複があっても max() で潰れて見えなくなる。そのため raw の段階で確かめる
{% for t in ['raw_cpi', 'raw_lfs', 'raw_jobs', 'raw_wage'] %}
select '{{ t }}' as tbl, month, series, count(*) as n
from {{ source('raw', t) }}
group by month, series
having count(*) > 1
{% if not loop.last %}union all{% endif %}
{% endfor %}
