"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：財務省・日本銀行「本邦対外資産負債残高」「国際収支統計」、内閣府「国民経済計算」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
a = pd.read_csv(R / "annual_table.csv").set_index("year")

# 図1 残高と GDP 比
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.bar(a.index, a.inward, color=C[0], width=0.75, label="対内直接投資残高（年末、兆円）")
ax.plot(a.index, a.inward_mv, color=C[0], lw=1.4, ls="--", marker="o", ms=3, label="同 時価の推計値（参考）")
ax.text(2025, a.loc[2025, "inward"] + 1.5, f"{a.loc[2025,'inward']:.1f}", ha="center", fontsize=9)
ax.set_ylabel("兆円")
ax2 = ax.twinx(); ax2.plot(a.index, a.gdp_ratio, color=C[1], lw=2.2, label="名目GDP比（右軸、%）"); ax2.set_ylim(0, 12); ax2.set_ylabel("名目GDP比（%）"); ax2.spines["top"].set_visible(False)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"対内直接投資残高は2014年{m['inward_2014']:.1f}兆円→2025年{m['inward_2025']:.1f}兆円（{m['inward_mult_2014_2025']:.1f}倍）。GDP比は{m['gdp_ratio_2024']:.1f}%", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.08, right=0.92, top=0.91, bottom=0.14)
save(fig, F / "fig1_inward_stock.png", SRC, "注：GDP比は2024年まで（2025年の暦年の名目GDPは未公表）。")

# 図2 対外との比
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.plot(a.index, a.outward, color=C[2], lw=2.2, label="対外直接投資残高（兆円）")
ax.plot(a.index, a.inward, color=C[0], lw=2.2, label="対内直接投資残高（兆円）")
ax.set_ylabel("兆円（年末）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"対内は対外の{m['in_out_2025']:.0f}%（2025年）。2014年の{m['in_out_2014']:.0f}%からむしろ下がった", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.14)
save(fig, F / "fig2_inward_vs_outward.png", SRC)

# 図3 年ごとの流れと残高の増加
t = pd.read_csv(R / "yearly_flows.csv").set_index("year")
fig, ax = plt.subplots(figsize=(8.8, 5.0))
pos = np.zeros(len(t)); neg = np.zeros(len(t))
for c, lab, col in [("flow_equity", "株式資本（新しい出資など）", C[0]), ("flow_reinv", "収益の再投資", C[3]), ("flow_debt", "負債性資本（親子間の貸し借り）", C[2]), ("other", "評価の変化など（残差）", C[5])]:
    v = t[c].values; b = np.where(v >= 0, pos, neg)
    ax.bar(t.index, v, bottom=b, color=col, width=0.7, label=lab)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.plot(t.index, t.increase, color=INK, marker="o", ms=4, lw=1.4, label="残高の増加")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("兆円（暦年）")
ax.legend(frameon=False, loc="upper left", fontsize=8.6, ncol=2)
ax.set_ylim(-4.5, 11)
style(ax)
ax.set_title(f"2015〜25年の流れの{q['reinv_share_of_flows']:.0f}%は再投資、新しい出資は{q['equity_share_of_flows']:.0f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig3_flows.png", SRC, "注：流れは国際収支の金融収支 直接投資（負債）のネット。残差＝残高の増加−流れ（為替や株価などによる評価の変化、統計の調整）。")

# 図4 地域の割合
sh = pd.read_csv(R / "region_shares.csv").set_index("year")
regs = [("欧州", C[2]), ("北米", C[0]), ("アジア", C[1]), ("中南米", C[3]), ("その他", C[5])]
sh["その他"] = 100 - sh[["欧州", "北米", "アジア", "中南米"]].sum(axis=1)
fig, ax = plt.subplots(figsize=(8.8, 5.0))
b = np.zeros(len(sh))
for rg, c in regs:
    ax.bar(sh.index, sh[rg], bottom=b, color=c, width=0.75, label=rg); b += sh[rg].values
ax.set_ylim(0, 100); ax.set_ylabel("対内直接投資残高に占める割合（%）")
ax.legend(frameon=False, loc="upper center", ncol=5, fontsize=9, bbox_to_anchor=(0.5, -0.08))
ax.set_title(f"アジアからは{m['region_asia_2014']:.0f}%→{m['region_asia_2025']:.0f}%、北米は{m['region_na_2014']:.0f}%→{m['region_na_2025']:.0f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.2)
save(fig, F / "fig4_region_shares.png", SRC, "注：地域は直接の投資家の所在地（最終的な親会社の国とは違うことがある）。金額の大きい順に積んだ。")
