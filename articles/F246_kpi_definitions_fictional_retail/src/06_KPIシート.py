"""06 KPI シート：KPI 定義の一覧（sheet/kpi_sheet.html）と、その画像（figures/fig6_kpi_sheet.png）を作る。
数字は results/ の CSV から読む（サンプルマート（架空）の合成データ、seed 0）。担当は役割の名前で、人ではない。"""
import pathlib, html
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
tree = pd.read_csv(R / "A_kpi_tree_fy2024_fy2025.csv", index_col=0)
sc = pd.read_csv(R / "E_kpi_scorecard.csv").set_index("KPI")

# id, 層, 名前, 計算式, 粒度, 見る頻度, 担当（役割）, 表示の種類, スコアカードの名前, メモ
KPIS = [
    ("K00", "KGI", "営業利益", "粗利（廃棄後）− 人件費 − その他の経費", "全社・月", "月次", "経営企画", "yen", None, "1店・月では偶然の幅が ±200% を超える。全社か、四半期で見る"),
    ("K01", "主要", "既存店売上（前年比）", "既存店の売上 ÷ 前年同月の同じ店の売上 − 1", "全社・月", "週次・月次", "営業部", "pct", "売上", "曜日・祝日の並びを補正して読む。物価で上がる分を含む"),
    ("K02", "主要", "客数（レシート枚数）", "レシート枚数の合計", "店・月", "週次", "店長", "cnt", "客数", "会員の人数とは別物。会員の人数は会員化が進むだけで増える"),
    ("K03", "主要", "買上点数", "点数の合計 ÷ レシート枚数", "店・月", "週次", "店長・部門担当", "num", "買上点数", "客単価 = 買上点数 × 一品単価。客単価だけでは理由が見えない"),
    ("K04", "主要", "一品単価", "売上 ÷ 点数の合計", "全社・月", "月次", "商品部", "yen1", "一品単価", "物価の影響が大きく、店では動かしにくい"),
    ("K05", "主要", "来店頻度（会員）", "会員のレシート枚数 ÷ 来店した会員の人数", "店・月", "月次", "販促担当", "num", "来店頻度（会員）", "会員だけの数字。会員比率が変わると全体の代わりにならない"),
    ("K06", "主要", "粗利率（廃棄後）", "（粗利 − 廃棄）÷ 売上", "店・部門・月", "月次", "部門担当", "rate", "粗利率（廃棄後）", "廃棄前の粗利率だと、廃棄の悪化が見えない"),
    ("K07", "主要", "廃棄率", "廃棄額 ÷ 売上", "店・部門・週", "週次", "部門担当", "rate", "廃棄率", "上がると悪い。値引きで減らすと粗利率が下がるので、2つを並べて見る"),
    ("K08", "主要", "人時粗利", "粗利（廃棄後）÷ 人時", "店・月", "月次", "店長", "yen1", "人時粗利", "時給が上がる年は、人時粗利が横ばいでも利益は減る"),
    ("K09", "補助", "人件費率", "人件費 ÷ 売上", "全社・月", "月次", "経営企画", "rate", "人件費率", "時給の改定は店では動かせない。店の評価には人時粗利を使う"),
]

def fmt(v, kind):
    if kind == "yen":
        return f"{v/1e8:,.1f}億円"
    if kind == "pct":
        return "—"
    if kind == "cnt":
        return f"{v/1e4:,.0f}万回"
    if kind == "num":
        return f"{v:.2f}"
    if kind == "yen1":
        return f"{v:,.0f}円"
    if kind == "rate":
        return f"{v*100:.2f}%"
    return str(v)

def change(name, kind):
    a, b = tree.loc[name, "既存店_FY2024"], tree.loc[name, "既存店_FY2025"]
    if kind == "rate":
        return f"{(b-a)*100:+.2f}pt"
    return f"{(b/a-1)*100:+.1f}%"

