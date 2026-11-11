# F231 図（4枚）とダッシュボード（HTML）
import json, base64, io, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f: font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["axes.spines.top"] = False; plt.rcParams["axes.spines.right"] = False
COL = {"季節ナイーブ": "#9e9e9e", "季節ナイーブ＋伸び": "#bcaaa4", "ETS": "#1f77b4", "SARIMA": "#d62728", "LightGBM": "#2ca02c"}
d = pd.read_csv("data/sales_monthly_6types.csv"); d["ym"] = pd.to_datetime(d.ym)
A = pd.read_csv("results/A_mape_by_h.csv", index_col=0); o = json.load(open("results/main.json"))
m = pd.read_csv("results/forecasts_main.csv.gz"); m["ape"] = (m["予測"] / m["実績"] - 1).abs() * 100
m["covid"] = (m["対象月"] >= "2020-03") & (m["対象月"] <= "2021-12")
TYPES = ["百貨店", "スーパー", "コンビニ", "ドラッグストア", "ホームセンター", "家電大型専門店"]

# 図1 データ：6業態の販売額（2014年の平均=100）
fig, ax = plt.subplots(figsize=(9, 4.8))
for k in TYPES:
    s = d[d.業態 == k].set_index("ym")["販売額_百万円"]; ax.plot(s.index, s / s["2014"].mean() * 100, lw=1.2, label=k)
ax.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-12-31"), color="#eee", zorder=0)
ax.text(pd.Timestamp("2020-04-01"), ax.get_ylim()[1] * 0.97, "コロナ期\n（採点しない）", fontsize=9, va="top", color="#666")
ax.set_ylabel("2014年の平均＝100"); ax.set_title("図1　業態別の月次販売額（商業動態統計、2014年1月〜2026年8月）", loc="left", fontsize=12)
ax.legend(ncol=3, fontsize=9, frameon=False); fig.tight_layout(); fig.savefig("figures/fig1_data.png", dpi=150); plt.close()

# 図2 予測の地平ごとの外れ
fig, ax = plt.subplots(figsize=(9, 4.8))
for c in A.columns: ax.plot(A.index, A[c], marker="o", ms=3, lw=1.8 if c in ("ETS", "SARIMA") else 1.2, color=COL[c], label=c)
ax.axvline(12.5, color="#888", ls=":", lw=1); ax.text(12.7, ax.get_ylim()[1] * 0.95, "ここから2年目", fontsize=9, color="#555", va="top")
ax.set_xlabel("何か月先を予測したか（h）"); ax.set_ylabel("外れの平均（MAPE, %）"); ax.set_xticks([1, 3, 6, 9, 12, 15, 18, 21, 24])
ax.set_title("図2　何か月先を当てるかで、外れはどう変わるか（6業態・47回の起点の平均）", loc="left", fontsize=12)
ax.legend(fontsize=9, frameon=False, ncol=3); fig.tight_layout(); fig.savefig("figures/fig2_mape_by_h.png", dpi=150); plt.close()

# 図3 業態別：季節ナイーブに対する改善（スキル）
x = m[~m.covid].groupby(["業態", "モデル", "h"]).ape.mean().unstack(1)
fig, ax = plt.subplots(figsize=(9, 4.8))
for k in TYPES:
    g = x.loc[k]; best = g.drop(columns="季節ナイーブ").min(axis=1); ax.plot(g.index, (1 - best / g["季節ナイーブ"]) * 100, marker="o", ms=3, label=k)
ax.axhline(0, color="#333", lw=1); ax.set_xticks([1, 3, 6, 9, 12, 15, 18, 21, 24])
ax.set_xlabel("何か月先を予測したか（h）"); ax.set_ylabel("去年の同じ月より何%外れが小さいか")
ax.set_title("図3　「去年と同じ」に比べて、いちばん良いモデルはどれだけ良いか（業態別）", loc="left", fontsize=12)
ax.legend(ncol=3, fontsize=9, frameon=False); fig.tight_layout(); fig.savefig("figures/fig3_skill_by_type.png", dpi=150); plt.close()

