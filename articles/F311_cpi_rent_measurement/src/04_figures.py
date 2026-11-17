"""図を作る（PNG、メタデータなし）。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES, FIG = ROOT / "data", ROOT / "results", ROOT / "figures"; FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e"})
C6 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
GRAY, INK2 = "#9a9893", "#52514e"
SRC_C = "出典：総務省「消費者物価指数」（品目別、暦年の年平均）、「住宅・土地統計調査」第34-1表をもとに作成者が加工"
SRC_J = "出典：総務省「令和5年住宅・土地統計調査」第27表（全国、民営借家）をもとに作成者が加工"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
cpi = pd.read_csv(D / "cpi_rent_annual.csv").set_index("year")
comp = pd.read_csv(RES / "cpi_vs_jutaku_by_year.csv", index_col=0)
def save(fig, name, src):
    fig.text(0.01, 0.01, src, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)

# 図1：長い目で見た CPI と住調（2003年=100）
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.8, top=0.83, bottom=0.14)
c = cpi.loc[1973:2025, "private_rent"]; ax.plot(c.index, 100 * c / c.loc[2003], color=C6[0], lw=2)
ax.text(2025.6, 88, "CPI 民営家賃\n（同じ住宅を追う）", fontsize=8.5, va="center", color=C6[0])
for k, (col, lab) in enumerate([("tatami_nonwood", "住調 民営借家・非木造\n（1畳当たり家賃）"), ("tatami_wood", "住調 民営借家・木造\n（1畳当たり家賃）")]):
    s = comp[col].dropna(); ax.plot(s.index, 100 * s / s.loc[2003], color=C6[k + 1], lw=1.6, marker="o", ms=5)
    ax.text(2025.6, 114 if k else 101, lab, fontsize=8.5, va="center", color=C6[k + 1])
ax.axhline(100, color=GRAY, lw=0.6, ls=":")
ax.set_ylabel("指数（2003年＝100）"); ax.set_xlabel("年"); ax.set_ylim(0, 120); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("1990年代の終わりから、CPI の家賃は横ばい。住調の家賃は2018年から上がった", x=0.02, ha="left", fontsize=12.5, y=0.97)
H1 = m["H1"]
fig.text(0.02, 0.885, f"2003→2023年（対数差×100）：住調の民営借家 {H1['jutaku']:+.1f}（木造・非木造を借家数で重みづけ）、CPI 民営家賃 {H1['cpi']:+.1f}", fontsize=9, color=INK2)
save(fig, "fig1_cpi_vs_survey_rent.png", SRC_C)

# 図2：建築時期別の1畳当たり家賃（2023年）
t = pd.read_csv(D / "t27_cells.csv")
g = t[(t.tenure == "private") & (t.movein == "総数") & (t.construction != "総数") & (t.section == "rent_per_tatami")]
LAB = {"昭和25年以前に建築": "〜1950", "昭和26年～45年": "51〜70", "昭和46年～55年": "71〜80", "昭和56年～平成２年": "81〜90", "平成３年～12年": "91〜2000",
       "平成13年～17年": "01〜05", "平成18年～22年": "06〜10", "平成23年～27年": "11〜15", "平成28年～令和２年": "16〜20", "令和３年～５年９月": "21〜23"}
fig, ax = plt.subplots(figsize=(8.4, 4.9)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.17)
x = np.arange(len(g)); cols = [C6[0] if c in ("平成３年～12年", "平成28年～令和２年") else "#86b6ef" for c in g.construction]
ax.bar(x, g.value, color=cols, width=0.7)
for xi, v in zip(x, g.value): ax.text(xi, v + 60, f"{v:,.0f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([LAB[c] for c in g.construction]); ax.set_xlabel("建築の時期（年）"); ax.set_ylabel("1畳当たり家賃（円／月）"); ax.set_ylim(0, 6000)
ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("新しい建物ほど、1畳当たりの家賃は高い", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"民営借家、2023年。2016〜20年建築は1991〜2000年建築より {m['H2']['new_2016_20_vs_1991_2000']:.0f}（対数差×100）高い。入居時期をそろえると、1年古いごとに約{-m['H4']['slope_per_year']:.1f}%低い", fontsize=9, color=INK2)
save(fig, "fig2_rent_by_construction.png", SRC_J)

# 図3：新しい契約の上乗せ（建築時期別）
p = pd.read_csv(RES / "requestion_premium_by_construction.csv").sort_values("age", ascending=False)
fig, ax = plt.subplots(figsize=(8.4, 4.9)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.17)
x = np.arange(len(p)); w = 0.38
ax.bar(x - w / 2, p.old_rent_wavg, w, color=GRAY, label="2015年以前に入居")
ax.bar(x + w / 2, p.new_rent, w, color=C6[0], label="2021〜23年に入居")
for xi, v, pr in zip(x + w / 2, p.new_rent, p.premium): ax.text(xi, v + 60, f"+{pr:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([LAB[c] for c in p.construction]); ax.set_xlabel("建築の時期（年）"); ax.set_ylabel("1畳当たり家賃（円／月）"); ax.set_ylim(0, 5000)
ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.suptitle("同じ時期に建った住宅でも、最近入った世帯のほうが高い", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"民営借家、2023年。数字は上乗せ（対数差×100）。建築時期をそろえた回帰で +{m['H3']['new_vs_old']:.1f}（標準誤差 {m['H3']['new_se']:.1f}）", fontsize=9, color=INK2)
save(fig, "fig3_new_contract_premium.png", SRC_J)

# 図4：経年の分を足し戻した CPI（試算）
yrs = np.arange(2003, 2024)
c = cpi.loc[2003:2023, "private_rent"]; base = 100 * c / c.loc[2003]
b = -m["H4"]["slope_per_year"]
adj = base * np.exp(b / 100 * (yrs - 2003))
wj = comp.loc[[2003, 2008, 2013, 2018, 2023]]
ww = m["w_wood_2023"]
jj = 100 * np.exp(ww * np.log(wj.tatami_wood / wj.tatami_wood.loc[2003]) + (1 - ww) * np.log(wj.tatami_nonwood / wj.tatami_nonwood.loc[2003]))
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.78, top=0.83, bottom=0.14)
ax.plot(yrs, base, color=C6[0], lw=2); ax.text(2023.5, base.iloc[-1], "CPI 民営家賃", fontsize=9, va="center")
ax.plot(yrs, adj, color=C6[1], lw=2, ls="--"); ax.text(2023.5, adj.iloc[-1], f"経年の分（年 約{b:.1f}%）を\n足し戻した試算", fontsize=9, va="center")
ax.plot(jj.index, jj, color=C6[2], lw=1.6, marker="o", ms=5); ax.text(2023.5, jj.iloc[-1], "住調 民営借家\n（1畳当たり）", fontsize=9, va="center")
ax.axhline(100, color=GRAY, lw=0.6, ls=":")
ax.set_ylabel("指数（2003年＝100）"); ax.set_xlabel("年"); ax.set_ylim(85, 125); ax.set_xticks([2003, 2008, 2013, 2018, 2023]); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("建物が古くなる分を足し戻すと、CPI の家賃も上がって見える（試算）", x=0.02, ha="left", fontsize=12.5, y=0.97)
fig.text(0.02, 0.885, f"2003→2023年（対数差×100）：CPI {m['H1']['cpi']:+.1f}、足し戻した試算 {m['H4']['cpi_adjusted_2003_2023']:+.1f}、住調 {m['H1']['jutaku']:+.1f}。経年の率は2023年の1時点の比較からの推測", fontsize=9, color=INK2)
save(fig, "fig4_aging_adjusted_cpi.png", SRC_C + "、同 第27表")
print("ok")
