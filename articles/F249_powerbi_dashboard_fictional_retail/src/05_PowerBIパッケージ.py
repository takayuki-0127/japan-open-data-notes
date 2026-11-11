"""05 Power BI パッケージ：measures.dax（DAX クエリビューに貼る DEFINE ブロック）、measures.md（期待値つき）、
powerquery.m、theme.json、期待値の表を powerbi/ に書き出す。layout_spec.md・rls.md・build_steps.md は手で書いたもの。

- 会社・数字は架空（サンプルマート（架空）、合成データ）。
- DAX は Power BI Desktop では動かしていない（この環境では Power BI Desktop を動かせないため）。
  期待値は src/03_分析.py が pandas と SQL の2通りで計算し、一致を確かめたもの。
"""
import json, pathlib, shutil
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
PB = ROOT / "powerbi"; RES = ROOT / "results"
H = "'fact_store_day'"  # メジャーを置く表
M = []  # (フォルダ, 名前, 式, 説明)


def add(folder, name, expr, desc):
    M.append((folder, name, expr.strip(), desc))


# ---- 基本の合計 ----
BASE = [("売上", "'fact_store_day'[sales]", "売上（円）"), ("レシート", "'fact_store_day'[receipts]", "客数（レシートの枚数）"),
        ("点数", "'fact_store_day'[items]", "買上点数の合計"), ("粗利_廃棄前", "'fact_store_day'[gross_profit_before_waste]", "廃棄前の粗利"),
        ("廃棄", "'fact_store_day'[waste]", "廃棄・値引きロス"), ("粗利_廃棄後", "'fact_store_day'[gross_profit]", "廃棄後の粗利"),
        ("人時", "'fact_store_day'[labor_hours]", "人時"), ("人件費", "'fact_store_day'[labor_cost]", "人件費"),
        ("その他経費", "'fact_store_month'[other_cost]", "その他の経費（店×月）"),
        ("会員レシート", "'fact_member_month'[member_receipts]", "会員のレシート"), ("会員数", "'fact_member_month'[active_members]", "来店した会員の人数（店×月）")]
for n, col, d in BASE:
    add("1 基本", n, f"SUM({col})", d)
add("1 基本", "営業利益", "[粗利_廃棄後] - [人件費] - [その他経費]", "営業利益 ＝ 粗利（廃棄後）− 人件費 − その他の経費")

# ---- 既存店：当月と、同じ店の前年同月 ----
EXIST = """SUMX (
    VALUES ( 'dim_date'[month_start] ),
    VAR S = CALCULATETABLE ( VALUES ( 'fact_store_month'[store_id] ), 'fact_store_month'[is_existing] = 1 )
    RETURN CALCULATE ( [{b}], KEEPFILTERS ( TREATAS ( S, 'dim_store'[store_id] ) ){ly} )
)"""
for n, _, d in BASE:
    add("2 既存店", f"既存店{n}", EXIST.format(b=n, ly=""), f"月ごとに、その月の既存店だけの{d}を足す")
    add("2 既存店", f"既存店{n}_前年", EXIST.format(b=n, ly=",\n        DATEADD ( 'dim_date'[date], -12, MONTH )"),
        f"月ごとに、その月の既存店（同じ店）の前年同月の{d}を足す")
add("2 既存店", "既存店営業利益", "[既存店粗利_廃棄後] - [既存店人件費] - [既存店その他経費]", "既存店の営業利益")
add("2 既存店", "既存店営業利益_前年", "[既存店粗利_廃棄後_前年] - [既存店人件費_前年] - [既存店その他経費_前年]", "同じ店の前年同月の営業利益")

