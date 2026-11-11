"""04 予算案：results/ の数字から、経営会議に出す1枚の予算案（md と HTML）と、5か月後の答え合わせのメモを作る。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, REP = ROOT / "results", ROOT / "reports"
REP.mkdir(exist_ok=True)
J = json.load(open(RES / "main.json"))
sc = pd.read_csv(RES / "D_budget_scenarios.csv", index_col=0) / 1e8
ar = pd.read_csv(RES / "D_budget_by_area.csv", index_col=0)
dr = J["D_drivers"]; D = J["D_budget"]; E = J["E_check"]
g = D["growth_base_pct"] / 100
vol = (1 + g) / ((1 + dr["unit_price_growth"]) * (1 + dr["items_per_receipt_growth"])) - 1
lo, hi = D["range80_pct"]; l9, h9 = D["range90_pct"]
oplo, ophi = J["D_op_range_pct_vs_base"]
b, f25 = sc.loc["基本"], sc.loc["FY2025 実績（同じ22店）"]
dn, up = sc.loc["下振れ（10%）"], sc.loc["上振れ（90%）"]
all24 = sc.loc["FY2025 実績（全24店）"]
r5lo, r5hi = E["range5_pct"]
_c = {(x["method"], x["model"]): x["covered"] for x in J["C_coverage"]}
cov_sng = _c[("③業界の外れ＋自社の揺れ", "季節ナイーブ＋伸び")]; cov_sngc = _c[("③業界の外れ＋自社の揺れ", "季節ナイーブ＋伸び＋暦")]
cov_ets = _c[("①モデルの区間", "ETS")]; cov_sar = _c[("①モデルの区間", "SARIMA")]


def yo(a, c):
    return f"{(a / c - 1) * 100:+.1f}%"


rows = [("売上", "sales", 1), ("粗利（廃棄のあと）", "gross_profit", 2), ("人件費", "labor_cost", 2), ("その他の経費", "other_cost", 2), ("営業利益", "operating_profit", 2)]
tbl = ["| 項目（億円） | FY2025 実績（同じ22店） | 下振れ（10%） | **基本** | 上振れ（90%） | 基本の前年比 |", "|---|---|---|---|---|---|"]
for nm, c, d in rows:
    tbl.append(f"| {nm} | {f25[c]:.{d}f} | {dn[c]:.{d}f} | **{b[c]:.{d}f}** | {up[c]:.{d}f} | {yo(b[c], f25[c])} |")
atbl = ["| 地域 | 売上（億円） | 売上の前年比 | 営業利益（億円） | 営業利益の前年比 |", "|---|---|---|---|---|"]
for a in ["都市", "郊外", "地方"]:
    r = ar.loc[a]
    atbl.append(f"| {a} | {r.sales / 1e8:.1f} | {r['sales_yoy%']:+.1f}% | {r.operating_profit / 1e8:.2f} | {r['op_yoy%']:+.1f}% |")

md = f"""# FY2026 予算案（売上・営業利益）　サンプルマート（架空）

作成の時点：2026年3月末（FY2025 までの実績）。対象：FY2026（2026年4月〜2027年3月）に営業する22店。
**会社も数字もすべて架空（合成データ）です。**

## 結論
1. **売上 {b.sales:.1f}億円**（同じ22店の FY2025 比 **{yo(b.sales, f25.sales)}**）。80%の幅は **{dn.sales:.1f}〜{up.sales:.1f}億円**（{lo:+.1f}〜{hi:+.1f}%）。
2. **営業利益 {b.operating_profit:.2f}億円**（{yo(b.operating_profit, f25.operating_profit)}）。幅は **{dn.operating_profit:.2f}〜{up.operating_profit:.2f}億円**（{oplo:+.0f}〜{ophi:+.0f}%）。売上の ±2% が、利益では ±16% になる。
3. 地方は売上 {ar.loc['地方', 'sales_yoy%']:+.1f}%・営業利益 {ar.loc['地方', 'op_yoy%']:+.0f}%。客数の減りと、FY2025 に悪化した廃棄がそのまま続く前提。

## 数字
{chr(10).join(tbl)}

- 全24店（閉店した店を含む）の FY2025 実績 {all24.sales:.1f}億円と比べると、売上は {yo(b.sales, all24.sales)}。

{chr(10).join(atbl)}

## 前提（推測を含む）
- **売上の伸び**：直近12か月の伸びが来期も続くとした（季節ナイーブ＋伸び、月ごとの曜日・祝日の並びを補正）。中身は、一品単価 {dr['unit_price_growth'] * 100:+.1f}%・1回の買上点数 {dr['items_per_receipt_growth'] * 100:+.1f}%・客数 {vol * 100:+.1f}%（どれも直近12か月の前年比が続くという仮定。**推測**）。
- **費用**：時給 {dr['wage_growth'] * 100:+.1f}%、その他の経費 {dr['other_cost_growth'] * 100:+.1f}%（直近12か月の実績の伸び）。人時は「店の固定分＋レシート1枚あたり {dr['hours_per_receipt']:.3f} 時間」。粗利率は店ごとの FY2025 の実績のまま（廃棄の悪化が戻らない前提。**推測**）。
- **新しい店**：08店（2024年10月開店）は前年の同じ月 × 地域の伸び、16店（2025年4月開店）は直近3か月の水準 × 地域の季節の形（**決め**）。
- **閉店**：24店（2025年9月末に閉店）は入れていない。

