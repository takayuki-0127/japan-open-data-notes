"""04 報告：2026年3月の「1枚の報告」を、results/ の数字から自動で書き出す（毎月同じ形で作れるように）。

- reports/report_202603_onepage.md / .html：結論から書く1枚の報告（採用する形）
- reports/report_202603_first_draft.md：比べるための「最初の下書き」（数字を上から順に並べ、偶然の揺れまで理由にしてしまう形）
- 数字はすべて results/main.json と results/A_monthly_decomposition_seed0.csv から入れる。手で書いた数字はない。
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, REP = ROOT / "results", ROOT / "reports"; REP.mkdir(exist_ok=True)
m = json.load(open(RES / "main.json"))
A = pd.read_csv(RES / "A_monthly_decomposition_seed0.csv").set_index("ym")
B = pd.read_csv(RES / "B_noise_band90_halfwidth.csv", index_col=0)
T = m["target"]; t = A.loc[T]; b = B.loc[T]
st = pd.read_csv(ROOT / "data" / "mart" / "dim_store.csv", encoding="utf-8-sig").set_index("store_id")
sm = pd.read_csv(ROOT / "data" / "mart" / "store_month.csv", encoding="utf-8-sig")

M = lambda s_: s_.replace("-", "−")   # 負の符号は「−」
pc = lambda x, d=1: M(f"{x * 100:+.{d}f}%")
pt = lambda x, d=1: M(f"{x * 100:+.{d}f}pt")
hw = lambda x, d=1: f"±{x * 100:.{d}f}pt"
fy25 = [ym for ym in A.index if ym >= "2025-04"]
radj_rank = A.loc[fy25, "receipts_adj_yoy"].rank().loc[T]           # 1 = いちばん弱い
ind = m["industry_yoy_FY2025"]; ind_min = min(ind, key=ind.get)
sales_m = sm[(sm.ym == T) & (sm.is_existing == 1)].sales.sum()
cal_adj = (1 + t.sales_yoy) / (1 + t.calendar_receipts) - 1
rel = m["rel_target"]
beyond = [k for k, v in rel.items() if v[2]]
fya = m["fy2025_area_seed0"]; fyb = m["fy2025_area_band90_half"]
area_rel = {a: rel[f"rel_area_receipts_adj_yoy_{a}"] for a in ["都市", "郊外", "地方"]}
stores_beyond = [int(k.split("_")[-1]) for k in beyond if "store" in k]
cats = {k.replace("cat_sales_yoy_", ""): t[k] for k in A.columns if k.startswith("cat_sales_yoy_")}
cat_rel_max = max(abs(rel[f"rel_cat_sales_yoy_{c}"][0]) for c in cats)
store_band = float(np.median([b[c] for c in B.columns if c.startswith("rel_store_sales_yoy_") and not np.isnan(b[c])]))
sname = lambda k: st.loc[k, "store_name"].replace("サンプルマート", "").replace("（架空）", "")
chance = m["robustness"]["chance_beyond_band_per_seed"]

# 来月（2026年4月）の暦の見込み：同じ回帰の係数で、2026-04 と 2025-04 の暦の重みを比べる（祝日は 4/29）
coef = pd.read_csv(RES / "D_calendar_coefficients_FY2022-24.csv", index_col=0).log_coef.values
def wsum(days, hol):
    X = np.zeros((len(days), 8))
    for k in range(1, 7): X[:, k - 1] = days.dayofweek == k
    X[:, 6] = days.isin(hol) & (days.dayofweek < 5)
    return np.exp(X @ coef).sum()
apr = wsum(pd.date_range("2026-04-01", "2026-04-30"), pd.to_datetime(["2026-04-29"])) / \
      wsum(pd.date_range("2025-04-01", "2025-04-30"), pd.to_datetime(["2025-04-29"])) - 1

v = dict(
    sales=pc(t.sales_yoy), oku=f"{sales_m / 1e8:.1f}億円", n=int(t.n_stores), cal=pt(t.c_calendar), caladj=pc(cal_adj),
    price=pc(t.unit_price_yoy), radj=pc(t.receipts_adj_yoy), items=pc(t.items_per_receipt_yoy),
    c_price=pt(t.c_price), c_items=pt(t.c_items), c_cal=pt(t.c_calendar), c_radj=pt(t.c_receipts_adj),
    band=hw(b.sales_yoy), band_radj=hw(b.receipts_adj_yoy), all=pc(t.sales_yoy_all),
    ind=pc(ind[T]), ind_avg=pc(np.mean(list(ind.values()))), apr=pt(apr),
    seedneg=f"{m['robustness']['seeds_target']['share_negative'] * 100:.0f}%",
    seedmean=pc(m["robustness"]["seeds_target"]["sales_yoy_mean"]),
)
rank_txt = "今年度でいちばん弱い" if radj_rank == 1 else f"今年度で{int(radj_rank)}番目に弱い"
ind_txt = "今年度でいちばん低い伸び" if ind_min == T else "低めの伸び"

one = f"""# 3月の既存店売上が前年を下回った理由