# ---- KPI（F246 の定義 v1） ----
K = [
    ("3 KPI", "既存店売上_前年比", "DIVIDE ( [既存店売上], [既存店売上_前年] ) - 1", "K01 既存店売上の前年比（補正前）"),
    ("3 KPI", "曜日の並びの効果", "DIVIDE ( SUM ( 'dim_date'[day_weight] ), CALCULATE ( SUM ( 'dim_date'[day_weight] ), DATEADD ( 'dim_date'[date], -12, MONTH ) ) ) - 1",
     "曜日・祝日の並びだけで動く分（dim_date[day_weight] の合計の比）"),
    ("3 KPI", "既存店売上_前年比_曜日補正", "DIVIDE ( 1 + [既存店売上_前年比], 1 + [曜日の並びの効果] ) - 1", "K01 曜日・祝日の並びを補正した前年比"),
    ("3 KPI", "既存店客数_前年比", "DIVIDE ( [既存店レシート], [既存店レシート_前年] ) - 1", "K02 客数（レシート）"),
    ("3 KPI", "既存店買上点数", "DIVIDE ( [既存店点数], [既存店レシート] )", "K03 買上点数（1回あたり）"),
    ("3 KPI", "既存店買上点数_前年比", "DIVIDE ( [既存店買上点数], DIVIDE ( [既存店点数_前年], [既存店レシート_前年] ) ) - 1", "K03 の前年比"),
    ("3 KPI", "既存店一品単価", "DIVIDE ( [既存店売上], [既存店点数] )", "K04 一品単価（円）"),
    ("3 KPI", "既存店一品単価_前年比", "DIVIDE ( [既存店一品単価], DIVIDE ( [既存店売上_前年], [既存店点数_前年] ) ) - 1", "K04 の前年比"),
    ("3 KPI", "既存店粗利率_廃棄後", "DIVIDE ( [既存店粗利_廃棄後], [既存店売上] )", "K06 粗利率（廃棄後）"),
    ("3 KPI", "既存店粗利率_廃棄後_前年差", "[既存店粗利率_廃棄後] - DIVIDE ( [既存店粗利_廃棄後_前年], [既存店売上_前年] )", "K06 の前年差（比で。0.001＝0.1pt）"),
    ("3 KPI", "既存店廃棄率", "DIVIDE ( [既存店廃棄], [既存店売上] )", "K07 廃棄率"),
    ("3 KPI", "既存店廃棄率_前年差", "[既存店廃棄率] - DIVIDE ( [既存店廃棄_前年], [既存店売上_前年] )", "K07 の前年差"),
    ("3 KPI", "既存店人時粗利", "DIVIDE ( [既存店粗利_廃棄後], [既存店人時] )", "K08 人時粗利（円／人時）"),
    ("3 KPI", "既存店人時粗利_前年比", "DIVIDE ( [既存店人時粗利], DIVIDE ( [既存店粗利_廃棄後_前年], [既存店人時_前年] ) ) - 1", "K08 の前年比"),
    ("3 KPI", "既存店人件費率", "DIVIDE ( [既存店人件費], [既存店売上] )", "K09 人件費率（補助）"),
    ("3 KPI", "既存店人件費率_前年差", "[既存店人件費率] - DIVIDE ( [既存店人件費_前年], [既存店売上_前年] )", "K09 の前年差"),
    ("3 KPI", "既存店営業利益_前年比", "DIVIDE ( [既存店営業利益], [既存店営業利益_前年] ) - 1", "K00 営業利益（KGI）の前年比。1店・月では幅 ±205% で使わない"),
    ("3 KPI", "来店頻度_会員", "DIVIDE ( [既存店会員レシート], [既存店会員数] )", "K05 来店頻度（会員、月あたり）"),
    ("3 KPI", "来店頻度_会員_前年比", "DIVIDE ( [来店頻度_会員], DIVIDE ( [既存店会員レシート_前年], [既存店会員数_前年] ) ) - 1", "K05 の前年比"),
    ("3 KPI", "既存店売上_前年比_全社との差", "[既存店売上_前年比_曜日補正] - CALCULATE ( [既存店売上_前年比_曜日補正], ALLSELECTED ( 'dim_store' ) )",
     "店の行で使う。見えている店ぜんぶ（RLS の地域の責任者なら自分の地域）との差"),
    ("4 橋", "橋_売上の伸び", "( [既存店売上] - [既存店売上_前年] ) * DIVIDE ( [既存店粗利_廃棄前_前年], [既存店売上_前年] )", "売上が伸びた分の粗利（前年の粗利率で）"),
    ("4 橋", "橋_廃棄前の粗利率", "[既存店売上] * ( DIVIDE ( [既存店粗利_廃棄前], [既存店売上] ) - DIVIDE ( [既存店粗利_廃棄前_前年], [既存店売上_前年] ) )", "値入れ（廃棄前の粗利率）が変わった分"),
    ("4 橋", "橋_廃棄", "- ( [既存店廃棄] - [既存店廃棄_前年] )", "廃棄の増加（マイナスが悪化）"),
    ("4 橋", "橋_人件費", "- ( [既存店人件費] - [既存店人件費_前年] )", "人件費の増加"),
    ("4 橋", "橋_その他経費", "- ( [既存店その他経費] - [既存店その他経費_前年] )", "その他の経費の増加"),
    ("5 日次", "売上_364日前", "CALCULATE ( [売上], DATEADD ( 'dim_date'[date], -364, DAY ) )", "同じ曜日どうし（52週前）"),
    ("5 日次", "売上_前年同曜日比", "DIVIDE ( [売上], [売上_364日前] ) - 1", "日・週の前年比（F246：日は364日前）。1店・日の幅は ±20%"),
]
for k in K:
    add(*k)