# 図4 年間予算（12月の起点から翌年・翌々年の合計）
C = pd.read_csv("results/C_annual_budget.csv", index_col=0).loc[list(COL)]
fig, ax = plt.subplots(figsize=(9, 4.6)); w = 0.38; xx = np.arange(len(C))
b1 = ax.bar(xx - w / 2, C["1年目"], w, color=[COL[c] for c in C.index], label="翌年（1年目）")
b2 = ax.bar(xx + w / 2, C["2年目"], w, color=[COL[c] for c in C.index], alpha=0.45, hatch="//", label="翌々年（2年目）")
for b in list(b1) + list(b2): ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.08, f"{b.get_height():.1f}", ha="center", fontsize=9)
ax.set_xticks(xx); ax.set_xticklabels(C.index); ax.set_ylabel("年間合計の外れ（%、平均）")
ax.set_title("図4　年間の合計（予算の数字）で見ると、外れはどれだけか（12月時点の予測）", loc="left", fontsize=12)
ax.legend(fontsize=9, frameon=False); fig.tight_layout(); fig.savefig("figures/fig4_annual_budget.png", dpi=150); plt.close()

# ダッシュボード（静的 HTML）：起点 2024-08 の予測と、地平ごとの外れの目安
last = m[m.起点 == m.起点.max()]
cards, rows = [], []
for k in TYPES:
    s = d[d.業態 == k].set_index("ym")["販売額_百万円"]
    sar = last[(last.業態 == k) & (last.モデル == "SARIMA")]
    fig, ax = plt.subplots(figsize=(4.2, 2.2))
    ax.plot(s["2021":].index, s["2021":] / 1e3, color="#444", lw=1)
    t = pd.to_datetime(sar.対象月); ax.plot(t, sar.予測 / 1e3, color="#d62728", lw=1.2)
    ax.fill_between(t, sar.下80 / 1e3, sar.上80 / 1e3, color="#d62728", alpha=0.15)
    ax.set_title(k, fontsize=10, loc="left"); ax.tick_params(labelsize=7); fig.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=110); plt.close(); cards.append((k, base64.b64encode(buf.getvalue()).decode()))
B = pd.DataFrame(o["B"]).set_index("業態")
for k in TYPES:
    r = B.loc[k]; ok = "◎" if r.skill_h12 > 0.1 else ("○" if r.skill_h12 > 0 else "△")
    rows.append(f"<tr><td>{k}</td><td>{r.h1_best:.1f}%</td><td>{r.h12_best:.1f}%</td><td>{r.h24_best:.1f}%</td><td>{int(r.skill_pos_last_h)}か月</td><td>{ok}</td></tr>")
html = f"""<!doctype html><html lang="ja"><meta charset="utf-8"><title>F231 売上予測の見方（例）</title>
<style>body{{font-family:'Noto Sans CJK JP',sans-serif;margin:24px;color:#222;background:#fafafa}}h1{{font-size:20px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.card{{background:#fff;border:1px solid #ddd;border-radius:6px;padding:6px}}
table{{border-collapse:collapse;background:#fff;margin-top:12px;font-size:13px}}td,th{{border:1px solid #ccc;padding:4px 10px;text-align:right}}td:first-child{{text-align:left}}
.note{{font-size:12px;color:#555;margin-top:10px;line-height:1.6}}</style>
<h1>売上予測の見方ダッシュボード（例：商業動態統計・6業態）</h1>
<div class="note">縦軸＝販売額（十億円）。赤線＝2024年8月時点の SARIMA の予測、帯＝80%区間、黒線＝実績。下の表は、過去47回の起点で確かめた「何か月先まで当たるか」の目安。</div>
<div class="grid">{''.join(f'<div class="card"><img src="data:image/png;base64,{b}" width="100%"></div>' for k,b in cards)}</div>
<table><tr><th>業態</th><th>1か月先の外れ</th><th>12か月先</th><th>24か月先</th><th>「去年と同じ」より良い最後の月（24か月まで）</th><th>12か月先の使いやすさ</th></tr>{''.join(rows)}</table>
<div class="note">外れ＝いちばん良いモデルの MAPE（コロナ期の月は除く）。◎＝12か月先でも「去年と同じ」より1割以上良い、○＝少し良い、△＝良くない。公開データで作った例で、実在の会社の数字ではありません。</div></html>"""
open("dashboard/index.html", "w", encoding="utf-8").write(html)
print("ok")