サンプルマート（架空）　経営会議 資料　作成：分析担当（2026年4月）

## 結論
**3月の既存店売上は前年比 {v['sales']}（{v['n']}店、{v['oku']}）。今年度はじめての前年割れだが、そのうち約{abs(t.c_calendar) * 100:.1f}pt は暦の差（土曜日が1日少ない）で、暦をそろえると {v['caladj']}。**
値上がりで一品単価は {v['price']} と今年度と同じ伸びだった。それを、客数の弱さ（暦をそろえて {v['radj']}、{rank_txt}）と、1回の買上点数の減り（{v['items']}）が打ち消した。
客数の弱さは3つの地域のすべて、売上の弱さは7部門のすべてに出ており、業界（スーパー全体の販売額）の伸びも3月は {v['ind']} と{ind_txt}だった。特定の店や部門の問題ではなく、市場全体の動きとみている（推測）。

## 数字（既存店・前年同月比）
| 項目 | 前年比 | 売上の前年比への寄与 | 偶然の幅（90%） |
|---|---|---|---|
| 売上 | {v['sales']} | — | {v['band']} |
| 一品単価 | {v['price']} | {v['c_price']} | {hw(b.unit_price_yoy)} |
| 1回の買上点数 | {v['items']} | {v['c_items']} | {hw(b.items_per_receipt_yoy)} |
| 客数のうち暦の差 | {pc(t.calendar_receipts)} | {v['c_cal']} | （計算で決まる） |
| 客数（暦をそろえた） | {v['radj']} | {v['c_radj']} | {v['band_radj']} |

全店（新店・閉店を含む）は {v['all']}。業界（商業動態統計・スーパー、全店・名目）は {v['ind']}（今年度の平均 {v['ind_avg']}）。

## 「いつもの揺れ」と見て、理由にしないもの
- **地域**：全体との差は 都市 {pt(area_rel['都市'][0])}・郊外 {pt(area_rel['郊外'][0])}・地方 {pt(area_rel['地方'][0])}。1か月の地域の差は偶然だけでも {hw(area_rel['郊外'][1])} 程度動く。年度の12か月で見ると、都市 {pt(fya['rel_fy_receipts_adj_yoy_都市'])}・地方 {pt(fya['rel_fy_receipts_adj_yoy_地方'])}（幅 {hw(fyb['rel_fy_receipts_adj_yoy_地方'])}）の差が続いており、これは3月に始まったことではない。郊外の3月の弱さ（{pt(area_rel['郊外'][0])}）は来月も見る。
- **部門**：7部門とも {pc(min(cats.values()))}〜{pc(max(cats.values()))} で、全体との差は最大 {cat_rel_max * 100:.1f}pt。どれも偶然の幅の中。
- **店**：1店・1か月の前年比は偶然だけで {hw(store_band, 0)} 程度動く。{'・'.join(f"{sname(k)}（{pc(t[f'store_sales_yoy_{k:02d}'])}）" for k in stores_beyond)} は幅をわずかに超えた（08店は開店から1年半で、まだ立ち上がりの伸びが残っている可能性がある：推測）が、{len(rel)}項目を見れば偶然だけでも平均 {chance['mean']:.0f} 項目は幅を超える。来月も同じ向きなら店に聞く。

## 次にやること
1. 4月の数字（翌月5日の締め）で、暦をそろえた客数の弱さが続くかを確かめる。2か月続けば、価格と販促の見直しの材料として改めて報告する。4月は暦の差がほとんどない見込み（{v['apr']}）。
2. 郊外の客数と、上の店の数字は、来月も同じ向きかを見る。それまでは店への指示は出さない。

