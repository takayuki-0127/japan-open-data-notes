"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：財務省・日本銀行「国際収支統計」、日本銀行「外国為替相場」（日本銀行 時系列統計データ検索サイト）をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
t = pd.read_csv(R / "annual_table.csv").set_index("year")
sh = pd.read_csv(R / "region_shares.csv").set_index("year")

# 図1 受取の内訳
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.bar(t.index, t.ind_rec, color=C[0], width=0.8, label="産業財産権等使用料（特許・技術など）")
ax.bar(t.index, t.cr_rec, bottom=t.ind_rec, color=C[1], width=0.8, label="著作権等使用料（作品・ソフトウェアなど）")
ax.text(2025, t.loc[2025, "ip_rec"] + 0.12, f"{t.loc[2025,'ip_rec']:.1f}", ha="center", fontsize=9)
ax.set_ylabel("受取（兆円、暦年）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"2025年の知的財産権等使用料の受取{m['ip_rec_2025']:.1f}兆円のうち、著作権は{m['cr_rec_2025']:.2f}兆円（{m['cr_share_2025']:.0f}%）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig1_receipts_breakdown.png", SRC)

# 図2 2014年＝100（円とドル）
s = t.loc[2014:2025]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, lab, c, ls in [("cr_rec", "著作権（円）", C[1], "-"), ("cr_rec_usd", "著作権（ドル）", C[1], "--"), ("ind_rec", "産業財産権（円）", C[0], "-"), ("ind_rec_usd", "産業財産権（ドル）", C[0], "--")]:
    v = s[col] / s.loc[2014, col] * 100
    ax.plot(v.index, v, color=c, ls=ls, lw=2.2, label=lab)
    ax.text(2025.2, v.iloc[-1], f"{v.iloc[-1]:.0f}", fontsize=9, color=c, va="center")
ax.set_xlim(2013.5, 2026.3); ax.set_xticks(range(2014, 2026, 2))
ax.set_ylabel("2014年＝100")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"著作権の受取はドルで{m['cr_usd_ratio']:.1f}倍、特許などはドルで{m['ind_usd_ratio']:.2f}倍（2014→2025年）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.14)
save(fig, F / "fig2_growth_yen_usd.png", SRC, f"注：ドル建ては月ごとの値をその月のドル円で割って合計。著作権の受取は2014年{m['cr_usd_2014']:.1f}億ドル→2025年{m['cr_usd_2025']:.1f}億ドル。")

# 図3 地域別の割合（受取の合計）
regs = [("北米", C[0]), ("アジア", C[1]), ("欧州", C[2]), ("中南米", C[3]), ("その他", C[5])]
s2 = sh.copy()
s2["その他"] = 100 - s2[["北米", "アジア", "欧州", "中南米"]].sum(axis=1)
fig, ax = plt.subplots(figsize=(8.8, 5.0))
bottom = np.zeros(len(s2))
for rg, c in regs:
    ax.bar(s2.index, s2[rg], bottom=bottom, color=c, width=0.75, label=rg)
    bottom += s2[rg].values
ax.set_ylim(0, 100)
ax.set_ylabel("知的財産権等使用料の受取に占める割合（%）")
ax.legend(frameon=False, loc="upper center", ncol=5, fontsize=9, bbox_to_anchor=(0.5, -0.08))
ax.set_title(f"受取の相手は北米が{m['region_na_2025']:.0f}%（米国{m['region_us_2025']:.0f}%）、アジアは{m['region_asia_2014']:.0f}%→{m['region_asia_2025']:.0f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.2)
save(fig, F / "fig3_region_shares.png", SRC, "注：地域別は知的財産権等使用料の合計（著作権と産業財産権を分けた地域別はない）。四半期の値を暦年に合計。地域は北から南ではなく金額の大きい順に積んだ。")

# 図4 著作権の受取と支払
s = t.loc[1996:2025]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(s.index, s.cr_rec, color=C[1], lw=2.2, label="著作権等使用料 受取")
ax.plot(s.index, s.cr_pay, color=C[0], lw=2.2, label="著作権等使用料 支払")
ax.bar(s.index, s.cr_net, color=C[5], width=0.75, alpha=0.6, label="ネット（受取−支払）")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("兆円（暦年）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"受取は支払の{q['cover_2014']:.0f}%（2014年）→{q['cover_2025']:.0f}%（2025年）。それでも赤字は{-q['cr_net_2014']:.1f}→{-q['cr_net_2025']:.1f}兆円に", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig4_copyright_rec_pay.png", SRC)