# ---- 部門 ----
add("6 部門", "部門売上", "SUM ( 'fact_store_day_category'[sales] )", "部門の売上")
add("6 部門", "部門粗利_廃棄前", "SUM ( 'fact_store_day_category'[gross_profit_before_waste] )", "部門の廃棄前の粗利")
add("6 部門", "部門廃棄", "SUM ( 'fact_store_day_category'[waste] )", "部門の廃棄")
for n in ("部門売上", "部門粗利_廃棄前", "部門廃棄"):
    add("6 部門", f"部門_既存店{n[2:]}", EXIST.format(b=n, ly=""), f"既存店の{n}")
    add("6 部門", f"部門_既存店{n[2:]}_前年", EXIST.format(b=n, ly=",\n        DATEADD ( 'dim_date'[date], -12, MONTH )"), f"同じ店の前年同月の{n}")
add("6 部門", "部門_既存店売上_前年比", "DIVIDE ( [部門_既存店売上], [部門_既存店売上_前年] ) - 1", "部門の売上の前年比")
add("6 部門", "部門_既存店粗利率_廃棄後", "DIVIDE ( [部門_既存店粗利_廃棄前] - [部門_既存店廃棄], [部門_既存店売上] )", "部門の粗利率（廃棄後）")
add("6 部門", "部門_既存店粗利率_廃棄後_前年差", "[部門_既存店粗利率_廃棄後] - DIVIDE ( [部門_既存店粗利_廃棄前_前年] - [部門_既存店廃棄_前年], [部門_既存店売上_前年] )", "その前年差")
add("6 部門", "部門_既存店廃棄率", "DIVIDE ( [部門_既存店廃棄], [部門_既存店売上] )", "部門の廃棄率")
add("6 部門", "部門_既存店廃棄率_前年差", "[部門_既存店廃棄率] - DIVIDE ( [部門_既存店廃棄_前年], [部門_既存店売上_前年] )", "その前年差")

# ---- 偶然の幅と色 ----
add("7 幅と色", "幅の範囲", """SWITCH (
    TRUE (),
    HASONEVALUE ( 'dim_store'[store_id] ), "1店",
    HASONEVALUE ( 'dim_store'[area] ), "地域",
    "全社"
)""", "いま見ている範囲（1店・地域・全社）。RLS で1つの地域だけ見える人は「地域」になる")
add("7 幅と色", "幅の粒度", """VAR n = DISTINCTCOUNT ( 'dim_date'[ym] )
RETURN SWITCH ( TRUE (), n = 1, "月", n = 12, "12か月", BLANK () )""", "1か月なら「月」、12か月なら「12か月」。それ以外は幅を出さない（色をつけない）")
BANDK = [("売上", "売上"), ("客数", "客数"), ("買上点数", "買上点数"), ("一品単価", "一品単価"), ("粗利率", "粗利率（廃棄後）"),
         ("廃棄率", "廃棄率"), ("人時粗利", "人時粗利"), ("営業利益", "営業利益")]
