-- 売上として数える明細（定義は models/docs.md の def_valid_line）
select
    l.receipt_id, l.line_no, l.date_key, l.store_id, l.item_id, l.amount_incl, l.tax_pct, l.status,
    {{ amount_factor('l.tax_pct') }} as amt_factor
from {{ ref('stg_sales_line') }} l
join {{ ref('stg_store') }} s on s.store_id = l.store_id
where l.status not in ({% for st in var('bad_status') %}'{{ st }}'{% if not loop.last %}, {% endif %}{% endfor %})
{%- if var('exclude_test_store') %}
  and not s.is_test
{%- endif %}
