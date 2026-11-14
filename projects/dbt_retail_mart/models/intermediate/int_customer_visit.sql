-- 客数の数え方（定義は models/docs.md の def_customer）。売上として数える明細が1行もないレシートは数えない
select
    r.receipt_id, r.date_key, r.store_id, r.member_id,
{%- if var('customer_key') == 'receipt' %}
    r.receipt_id as cust_key
{%- elif var('customer_key') == 'member_day' %}
    coalesce(r.member_id * 100000000 + r.date_key, -r.receipt_id) as cust_key
{%- else %}
    {{ exceptions.raise_compiler_error("customer_key は receipt か member_day") }}
{%- endif %}
from {{ ref('stg_receipt') }} r
where exists (select 1 from {{ ref('int_sales_line_valid') }} o where o.receipt_id = r.receipt_id)
