-- 集計をストアドプロシージャにまとめた形（T-SQL。SQL Server 本体では試していない＝未検証）
CREATE OR ALTER PROCEDURE dbo.sp_sales_summary
    @store_code VARCHAR(50), @date_from DATE, @date_to DATE  -- 日付は DATE 型で受け取る（'2025-02-31' は呼び出しの時点で変換エラー）
    -- 店コードを VARCHAR(4) で受けると、長すぎる文字は黙って4文字に切り詰められる。なので広めに受けて長さを検査する
AS
BEGIN
    SET NOCOUNT ON;
    IF @store_code IS NULL OR @date_from IS NULL OR @date_to IS NULL
        THROW 50001, N'店コードと期間は必須です', 1;
    IF LEN(@store_code) <> 4
        THROW 50004, N'店コードは4文字です', 1;
    IF @date_from > @date_to
        THROW 50002, N'期間の始まりが終わりより後です', 1;
    IF NOT EXISTS (SELECT 1 FROM dbo.stores WHERE store_code = @store_code)
        THROW 50003, N'存在しない店コードです', 1;
    SELECT COUNT(*) AS orders, SUM(amount) AS sales
    FROM dbo.orders
    WHERE store_code = @store_code
      AND order_date >= @date_from AND order_date < DATEADD(day, 1, @date_to)
      AND status = N'完了';
END;
-- 呼び出し側：EXEC dbo.sp_sales_summary @store_code = 'S017', @date_from = '2025-04-01', @date_to = '2025-04-30';