for short, kpi in BANDK:
    add("7 幅と色", f"幅_{short}", f"""VAR lv = [幅の範囲]
VAR gr = [幅の粒度]
RETURN IF ( ISBLANK ( gr ), BLANK (),
    LOOKUPVALUE ( 'ref_noise_band'[band_ratio], 'ref_noise_band'[level], lv, 'ref_noise_band'[grain], gr, 'ref_noise_band'[KPI], "{kpi}" ) )""",
        f"{kpi}の偶然の幅（比。0.013＝±1.3%、率は 0.0005＝±0.05pt）")
COLOR = """VAR v = [{m}]
VAR b = [幅_{b}]
RETURN SWITCH ( TRUE (),
    ISBLANK ( v ) || ISBLANK ( b ) || ABS ( v ) <= b, "#A3A29D",
    {good} )"""
for short, m, b, good in [("既存店売上", "既存店売上_前年比_曜日補正", "売上", 1), ("客数", "既存店客数_前年比", "客数", 1),
                          ("買上点数", "既存店買上点数_前年比", "買上点数", 1), ("一品単価", "既存店一品単価_前年比", "一品単価", 0),
                          ("粗利率", "既存店粗利率_廃棄後_前年差", "粗利率", 1), ("廃棄率", "既存店廃棄率_前年差", "廃棄率", -1),
                          ("人時粗利", "既存店人時粗利_前年比", "人時粗利", 1), ("営業利益", "既存店営業利益_前年比", "営業利益", 1)]:
    g = '"#5B4FC4"' if good == 0 else (f'IF ( v > 0, "#2A78D6", "#EB6834" )' if good > 0 else 'IF ( v > 0, "#EB6834", "#2A78D6" )')
    add("7 幅と色", f"色_{short}", COLOR.format(m=m, b=b, good=g), "条件付き書式（フィールド値）に使う。幅の内＝灰、外＝良い青・悪い橙・物価は紫")


def write_dax():
    lines = ["// F249 サンプルマート（架空）の DAX メジャー。会社・数字は架空（合成データ）。",
             "// 使い方：Power BI Desktop の「DAX クエリ ビュー」に全部貼り、上に出る「モデルの更新：新しいメジャーを追加」を押す。",
             "//         そのあと「実行」すると、最後の EVALUATE が FY ごとの値を出す（powerbi/expected_values.csv と比べる）。",
             "// この DAX は Power BI Desktop では動かしていない。期待値は pandas と SQL で計算して一致を確かめたもの。", "", "DEFINE"]
    for f, n, e, d in M:
        lines.append(f"    // [{f}] {d}")
        body = e.replace("\n", "\n        ")
        lines.append(f"    MEASURE {H}[{n}] =\n        {body}")
    lines += ["", "EVALUATE",
              "SUMMARIZECOLUMNS (", "    'dim_date'[fy_label],", "    FILTER ( VALUES ( 'dim_date'[fy_label] ), 'dim_date'[fy_label] IN { \"FY2023\", \"FY2024\", \"FY2025\" } ),",
              "    \"売上\", [売上], \"営業利益\", [営業利益], \"既存店売上\", [既存店売上], \"既存店売上_前年比\", [既存店売上_前年比],",
              "    \"既存店売上_前年比_曜日補正\", [既存店売上_前年比_曜日補正], \"既存店客数_前年比\", [既存店客数_前年比],",
              "    \"既存店買上点数_前年比\", [既存店買上点数_前年比], \"既存店一品単価_前年比\", [既存店一品単価_前年比],",
              "    \"既存店廃棄率_前年差\", [既存店廃棄率_前年差], \"既存店人時粗利_前年比\", [既存店人時粗利_前年比],",
              "    \"既存店営業利益_前年比\", [既存店営業利益_前年比], \"幅_売上\", [幅_売上], \"色_既存店売上\", [色_既存店売上]",
              ")", "ORDER BY 'dim_date'[fy_label]", ""]
    (PB / "measures.dax").write_text("\n".join(lines), encoding="utf-8")


def fmtv(v, n):
    if pd.isna(v):
        return "―"
    if any(k in n for k in ("前年比", "効果", "差", "率", "幅")) and abs(v) < 5:
        return f"{v:.6f}"
    return f"{v:,.2f}"


