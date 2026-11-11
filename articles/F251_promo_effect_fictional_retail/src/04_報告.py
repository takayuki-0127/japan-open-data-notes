"""04 報告：効果測定の報告（1枚）を書く。reports/promo_effect_report.md と .html。

報告は「実務で答えを知らない担当者」が書く形にした。主に使う測り方は合成対照、確かめに差の差（店ごとの傾きあり・なし）。
答え（入れた効果）との比べは記事と README で行い、報告には書かない。
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; REP = ROOT / "reports"; REP.mkdir(exist_ok=True)
m = json.load(open(RES / "main.json"))
A = pd.read_csv(RES / "A_estimates_seed0.csv").set_index("method")
S = pd.read_csv(RES / "C_error_summary.csv")
S = S[S.case == "weak_eff"].set_index("method")
MN = pd.read_csv(RES / "C_money_error.csv").set_index("method")
pt = m["placebo_time"]; ps = m["placebo_space"]
EV = pd.read_csv(RES / "A_event_study_seed0.csv"); EV = EV[EV.trend == 0].set_index("k").coef
ev_early, ev_late = EV.loc[-52:-40].mean(), EV.loc[-13:-2].mean()
SEL = pd.read_csv(RES / "A_selection_yoy.csv")

pc = lambda v: f"{v * 100:+.1f}%"
oku = lambda v: f"{v / 1e6:+.1f}百万円"
sc, did, dt = A.loc["M6_合成対照"], A.loc["M4_DiD"], A.loc["M5_DiD傾き"]
h = S.loc["M6_合成対照", "half90"]
hn = 1.645 * MN.loc["M6_合成対照", "net_sd"]
lo, hi = sc.promo_lift - h, sc.promo_lift + h

md = f"""# 会員アプリの来店クーポン　効果測定の報告（サンプルマート（架空））

対象：地方の6店（17・18・19・20・22・23店）　期間：2025年10月6日〜11月30日（8週）　作成：分析担当

## 結論
1. **売上は、販促がなかった場合より {pc(sc.promo_lift)} 多かった（90%の幅 {pc(lo)}〜{pc(hi)}）。** 8週で {sc.inc_sales_promo / 1e6:.0f}百万円。
2. **増えた粗利 {sc.inc_gp_total / 1e6:.1f}百万円 − クーポン {m['truth']['promo']['coupon'] / 1e6:.1f}百万円 − 固定費 0.6百万円 ＝ 差し引き {oku(sc.net)}**（幅 ±{hn / 1e6:.0f}百万円）。黒字の見込みが高いが、赤字の可能性も残る。
3. 前年比（{pc(A.loc['M2_前年比', 'promo_lift'])}）と、対象外の店との前年比の差（{pc(A.loc['M3_前年比の差', 'promo_lift'])}）は、効果の数字として使わない（理由は下）。

## 数字
| 測り方 | 効果（8週） | 差し引き | この測り方の弱いところ |
|---|---|---|---|
| **合成対照（主に使う）** | **{pc(sc.promo_lift)}** | **{oku(sc.net)}** | 地方の店がほかにないので、郊外・都市の店の組み合わせで代わりを作っている |
| 差の差 | {pc(did.promo_lift)} | {oku(did.net)} | 期間の前から、対象の店は相手より少しずつ下がっていた（下の確かめ1） |
| 差の差＋店ごとの傾き | {pc(dt.promo_lift)} | {oku(dt.net)} | 7〜9月が弱かった店を選んだので、傾きを下に引きすぎやすい |
| 前年比 | {pc(A.loc['M2_前年比', 'promo_lift'])} | — | 値上がり（一品単価 +4%前後）がそのまま入る |
| 前年比の差 | {pc(A.loc['M3_前年比の差', 'promo_lift'])} | — | 地方の店は前年比が低い流れが続いている（7〜9月の前年比の低い6店がすべて地方）。都市・郊外と比べると低く出る |
| 前後比較（直前8週） | {pc(A.loc['M1_前後', 'promo_lift'])} | — | 季節（9月→10・11月）と値上がりが入る |

