-- 売上を何月に数えるか（暦の月か、21日締めの会計月か）。ym は 202604 の形、mi は月の通し番号
select
    date_key,
{%- if var('month_basis') == 'cal' %}
    cal_ym as ym, cal_mi as mi
{%- elif var('month_basis') == 'fis' %}
    fis_ym as ym, fis_mi as mi
{%- else %}
    {{ exceptions.raise_compiler_error("month_basis は cal か fis") }}
{%- endif %}
from {{ ref('stg_calendar') }}
