-- 来店（1行＝1レシート）。cust_key を数えると客数になる
select receipt_id, date_key, store_id, cust_key
from {{ ref('int_customer_visit') }}