rows = []
for kid, layer, name, formula, grain, freq, owner, kind, scname, note in KPIS:
    key = {"既存店売上（前年比）": "売上", "客数（レシート枚数）": "客数"}.get(name, name)
    val = fmt(tree.loc[key, "既存店_FY2025"], "yen" if key == "売上" else kind)
    chg = change(key, kind)
    if scname:
        s = sc.loc[scname]
        unit = "pt" if kind == "rate" else "%"
        if pd.isna(s.iloc[2]):
            noise = "未計測"
        else:
            noise = f"±{s.iloc[2]:.2f}{unit}" if kind == "rate" else f"±{s.iloc[2]:.1f}{unit}"
        corr = f"{s.iloc[0]:.2f}"
        move = s.iloc[3]
    else:
        noise, corr, move = "±205%（1店）", "—", "—"
    rows.append(dict(id=kid, layer=layer, name=name, formula=formula, grain=grain, freq=freq, owner=owner,
                     val=val, chg=chg, noise=noise, corr=corr, move=move, note=note))
df = pd.DataFrame(rows)
df.to_csv(R / "F_kpi_sheet.csv", index=False, encoding="utf-8-sig")

head = ["ID", "層", "KPI", "計算式", "見る粒度", "頻度", "担当（役割）", "FY2025 既存店", "前年比", "1店・月の偶然の幅", "利益との相関", "店で動かせるか", "注意"]
tr = []
for r in rows:
    cls = {"KGI": "kgi", "主要": "main", "補助": "sub"}[r["layer"]]
    cells = [r[k] for k in ["id", "layer", "name", "formula", "grain", "freq", "owner", "val", "chg", "noise", "corr", "move", "note"]]
    tr.append(f'<tr class="{cls}">' + "".join(f"<td>{html.escape(str(c))}</td>" for c in cells) + "</tr>")
page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>KPI 定義シート</title>
<style>
:root{{--ink:#1f2328;--muted:#5b6470;--line:#d6dbe1;--kgi:#fbe9e7;--main:#eef4fb;--sub:#f6f7f8;--bg:#ffffff}}
body{{font-family:"Noto Sans CJK JP","Noto Sans JP",sans-serif;color:var(--ink);background:var(--bg);margin:24px;font-size:13px}}
h1{{font-size:20px;margin:0 0 4px}} p{{margin:2px 0;color:var(--muted)}}
table{{border-collapse:collapse;margin-top:12px;width:100%}}
th,td{{border:1px solid var(--line);padding:6px 7px;vertical-align:top;text-align:left}}
th{{background:#e9edf1;font-weight:700;white-space:nowrap}}
td:nth-child(8),td:nth-child(9),td:nth-child(10),td:nth-child(11){{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}}
td:nth-child(12){{text-align:center}}
tr.kgi td{{background:var(--kgi)}} tr.main td{{background:var(--main)}} tr.sub td{{background:var(--sub)}}
td:nth-child(2),td:nth-child(5),td:nth-child(6){{white-space:nowrap}} td:nth-child(3){{font-weight:700;white-space:nowrap}} td:nth-child(4){{min-width:220px}} td:nth-child(13){{min-width:260px}}
.foot{{margin-top:10px;font-size:12px}}
</style></head><body>
<h1>サンプルマート（架空）KPI 定義シート　v1</h1>
<p>既存店＝その月の月初で開店から13か月以上、かつ月末まで営業している店。前年比は同じ店どうしで比べる。数字は FY2025（2025年4月〜2026年3月）の既存店。</p>
<table><thead><tr>{"".join(f"<th>{h}</th>" for h in head)}</tr></thead><tbody>
{"".join(tr)}
</tbody></table>
<p class="foot">偶然の幅：本当の変化がなくても出る前年比のぶれ（合成データを20回作り直した標準偏差×1.96）。利益との相関：店・月の営業利益の前年差との順位相関。「店で動かせるか」は筆者の判断。サンプルマート（架空）の合成データ。売上の季節と物価の動きだけ公開データ（商業動態統計・家計調査）から借りた。</p>
</body></html>"""
(ROOT / "sheet").mkdir(exist_ok=True)
(ROOT / "sheet" / "kpi_sheet.html").write_text(page, encoding="utf-8")

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1700, "height": 400}, device_scale_factor=1)
    pg.goto((ROOT / "sheet" / "kpi_sheet.html").as_uri())
    pg.screenshot(path=str(ROOT / "figures" / "fig6_kpi_sheet.png"), full_page=True)
    b.close()
print(df[["id", "name", "val", "chg", "noise", "corr", "move"]].to_string(index=False))
