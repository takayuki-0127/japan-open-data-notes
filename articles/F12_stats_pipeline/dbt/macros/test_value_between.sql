{% test value_between(model, column_name, min_value, max_value) %}
-- 値の範囲チェック：範囲外の行があれば失敗
select * from {{ model }}
where {{ column_name }} is not null
  and ({{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }})
{% endtest %}