---
付記：既存店＝月初で開店から13か月以上、かつ月末まで営業している店。暦の差＝前の年度までの店×日のデータで測った曜日・祝日の効き方を、今年と前年の3月の日の並びに当てたもの。偶然の幅＝同じ設定で乱数だけを変えた20通りのデータで同じ計算をしたときの90%の幅（半分の幅）。会社・数字はすべて架空（合成データ）。
"""

store_worst = int(A.loc[T, [c for c in A.columns if c.startswith("store_sales_yoy_")]].idxmin().split("_")[-1])
store_best = int(A.loc[T, [c for c in A.columns if c.startswith("store_sales_yoy_")]].idxmax().split("_")[-1])
cat_worst = min(cats, key=cats.get)
area_s = {a: t[f"area_sales_yoy_{a}"] for a in ["都市", "郊外", "地方"]}
area_worst = min(area_s, key=area_s.get)
draft = f"""# 3月度 売上報告（最初の下書き：比べるために残したもの）

3月の既存店売上は {v['oku']}で、前年同月比 {v['sales']}となりました。客数は {pc(t.receipts_yoy)}、1回の買上点数は {v['items']}、一品単価は {v['price']}でした。

地域別では、{area_worst}が {pc(area_s[area_worst])}ともっとも悪く、{'、'.join(f"{a} {pc(x)}" for a, x in area_s.items() if a != area_worst)}でした。
部門別では、{cat_worst}が {pc(cats[cat_worst])}ともっとも落ち込み、{'、'.join(f"{c} {pc(x)}" for c, x in cats.items() if c != cat_worst)}でした。
店別では、{sname(store_worst)}が {pc(t[f'store_sales_yoy_{store_worst:02d}'])}と大きく落ち込み、{sname(store_best)}は {pc(t[f'store_sales_yoy_{store_best:02d}'])}と好調でした。

以上から、{area_worst}の店の集客の見直し、{cat_worst}の売場の確認、{sname(store_worst)}への聞き取りが必要と考えます。
"""
(REP / "report_202603_onepage.md").write_text(one)
(REP / "report_202603_first_draft.md").write_text(draft)

# HTML（A4 1枚に収まる大きさ。図の6はこれを画像にしたもの）
import re
def md2html(md):
    out, rows = [], []
    for line in md.splitlines():
        if line.startswith("|"):
            if set(line.replace("|", "").strip()) <= set("-"):
                continue
            rows.append([c.strip() for c in line.strip("|").split("|")]); continue
        if rows:
            out.append("<table>" + "".join(("<tr>" + "".join(f"<{'th' if i == 0 else 'td'}>{c}</{'th' if i == 0 else 'td'}>" for c in r) + "</tr>") for i, r in enumerate(rows)) + "</table>"); rows = []
        if line.startswith("# "): out.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "): out.append(f"<h2>{line[3:]}</h2>")
        elif re.match(r"^\d\. ", line): out.append(f"<p class='n'>{line}</p>")
        elif line.startswith("- "): out.append(f"<p class='b'>・{line[2:]}</p>")
        elif line.startswith("---"): out.append("<hr>")
        elif line.strip(): out.append(f"<p>{line}</p>")
    html = "\n".join(out)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
css = """body{font-family:'Noto Sans CJK JP','Noto Sans JP',sans-serif;width:794px;margin:0 auto;padding:28px 36px;box-sizing:border-box;color:#1d2433;font-size:12.5px;line-height:1.65;background:#fff}
h1{font-size:20px;margin:0 0 2px;border-bottom:3px solid #2b5c8a;padding-bottom:4px}h2{font-size:14px;color:#2b5c8a;margin:14px 0 4px;border-left:4px solid #2b5c8a;padding-left:6px}
p{margin:3px 0}p.b,p.n{padding-left:1em;text-indent:-1em}strong{background:#fff3c4}table{border-collapse:collapse;width:100%;margin:4px 0;font-size:12px}
th,td{border:1px solid #c9d3df;padding:3px 6px;text-align:right}th{background:#eef3f8}td:first-child,th:first-child{text-align:left}hr{border:0;border-top:1px solid #c9d3df;margin:12px 0 6px}
p:last-child{font-size:10.5px;color:#556}"""
(REP / "report_202603_onepage.html").write_text(f"<!doctype html><html lang='ja'><meta charset='utf-8'><title>3月の既存店売上の報告（架空）</title><style>{css}</style><body>{md2html(one)}</body></html>")
json.dump({"april_calendar_effect": apr, "cal_adjusted_sales_yoy": cal_adj, "receipts_adj_rank_FY2025": int(radj_rank),
           "stores_beyond": stores_beyond, "draft_area_worst": area_worst, "draft_cat_worst": cat_worst,
           "draft_store_worst": store_worst, "draft_store_best": store_best}, open(RES / "G_report_numbers.json", "w"), ensure_ascii=False, indent=1)
print(one); print(draft)