幅は、同じ選び方・同じ測り方を、偶然の揺れだけを変えた20通りに当てて測った（90%）。

## 確かめたこと
1. **期間の前の動き**：差の差の形で週ごとに見ると（直前の週を0とする）、対象の6店は1年前（期間の52〜40週前）に相手より平均 {pc(ev_early)}、直前の3か月（13〜2週前）に {pc(ev_late)} と、少しずつ下がっていた。差の差は効果を低めに出しやすい。
2. **1年前に偽の販促を置く**：同じ6店・同じ8週の1年前で測ると、差の差 {pc(pt['M4_DiD'])}、合成対照 {pc(pt['M6_合成対照'])}、傾きあり {pc(pt['M5_DiD傾き'])}（本当は 0%）。
3. **店を入れ替える**：対象外の14店から6店を選んで偽の対象にした200通りでは、合成対照の偽の効果は {pc(ps['M6_合成対照']['q05'])}〜{pc(ps['M6_合成対照']['q95'])}（90%）。今回の {pc(sc.promo_lift)} はその外。ただし相手の店はすべて都市・郊外なので、地方の流れの違いはこの確かめに入っていない。

## 理由にしないもの
- 12月（期間の後の4週）の残りの効果：測り方で {pc(min(A.loc[k, 'after_lift'] for k in ['M4_DiD', 'M5_DiD傾き', 'M6_合成対照']))}〜{pc(max(A.loc[k, 'after_lift'] for k in ['M4_DiD', 'M5_DiD傾き', 'M6_合成対照']))} と割れ、幅の中。年末の動きも大きい。

## 次にやること
- 続けるなら、**対象の店を「弱い店」ではなく、同じ地域・同じ大きさの店の対から無作為に選ぶ**。今回のように地方の店がすべて対象だと、比べる相手がいない。
- 測り方（合成対照、確かめに差の差）と判断の線（差し引きが黒字か）を、始める前に決めて残す。
- 2〜3月の売上が出たら、残りの効果がないかをもう一度見る。
"""
(REP / "promo_effect_report.md").write_text(md, encoding="utf-8")

# HTML（図6の画像用）
import re, html as H
def md2html(t):
    out, intable = [], False
    for line in t.splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            tag = "th" if not intable else "td"
            if not intable: out.append("<table>"); intable = True
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"); continue
        if intable: out.append("</table>"); intable = False
        if line.startswith("# "): out.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "): out.append(f"<h2>{line[3:]}</h2>")
        elif re.match(r"^\d+\. ", line): out.append(f"<p class='li'>{line}</p>")
        elif line.startswith("- "): out.append(f"<p class='li'>・{line[2:]}</p>")
        elif line.strip(): out.append(f"<p>{line}</p>")
    if intable: out.append("</table>")
    s = "\n".join(out)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)

css = """body{font-family:'Noto Sans CJK JP';width:980px;margin:24px;color:#1d1d1b;font-size:14px;line-height:1.55;background:#fff}
h1{font-size:21px;border-bottom:3px solid #2a78d6;padding-bottom:6px;margin:0 0 6px}
h2{font-size:16px;margin:14px 0 4px;color:#2a78d6}
p{margin:3px 0} p.li{margin:3px 0 3px 10px}
table{border-collapse:collapse;width:100%;margin:6px 0;font-size:13px} td,th{border:1px solid #d0cfca;padding:4px 6px;text-align:left}
th{background:#f1f0ec} .note{font-size:11px;color:#6b6a66;margin-top:10px}"""
body = md2html(md) + "<p class='note'>サンプルマート（架空）・合成データ。会社も数字も実在しません。</p>"
(REP / "promo_effect_report.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>", encoding="utf-8")
print(md)
