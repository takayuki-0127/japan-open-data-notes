# F255 05 報告：1枚の「振り返りの報告」（md・html）を results から作り、html を画像にして fig6 にする
# 数字はすべて data/processed/numbers.csv と results/ から入れる（手で書かない）
import json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
RES = HERE / "results"; REP = HERE / "reports"; FIG = HERE / "figures"
REP.mkdir(exist_ok=True)
N = pd.read_csv(HERE / "data/processed/numbers.csv").set_index("id")["値"]
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
A = pd.read_csv(RES / "A_before_after.csv", encoding="utf-8-sig")
Bn = M["B_range"]
C = M["C"]


def p(x, d=0):
    return f"{x:.{d}f}"


lines = []
w = lines.append
w("# 振り返りの報告：分析業務の1年（サンプルマート（架空））")
w("")
w("対象：F246〜F253 の8つの仕事（KPI・データ・月次レポート・ダッシュボード・悪い月の説明・販促の効果・予算・データの品質）。会社も数字もすべて架空の合成データ。")
w("")
w("## 結論（3行）")
w(f"1. **いちばん効いたのは「偶然の幅」を先に測ったこと**。決めた線（±3pt）では差のない店×月の{p(N.V249_fixed_false)}%に色がつき、偶然の幅なら{p(N.V249_band_false)}%。上下5店を並べると本当に差がある店は{p(N.R248_top5_true)}%、決まりで選ぶと{p(N.R248_rule_true)}%。")
w(f"2. **役に立たなかったのは、1店・1か月で営業利益を見ること**（偶然の幅 ±{p(N.N246_store_month_op)}%）と、**モデルが出す予測の区間**（80%のはずが{p(N.F252_cov_ets)}%・{p(N.F252_cov_sarima)}%しか入らない）。")
w(f"3. **来年は、偶然の幅と決めごとを1か所にまとめ、版を固定してから始める**。同じ幅を{C['noise_band_code']}つの回で計算し直し、ライブラリの版は{C['pinned'] + C['floor_only']}行のうち{C['pinned']}行しか固定していなかった。")
w("")
w("## 役に立ったもの（素朴なやり方 → 採用したやり方）")
w("| 仕事 | ものさし | 素朴 | 採用 |")
w("|---|---|---|---|")
for _, r in A.iterrows():
    w(f"| {r.回} {r.仕事} | {r.ものさし} | {p(r.素朴)}%（{r.素朴なやり方}） | {p(r.採用)}%（{r.採用したやり方}） |")
w("")
w("## 役に立たなかったもの・足りなかったもの")
w(f"- 1店・月の営業利益：偶然の幅 ±{p(N.N246_store_month_op)}%。KPI から外した（F246）")
w(f"- 予算の答え合わせ（1回）：4〜8月の売上累計が予算より {N.F252_check_diff:+.1f}%、見直しの線（{N.F252_check_lo:+.1f}〜{N.F252_check_hi:+.1f}%）の外。業界の伸びが {N.F252_ind_before:+.1f}% から {N.F252_ind_after:+.1f}% に鈍った（F252）")
w(f"- 1回の答え合わせではモデルを選べない：過去にいちばん外れた季節ナイーブが、今回はいちばん近かった（{N['F252_check_季節ナイーブ']:+.2f}%）")
w(f"- 日ごとの品質チェックは、小さな取りこぼしが見えない：売上・客数・点数がそろって1.3倍になる汚れは {p(N.Q253_x13, 1)}% しか見つからない（途中までしか入らない 0.3〜0.7倍の汚れでも {p(N.Q253_partial)}%）（F253）")
w(f"- 内訳を広げすぎると、偶然だけで外れが出る：31項目なら平均 {p(N.E250_chance_items, 1)} 項目（F250）")
w("- Power BI の .pbix は作れず、DAX は Power BI で一度も動かしていない（F249）")
w("")
w("## 来年やり直すこと（順番に）")
w("1. 偶然の幅を1つの表（95%）にして、全部の回が同じ表を読む")
w("2. 版を固定し、1つのコマンドで全部を作り直せる形にしてから始める（F254）")
w("3. 品質チェック（F253）を、月次レポート（F248）より先に置く")
w("4. 販促は、対象の店を同じ地域の対から無作為に選んでから打つ")
w("5. 予算は毎月、業界の伸びと並べて見直す（線の外に出たら、まず業界との差を見る）")
w("")
w(f"数字の出どころ：各回の results（`data/processed/numbers.csv` に {len(N)} 個、ファイルと場所つき）")
md = "\n".join(lines)
(REP / "振り返りの報告.md").write_text(md, encoding="utf-8")

# ---- html（画像用）
import re, html as H
def md2html(t):
    out = []; inlist = None; intable = False
    for l in t.split("\n"):
        l2 = H.escape(l)
        l2 = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", l2); l2 = re.sub(r"`(.+?)`", r"<code>\1</code>", l2)
        if l.startswith("|"):
            cells = [c.strip() for c in l2.strip("|").split("|")]
            if set("".join(cells)) <= set("-"):
                continue
            if not intable:
                out.append("<table>"); intable = True; tag = "th"
            else:
                tag = "td"
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"); continue
        if intable:
            out.append("</table>"); intable = False
        m1 = re.match(r"^(\d+)\. (.*)", l2); m2 = re.match(r"^- (.*)", l2)
        if m1 or m2:
            kind = "ol" if m1 else "ul"
            if inlist != kind:
                if inlist: out.append(f"</{inlist}>")
                out.append(f"<{kind}>"); inlist = kind
            out.append(f"<li>{(m1.group(2) if m1 else m2.group(1))}</li>"); continue
        if inlist:
            out.append(f"</{inlist}>"); inlist = None
        if l.startswith("# "):
            out.append(f"<h1>{l2[2:]}</h1>")
        elif l.startswith("## "):
            out.append(f"<h2>{l2[3:]}</h2>")
        elif l.strip():
            out.append(f"<p>{l2}</p>")
    if inlist: out.append(f"</{inlist}>")
    if intable: out.append("</table>")
    return "\n".join(out)

css = """body{font-family:'Noto Sans CJK JP',sans-serif;width:980px;margin:18px;color:#1a202c;font-size:13px;line-height:1.5}
h1{font-size:19px;margin:0 0 4px}h2{font-size:14.5px;margin:12px 0 4px;border-left:4px solid #2b6cb0;padding-left:6px}
p{margin:3px 0}ul,ol{margin:3px 0 3px 20px;padding:0}li{margin:1px 0}
table{border-collapse:collapse;width:100%;font-size:12px}th,td{border:1px solid #cbd5e0;padding:3px 6px;text-align:left}th{background:#edf2f7}
code{font-size:11.5px;background:#f7fafc}"""
page = f"<!doctype html><html lang='ja'><head><meta charset='utf-8'><style>{css}</style></head><body>{md2html(md)}</body></html>"
(REP / "振り返りの報告.html").write_text(page, encoding="utf-8")

from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1016, "height": 600}, device_scale_factor=1.5)
    pg.goto((REP / "振り返りの報告.html").resolve().as_uri()); pg.wait_for_timeout(300)
    pg.screenshot(path=str(FIG / "fig6_review_report.png"), full_page=True); b.close()
print(md)