## 幅の作り方
- 自社の記録は4年しかなく、1年分の予算の外れの「答え」は1回分しかない。そこで、**業界（商業動態統計・スーパー）で同じ作り方の予測を2015年から毎月作り、1年合計の外れ（コロナ期を除く {D['n_industry_errors']}回）の幅を借りた**。これに、自社だけの偶然の揺れ（業界との差のばらつき）を足した。
- この作り方で過去（予算の起点13回 × 乱数を変えた20通り）を作り直すと、実際が80%の幅に入ったのは {cov_sng:.0f}%（伸びのみ）・{cov_sngc:.0f}%（暦の補正あり）。ETS・SARIMA のモデルの区間は狭すぎ、{cov_ets:.0f}%・{cov_sar:.0f}%しか入らなかった。
- 90%の幅にすると、売上は {l9:+.1f}〜{h9:+.1f}%。

## 毎月見ること
- **売上の累計の予算差**が、5か月目までに **{r5lo:+.1f}〜{r5hi:+.1f}%** を出たら、伸びの前提（特に市場の伸び）を見直して見通しを出し直す。
- 費用の前提（時給・経費）は、売上が予算どおりなら利益はほぼ予算どおり。**利益の外れは、ほとんど売上の外れから来る**。
"""
(REP / "budget_FY2026_onepage.md").write_text(md, encoding="utf-8")

# 5か月後の答え合わせ
e = pd.read_csv(RES / "E_check_apr_aug_2026.csv")
e2 = pd.read_csv(RES / "E_check_pl_apr_aug_2026.csv", index_col=0)
lines = ["| 月 | 予算（億円） | 実績（億円） | 予算との差 | 実績の前年比 | 業界の前年比 |", "|---|---|---|---|---|---|"]
for _, r in e.iterrows():
    lines.append(f"| {r.ym} | {r.budget / 1e8:.2f} | {r.actual / 1e8:.2f} | {r['diff%']:+.1f}% | {r['actual_yoy%']:+.1f}% | {r['industry_yoy%']:+.1f}% |")
chk = f"""# FY2026 予算の答え合わせ（4〜8月の5か月）　サンプルマート（架空）

作成の時点：2026年9月（8月までの実績）。**会社も数字もすべて架空（合成データ）です。**

## 結論
- 売上の累計は予算より **{E['cum5_diff_pct']:+.1f}%**。決めておいた見直しの線（{r5lo:+.1f}〜{r5hi:+.1f}%）を下に出た。
- 理由は市場の伸びの鈍化：業界（スーパー）の前年比は、予算を作った時点の直近12か月で {E['industry_yoy_12m_to_2026-03']:+.1f}%、4〜8月は {E['industry_yoy_apr_aug_2026']:+.1f}%。
- 営業利益は予算 {E['op5_budget_oku']:.2f}億円に対し実績 {E['op5_actual_oku']:.2f}億円（{E['op5_diff_pct']:+.0f}%）。実績の売上を入れて同じ作り方で利益を計算すると {e2.loc['operating_profit', '実績の売上で計算']:.2f}億円で、実績とほぼ同じ。**利益の外れは、ほぼすべて売上の外れから来ている**。

{chr(10).join(lines)}

## 次にやること
- 伸びの前提を「直近12か月」から「直近の数か月の業界の伸び」に替えて、下期の見通しを出し直す（推測：鈍化が続くかは、9月以降の数字で確かめる）。
- 費用の前提は変えない。
"""
(REP / "check_FY2026_apr_aug.md").write_text(chk, encoding="utf-8")


def md2html(t):
    import re
    out, intable = [], False
    for line in t.split("\n"):
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-"):
                continue
            tag = "th" if not intable else "td"
            if not intable:
                out.append("<table>"); intable = True
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
            continue
        if intable:
            out.append("</table>"); intable = False
        if line.startswith("# "):
            out.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("- "):
            out.append(f"<p class='li'>・{line[2:]}</p>")
        elif line[:2] in ("1.", "2.", "3."):
            out.append(f"<p class='li'>{line}</p>")
        elif line.strip():
            out.append(f"<p>{line}</p>")
    if intable:
        out.append("</table>")
    h = "\n".join(out)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", h)


css = """<style>body{font-family:'Noto Sans CJK JP','Noto Sans JP',sans-serif;margin:28px 34px;color:#222;font-size:13.5px;line-height:1.6;background:#fff}
h1{font-size:19px;border-bottom:3px solid #2563a8;padding-bottom:6px;margin:0 0 6px}h2{font-size:15px;color:#2563a8;margin:16px 0 4px}
table{border-collapse:collapse;margin:6px 0 8px;font-size:12.5px}td,th{border:1px solid #ccd;padding:3px 9px;text-align:right}th{background:#eef3fa}
td:first-child,th:first-child{text-align:left}p{margin:3px 0}p.li{margin:2px 0 2px 6px}</style>"""
(REP / "budget_FY2026_onepage.html").write_text(f"<!doctype html><html lang='ja'><head><meta charset='utf-8'>{css}</head><body>{md2html(md)}</body></html>", encoding="utf-8")
print(md)
print(chk)
