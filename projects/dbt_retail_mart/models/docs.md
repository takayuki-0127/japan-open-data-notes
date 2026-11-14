{% docs def_valid_line %}
売上として数える明細。ステータスが vars の `bad_status`（既定は cancel）のものを除く。
`exclude_test_store` が true のときはテスト店（store.is_test）の明細も除く。
金額は `amount_basis` が incl なら税込みのまま、excl なら 100 / (100 + 税率) を掛けて税抜きにする。
{% enddocs %}

{% docs def_net_sales %}
正味の売上。売上の明細に、返品をマイナスの金額で足したもの。
返品は、売上として数える明細に対応するものだけを数える（キャンセルした明細の返品は数えない）。
返品をどの日に数えるかは `return_date_basis`（return＝返品した日、sale＝元の売上日）。
{% enddocs %}

{% docs def_comp_store %}
既存店。開店した月の通し番号 open_mi が、その月の通し番号 mi より `comp_store_min_months`（既定 13）以上前の店。
既存店の前年比は、既存店のうち前年同月の売上がある店だけで比べる。
{% enddocs %}

{% docs def_customer %}
客数。`customer_key` が receipt ならレシート1枚を1人と数える。
member_day なら、同じ会員の同じ日の来店は1人とし、会員 ID がないレシートは1枚を1人とする。
売上として数える明細が1行もないレシート（キャンセルだけのレシートなど）は数えない。
{% enddocs %}

{% docs def_month %}
月。`month_basis` が cal なら暦の月、fis なら21日締めの会計月（21日以降は翌月に数える）。
{% enddocs %}
