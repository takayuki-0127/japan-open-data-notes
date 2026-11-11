-- 02 照合用の列を作る（T-SQL。DuckDB では SELECT … INTO を CREATE TABLE … AS に置き換えて検証）
-- 名前：半角・全角の空白を取る／電話：ハイフンと空白を取る／メール：小文字に
SELECT customer_id, person_id, name, birth, tel, email, dup_type, updated_at,
       REPLACE(REPLACE(name, ' ', ''), N'　', '')  AS name_n,
       REPLACE(REPLACE(tel, '-', ''), ' ', '')     AS tel_n,
       LOWER(email)                                AS email_n
INTO dbo.c_norm
FROM dbo.customers;
