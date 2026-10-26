-- 鮮度チェック：物価の最新月が、実行日から4か月より古ければ失敗（取り込みが止まっていないか）
select max(month) as last_month
from {{ ref('mart_indicators_monthly') }}
having max(month) < current_date - interval 4 month