def write_md():
    E = pd.read_csv(RES / "expected_values.csv", encoding="utf-8-sig").set_index(["範囲", "期間", "メジャー"]).期待値
    nz = pd.read_csv(PB / "data" / "ref_noise_band.csv", encoding="utf-8-sig")
    def ex(sc, p, n):
        return E.get((sc, p, n), float("nan"))
    out = ["# F249 DAX メジャー一覧と期待値", "",
           "サンプルマート（架空）・合成データ。**DAX は Power BI Desktop では動かしていない。** 期待値は `src/03_分析.py` が pandas と SQL（DuckDB）の2通りで計算し、4,836 個の値で一致（相対差 1e-11 未満）を確かめたもの。",
           "Power BI で組み立てたら、下の「全社 FY2025」「全社 2026-03」の列と同じ値になるかを見る（スライサーで FY2025、または 2026年3月を選ぶ）。ほかの範囲（地域・店・部門）と月は `expected_values.csv`。", "",
           f"メジャーは {len(M)} 本。置き場所はすべて `fact_store_day`（表示フォルダで分ける）。", ""]
    cur = None
    for f, n, e, d in M:
        if f != cur:
            out += [f"## {f}", "", "| メジャー | 説明 | 全社 FY2025 | 全社 2026-03 |", "|---|---|---|---|"]; cur = f
        a, b = ex("全社", "FY2025", n), ex("全社", "2026-03", n)
        if f.startswith("6"):
            a, b = ex("部門4", "FY2025", n), ex("部門4", "2026-03", n)
            d = d + "（値は惣菜＝部門4）"
        if f.startswith("7"):
            a = b = float("nan")
        if f.startswith("1") and n not in ("売上", "営業利益", "粗利_廃棄後"):
            a = b = float("nan")
        if n.startswith("既存店") and n not in E.index.get_level_values(2):
            a = b = float("nan")
        out.append(f"| `{n}` | {d} | {fmtv(a, n)} | {fmtv(b, n)} |")
    out += ["", "―は期待値の表に入れていないもの（合計の部品など）。部品の値は、上の比の値が合えば合っている。", "",
            "## 幅と色の期待値（全社）", "", "| メジャー | FY2025（12か月） | 2026-03（月） |", "|---|---|---|"]
    for short, kpi in BANDK:
        g = lambda gr: nz[(nz.level == "全社") & (nz.grain == gr) & (nz.KPI == kpi)].band_ratio
        out.append(f"| `幅_{short}` | {g('12か月').iloc[0]:.6f} | {g('月').iloc[0]:.6f} |")
    out += ["", "色（FY2025・全社）：既存店売上 #2A78D6、客数 #A3A29D、買上点数 #EB6834、一品単価 #5B4FC4、粗利率 #EB6834、廃棄率 #EB6834、人時粗利 #2A78D6、営業利益 #EB6834。", "",
            "## 全文", "", "`measures.dax` を見る（DAX クエリ ビューにそのまま貼れる DEFINE ブロック）。", ""]
    (PB / "measures.md").write_text("\n".join(out), encoding="utf-8")


PQ_COLS = {
    "dim_date": [("date", "type date"), ("year", "Int64.Type"), ("month", "Int64.Type"), ("ym", "type text"), ("month_start", "type date"),
                 ("fy", "Int64.Type"), ("fy_label", "type text"), ("fy_month_no", "Int64.Type"), ("dow", "Int64.Type"), ("dow_name", "type text"),
                 ("hol", "Int64.Type"), ("flyer", "Int64.Type"), ("day_weight", "type number")],
    "dim_store": [("store_id", "Int64.Type"), ("store_name", "type text"), ("area", "type text"), ("size", "type text"), ("open_date", "type date"),
                  ("close_date", "type date"), ("area_order", "Int64.Type")],
    "dim_category": [("category_id", "Int64.Type"), ("category", "type text"), ("margin", "type number"), ("waste", "type number"), ("promo", "Int64.Type")],
    "fact_store_day": [("biz_date", "type date"), ("store_id", "Int64.Type"), ("receipts", "Int64.Type"), ("member_receipts", "Int64.Type"), ("items", "Int64.Type"),
                       ("sales", "type number"), ("gross_profit_before_waste", "type number"), ("waste", "type number"), ("gross_profit", "type number"),
                       ("labor_hours", "type number"), ("labor_cost", "type number"), ("labor_imputed", "Int64.Type")],
    "fact_store_day_category": [("biz_date", "type date"), ("store_id", "Int64.Type"), ("category_id", "Int64.Type"), ("sales", "type number"),
                                ("gross_profit_before_waste", "type number"), ("waste", "type number")],
    "fact_store_month": [("month_start", "type date"), ("store_id", "Int64.Type"), ("other_cost", "type number"), ("is_existing", "Int64.Type"),
                         ("labor_imputed_days", "Int64.Type"), ("days_with_sales", "Int64.Type")],
    "fact_member_month": [("month_start", "type date"), ("store_id", "Int64.Type"), ("active_members", "Int64.Type"), ("member_receipts", "Int64.Type")],
    "ref_noise_band": [("level", "type text"), ("grain", "type text"), ("KPI", "type text"), ("band", "type number"), ("unit", "type text"), ("band_ratio", "type number")],
    "sec_user_area": [("user_principal", "type text"), ("area", "type text")],
}


