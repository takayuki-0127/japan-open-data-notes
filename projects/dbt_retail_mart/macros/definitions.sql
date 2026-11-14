{#- 業務の定義をまとめたマクロ。値は dbt_project.yml の vars で切り替える -#}

{% macro dept_group(dept_col) -%}
{%- if var('dept_group_version') == 'old' -%}
    case
        when {{ dept_col }} in (1, 2) then '生鮮'
        when {{ dept_col }} in (3, 4) then '加工食品'
        when {{ dept_col }} in (5) then '日配'
        when {{ dept_col }} in (6, 7) then '日用品'
        else 'その他'
    end
{%- elif var('dept_group_version') == 'new' -%}
    case
        when {{ dept_col }} in (1, 2, 5) then '生鮮・日配'
        when {{ dept_col }} in (3, 4) then '加工食品'
        when {{ dept_col }} in (6, 7, 8) then '日用品'
        else 'その他'
    end
{%- else -%}
    {{ exceptions.raise_compiler_error("dept_group_version は old か new: " ~ var('dept_group_version')) }}
{%- endif -%}
{%- endmacro %}

{% macro amount_factor(tax_col) -%}
{%- if var('amount_basis') == 'incl' -%} 1.0
{%- elif var('amount_basis') == 'excl' -%} 100.0 / (100 + {{ tax_col }})
{%- else -%}{{ exceptions.raise_compiler_error("amount_basis は incl か excl") }}
{%- endif -%}
{%- endmacro %}

{% macro date_key_minus_days(date_key_expr, days) -%}
    cast(strftime(strptime(cast({{ date_key_expr }} as varchar), '%Y%m%d') - interval {{ days }} day, '%Y%m%d') as integer)
{%- endmacro %}
