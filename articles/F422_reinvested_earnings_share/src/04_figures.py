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
a = pd.read_csv(D / "annual.csv").set_index("year")
s = pd.read_csv(R / "annual_shares.csv").set_index("year")

# 図1 直接投資収益の受取の内訳
fig, ax = plt.subplots(figsize=(8.8, 5.0))
parts = [("di_div_rec", "配当金・配分済支店収益", C[1]), ("di_reinv_rec", "再投資収益（海外に残した分）", "#f2a27f"), ("di_int_rec", "利子", C[5])]
pos = np.zeros(len(a)); neg = np.zeros(len(a))
for c, lab, col in parts:
    v = a[c].values / 1e4
    bottom = np.where(v >= 0, pos, neg)
    ax.bar(a.index, v, bottom=bottom, color=col, width=0.8, label=lab)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("兆円（暦年、受取）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"2025年の直接投資収益の受取{m['di_rec_2025']:.1f}兆円のうち、再投資収益は{m['reinv_rec_2025']:.1f}兆円", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig1_di_receipts.png", SRC)

# 図2 再投資収益の割合
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(s.index, s.reinv_share_rec, color=C[1], lw=2.2, marker="o", ms=3.5)
for (y0, y1) in [(1996, 2005), (2021, 2025)]:
    v = s.loc[y0:y1, "reinv_share_rec"].mean()
    ax.hlines(v, y0 - 0.4, y1 + 0.4, color=INK2, lw=1.4, ls="--")
    ax.text((y0 + y1) / 2, v + 3, f"{y0}〜{str(y1)[2:]}年の平均 {v:.1f}%", ha="center", fontsize=8.8, color=INK2)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylim(-35, 70)
ax.set_ylabel("直接投資収益の受取に占める再投資収益（%）")
style(ax)
ax.set_title(f"海外に残す割合は約3割から5割弱へ。ただし2016年の{m['reinv_share_max']:.0f}%が山で、2025年は{m['reinv_share_2025']:.0f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.17)
save(fig, F / "fig2_reinvested_share.png", SRC, "注：1998年は再投資収益が負（海外子会社の配当が利益を上回ったか、損失が出た）。")

# 図3 経常収支と、再投資収益を除いた経常収支
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(s.index, s.ca, color=C[0], lw=2.2, label="経常収支")
ax.plot(s.index, s.ca_ex_reinv, color=C[1], lw=2.2, label="経常収支 − 再投資収益（ネット）")
ax.fill_between(s.index, s.ca_ex_reinv, s.ca, color=C[1], alpha=0.12, lw=0)
ax.axhline(0, color=INK2, lw=0.8)
ax.text(2025.2, s.loc[2025, "ca"], f"{s.loc[2025,'ca']:.1f}", fontsize=9, color=C[0], va="center")
ax.text(2025.2, s.loc[2025, "ca_ex_reinv"], f"{s.loc[2025,'ca_ex_reinv']:.1f}", fontsize=9, color=C[1], va="center")
ax.set_xlim(1995.5, 2027)
ax.set_ylabel("兆円（暦年）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"再投資収益を除くと、2025年の経常黒字は{m['ca_ex_reinv_2025']:.1f}兆円（{m['ca_ex_ratio_2025']:.0f}%）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.17)
save(fig, F / "fig3_ca_ex_reinvested.png", SRC, f"注：再投資収益（ネット）＝受取（日本企業の海外子会社の分）−支払（外国企業の日本の子会社の分）。2022年は {q['ca_ex_reinv_2022']:.1f}兆円まで縮む。")

# 図4 ドル円の前年比と、再投資の割合の前年差
dfx = np.log(s.usdjpy).diff() * 100
dsh = s.reinv_share_rec.diff()
ok = dfx.notna() & dsh.notna()
fig, ax = plt.subplots(figsize=(7.8, 5.6))
ax.scatter(dfx[ok], dsh[ok], color=C[0], s=30)
for y in [1998, 2008, 2013, 2016, 2022, 2025]:
    if ok.loc[y]:
        ax.annotate(str(y), (dfx.loc[y], dsh.loc[y]), xytext=(4, 3), textcoords="offset points", fontsize=8.5, color=INK2)
b = np.polyfit(dfx[ok], dsh[ok], 1)
xx = np.array([dfx[ok].min(), dfx[ok].max()])
ax.plot(xx, np.polyval(b, xx), color=INK2, lw=1)
ax.axhline(0, color=GRID, lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
ax.set_xlabel("ドル円の前年比（%、正は円安）")
ax.set_ylabel("再投資収益の割合の前年差（ポイント）")
ax.set_title(f"円安の年は、海外に残す割合が下がる傾向が弱く見られる（相関 {m['corr_fx_change_vs_share_change']:.2f}）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.12, right=0.97, top=0.92, bottom=0.17)
save(fig, F / "fig4_fx_vs_share.png", SRC, f"注：1997〜2025年。円安が5%を超えた年の平均 {q['share_change_yen_weak_mean']:+.1f}ポイント、円高が5%を超えた年の平均 {q['share_change_yen_strong_mean']:+.1f}ポイント。")
