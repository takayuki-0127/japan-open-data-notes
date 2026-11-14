-- 売上と返品を1つの列（amt）にそろえる。返品はマイナス。計上日 date_key は vars の return_date_basis で決まる
select
    o.receipt_id, o.line_no, 'sale' as kind,
    o.date_key, o.store_id, o.item_id,
    o.amount_incl * o.amt_factor as amt
from {{ ref('int_sales_line_valid') }} o
union all
select
    o.receipt_id, o.line_no, 'return' as kind,
{%- if var('return_date_basis') == 'return' %}
    r.return_date_key as date_key,
{%- elif var('return_date_basis') == 'sale' %}
    o.date_key as date_key,
{%- else %}
    {{ exceptions.raise_compiler_error("return_date_basis は return か sale") }}
{%- endif %}
    o.store_id, o.item_id,
    -r.amount_incl * o.amt_factor as amt
from {{ ref('stg_returns_line') }} r
join {{ ref('int_sales_line_valid') }} o
  on o.receipt_id = r.receipt_id and o.line_no = r.line_no
