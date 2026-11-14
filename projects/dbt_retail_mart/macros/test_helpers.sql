{% macro is_base_config() -%}
{#- 答え合わせの期待値（seeds/expected_*）は、既定の vars と答え合わせ用データで作ったもの。
    force_golden を true にすると、vars を変えても期待値と比べる（定義を変えたら落ちることの確かめ用） -#}
{{ return(
    var('force_golden', false) or (
    var('dataset') == 'fixture_2751' and var('load_until') == 20991231 and var('month_basis') == 'cal'
    and var('bad_status') == ['cancel'] and not var('exclude_test_store') and var('amount_basis') == 'incl'
    and var('return_date_basis') == 'return' and var('comp_store_min_months') == 13
    and var('dept_group_version') == 'old' and var('customer_key') == 'receipt'
)) }}
{%- endmacro %}