def write_pq():
    out = ["// F249 Power Query（M）。サンプルマート（架空）・合成データ。",
           "// 使い方：「データの変換」→「新しいパラメーター」で DataFolder（テキスト。例 C:\\work\\F249\\powerbi\\data\\ 、最後の \\ を忘れない）を作り、",
           "//         「新しいソース」→「空のクエリ」を表の数だけ作って、下の各ブロックを「詳細エディター」に貼る。クエリ名は // ==== の名前にする。",
           "// .gz は Binary.Decompress で展開して読む。CSV は UTF-8（BOM つき）。日付は yyyy-mm-dd。", ""]
    for t, cols in PQ_COLS.items():
        fn = f"{t}.csv.gz" if t.startswith("fact_store_day") else f"{t}.csv"
        src = (f'Binary.Decompress ( File.Contents ( DataFolder & "{fn}" ), Compression.GZip )' if fn.endswith(".gz")
               else f'File.Contents ( DataFolder & "{fn}" )')
        types = ",\n        ".join(f'{{"{c}", {ty}}}' for c, ty in cols)
        out += [f"// ==== {t} ====", "let",
                f"    Source = Csv.Document ( {src}, [Delimiter = \",\", Encoding = 65001, QuoteStyle = QuoteStyle.Csv] ),",
                "    Promoted = Table.PromoteHeaders ( Source, [PromoteAllScalars = true] ),",
                f"    Typed = Table.TransformColumnTypes ( Promoted, {{\n        {types}\n    }}, \"en-US\" )", "in", "    Typed", ""]
    (PB / "powerquery.m").write_text("\n".join(out), encoding="utf-8")


def write_theme():
    th = {"name": "サンプルマート（架空）F249",
          "dataColors": ["#2A78D6", "#EB6834", "#1BAF7A", "#5B4FC4", "#A3A29D", "#0B0B0B", "#E0A800", "#52514E"],
          "background": "#FFFFFF", "foreground": "#0B0B0B", "tableAccent": "#2A78D6",
          "good": "#2A78D6", "neutral": "#A3A29D", "bad": "#EB6834", "maximum": "#2A78D6", "center": "#F0F0EE", "minimum": "#EB6834",
          "textClasses": {"callout": {"fontSize": 28, "fontFace": "Segoe UI Semibold", "color": "#0B0B0B"},
                          "title": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#0B0B0B"},
                          "header": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": "#52514E"},
                          "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": "#52514E"}},
          "visualStyles": {"*": {"*": {"background": [{"show": True, "color": {"solid": {"color": "#F7F7F5"}}, "transparency": 0}],
                                       "border": [{"show": False}], "dropShadow": [{"show": False}]}},
                           "page": {"*": {"background": [{"color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}]}}}}
    (PB / "theme.json").write_text(json.dumps(th, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    write_dax(); write_md(); write_pq(); write_theme()
    shutil.copy(RES / "expected_values.csv", PB / "expected_values.csv")
    n = pd.read_csv(PB / "expected_values.csv", encoding="utf-8-sig")
    print("measures", len(M), "expected rows", len(n))
    json.dump({"measures": len(M), "expected_rows": len(n)}, open(RES / "H_package_counts.json", "w"))


if __name__ == "__main__":
    main()
