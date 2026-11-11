// F249 Power Query（M）。サンプルマート（架空）・合成データ。
// 使い方：「データの変換」→「新しいパラメーター」で DataFolder（テキスト。例 C:\work\F249\powerbi\data\ 、最後の \ を忘れない）を作り、
//         「新しいソース」→「空のクエリ」を表の数だけ作って、下の各ブロックを「詳細エディター」に貼る。クエリ名は // ==== の名前にする。
// .gz は Binary.Decompress で展開して読む。CSV は UTF-8（BOM つき）。日付は yyyy-mm-dd。

// ==== dim_date ====
let
    Source = Csv.Document ( File.Contents ( DataFolder & "dim_date.csv" ), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv] ),
    Promoted = Table.PromoteHeaders ( Source, [PromoteAllScalars = true] ),
    Typed = Table.TransformColumnTypes ( Promoted, {
        {"date", type date},
        {"year", Int64.Type},
        {"month", Int64.Type},
        {"ym", type text},
        {"month_start", type date},
        {"fy", Int64.Type},
        {"fy_label", type text},
        {"fy_month_no", Int64.Type},
        {"dow", Int64.Type},
        {"dow_name", type text},
        {"hol", Int64.Type},
        {"flyer", Int64.Type},
        {"day_weight", type number}
    }, "en-US" )
in
    Typed

// ==== dim_store ====
let
    Source = Csv.Document ( File.Contents ( DataFolder & "dim_store.csv" ), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv] ),
    Promoted = Table.PromoteHeaders ( Source, [PromoteAllScalars = true] ),
    Typed = Table.TransformColumnTypes ( Promoted, {
        {"store_id", Int64.Type},
        {"store_name", type text},
        {"area", type text},
        {"size", type text},
        {"open_date", type date},
        {"close_date", type date},
        {"area_order", Int64.Type}
    }, "en-US" )
in
    Typed

// ==== dim_category ====
let
    Source = Csv.Document ( File.Contents ( DataFolder & "dim_category.csv" ), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv] ),
    Promoted = Table.PromoteHeaders ( Source, [PromoteAllScalars = true] ),
    Typed = Table.TransformColumnTypes ( Promoted, {
        {"category_id", Int64.Type},
        {"category", type text},
        {"margin", type number},
        {"waste", type number},
        {"promo", Int64.Type}
    }, "en-US" )
in
    Typed

// ==== fact_store_day ====
let
    Source = Csv.Document ( Binary.Decompress ( File.Contents ( DataFolder & "fact_store_day.csv.gz" ), Compression.GZip ), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv] ),
    Promoted = Table.PromoteHeaders ( Source, [PromoteAllScalars = true] ),
    Typed = Table.TransformColumnTypes ( Promoted, {
        {"biz_date", type date},
        {"store_id", Int64.Type},
        {"receipts", Int64.Type},
        {"member_receipts", Int64.Type},
        {"items", Int64.Type},
        {"sales", type number},
        {"gross_profit_before_waste", type number},
        {"waste", type number},
        {"gross_profit", type number},
        {"labor_hours", type number},
        {"labor_cost", type number},
        {"labor_imputed", Int64.Type}
    }, "en-US" )
in
    Typed

// ==== fact_store_day_category ====
let
    Source = Csv.Document ( Binary.Decompress ( File.Contents ( DataFolder & "fact_store_day_category.csv.gz" ), Compression.GZip ), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv] ),
    Promoted = Table.PromoteHeaders ( Source, [PromoteAllScalars = true] ),
    Typed = Table.TransformColumnTypes ( Promoted, {
        {"biz_date", type date},
        {"store_id", Int64.Type},
        {"category_id", Int64.Type},
        {"sales", type number},
        {"gross_profit_before_waste", type number},
        {"waste", type number}
    }, "en-US" )
in
    Typed

// ==== fact_store_month ====
let
    Source = Csv.Document ( File.Contents ( DataFolder & "fact_store_month.csv" ), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv] ),
    Promoted = Table.PromoteHeaders ( Source, [PromoteAllScalars = true] ),
    Typed = Table.TransformColumnTypes ( Promoted, {
        {"month_start", type date},
        {"store_id", Int64.Type},
        {"other_cost", type number},
        {"is_existing", Int64.Type},
        {"labor_imputed_days", Int64.Type},
        {"days_with_sales", Int64.Type}
    }, "en-US" )
in
    Typed

// ==== fact_member_month ====
let
    Source = Csv.Document ( File.Contents ( DataFolder & "fact_member_month.csv" ), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv] ),
    Promoted = Table.PromoteHeaders ( Source, [PromoteAllScalars = true] ),
    Typed = Table.TransformColumnTypes ( Promoted, {
        {"month_start", type date},
        {"store_id", Int64.Type},
        {"active_members", Int64.Type},
        {"member_receipts", Int64.Type}
    }, "en-US" )
in
    Typed

// ==== ref_noise_band ====
let
    Source = Csv.Document ( File.Contents ( DataFolder & "ref_noise_band.csv" ), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv] ),
    Promoted = Table.PromoteHeaders ( Source, [PromoteAllScalars = true] ),
    Typed = Table.TransformColumnTypes ( Promoted, {
        {"level", type text},
        {"grain", type text},
        {"KPI", type text},
        {"band", type number},
        {"unit", type text},
        {"band_ratio", type number}
    }, "en-US" )
in
    Typed

// ==== sec_user_area ====
let
    Source = Csv.Document ( File.Contents ( DataFolder & "sec_user_area.csv" ), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv] ),
    Promoted = Table.PromoteHeaders ( Source, [PromoteAllScalars = true] ),
    Typed = Table.TransformColumnTypes ( Promoted, {
        {"user_principal", type text},
        {"area", type text}
    }, "en-US" )
in
    Typed
