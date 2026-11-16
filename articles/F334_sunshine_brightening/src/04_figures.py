"""04 図：fig1〜fig4（PNG、日付などのメタデータなし）。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
RES = ROOT / "results"
p = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if pathlib.Path(p).exists():
    fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e5e0",
                     "grid.linewidth": 0.6, "axes.axisbelow": True})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK2 = "#52514e"
SRC = "出典：気象庁「過去の気象データ検索（年ごとの値）」をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
MM, A = M["main"], M["adjusted"]
Y = pd.read_csv(RES / "yearly.csv", index_col=0)


def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


# fig1 日照時間（そのまま）
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(Y.index, Y.sun_idx, color=C[0], lw=1.6, marker="o", ms=3)
ax.axvline(1985.5, color=C[1], lw=1.2, ls="--")
ax.text(1986.2, 122, "1986年：ジョルダン式日照計の\n使用が終わったころ", fontsize=8.5, color=INK2, va="top")
ax.text(1962, 66, f"1961〜1965年 {M['sun_idx_1961_1965']:.0f}　→　最も少ない5年（{M['sun_idx_min5_year'] - 2}〜{M['sun_idx_min5_year'] + 2}年）{M['sun_idx_min5']:.0f}　→　2021〜2025年 {M['sun_idx_2021_2025']:.0f}",
        fontsize=8.5, color=INK2)
ax.set_ylim(60, 125)
ax.set_xlabel("年"); ax.set_ylabel("年間日照時間（1991〜2020年平均＝100）")
ax.set_title("そのままの日照時間は「減ってから増えた」ように見える", loc="left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig1_sunshine_raw.png", f"1961〜2025年に60年以上の値がある{MM['n_sun']}地点（気象台など）の指数の中央値。縦軸は60から")

# fig2 日照時間÷全天日射量の比
Q = pd.read_csv(RES / "ratio_yearly.csv", index_col=0)
Q = Q.loc[1961:2025]
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(Q.index, Q.ratio_idx, color=C[3], lw=1.6, marker="o", ms=3)
ax.hlines(M["ratio_idx_1981_1985"], 1981, 1985, color="#0b0b0b", lw=2.4)
ax.hlines(M["ratio_idx_1987_1991"], 1987, 1991, color="#0b0b0b", lw=2.4)
ax.annotate(f"1981〜1985年 {M['ratio_idx_1981_1985']:.0f}", (1983, M["ratio_idx_1981_1985"]), xytext=(-110, 14), textcoords="offset points", fontsize=8.5, color=INK2)
ax.annotate(f"1987〜1991年 {M['ratio_idx_1987_1991']:.0f}", (1989, M["ratio_idx_1987_1991"]), xytext=(10, -26), textcoords="offset points", fontsize=8.5, color=INK2)
ax.axvline(1985.5, color=C[1], lw=1.2, ls="--")
ax.set_ylim(80, 125)
ax.set_xlabel("年"); ax.set_ylabel("日照時間÷全天日射量（1991〜2020年平均＝100）")
ax.set_title(f"同じ地点の日照時間と日射量の比は、1986年に段差がある（地点の中央値 {M['ratio_shift_median']:.1f}%）", loc="left", fontsize=10)
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig2_ratio_step.png", "両方を観測している地点の、比の指数の中央値。縦軸は80から。日射量は日射計で測るので、日照計の切り替えの影響を受けない")

# fig3 そろえた日照時間と全天日射量
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(Y.index, Y.sun_adj_idx, color=C[0], lw=1.6, label="日照時間（1985年以前を段差の分だけ下げた）")
ax.plot(Y.index, Y.rad_idx, color=C[2], lw=1.6, label="全天日射量")
ax.plot(Y.index, Y.sun_adj_idx.rolling(11, center=True, min_periods=6).mean(), color=C[0], lw=3, alpha=0.5)
ax.plot(Y.index, Y.rad_idx.rolling(11, center=True, min_periods=6).mean(), color=C[2], lw=3, alpha=0.5)
ax.set_ylim(60, 125)
ax.set_xlabel("年"); ax.set_ylabel("1991〜2020年平均＝100")
ax.set_title("段差をそろえると、日照時間ははっきり増えたのが2010年代から", loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig3_adjusted.png", f"日照時間の1985年以前の値に {A['factor']:.3f} を掛けた（比の段差の地点中央値）。太い線は11年移動平均。全天日射量は{MM['n_rad']}地点。縦軸は60から")

# fig4 地点ごとの比の変化
R = pd.read_csv(RES / "ratio_shift.csv")
fig, ax = plt.subplots(figsize=(8, 4.4))
bins = np.arange(-20, 2.5, 1)
ax.hist(R.chg, bins=bins, color=C[3], edgecolor="white", linewidth=1.5)
ax.axvline(0, color="#0b0b0b", lw=0.8)
ax.axvline(R.chg.median(), color=INK2, lw=1.2, ls="--")
ax.text(R.chg.median() + 0.2, ax.get_ylim()[1] * 0.92, f"中央値 {R.chg.median():.1f}%", fontsize=8.5, color=INK2)
ax.set_xlabel("日照時間÷全天日射量の変化（%、1981〜1985年平均 → 1987〜1991年平均）")
ax.set_ylabel("地点の数")
ax.set_title(f"{len(R)}地点すべてで比が下がった", loc="left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig4_station_shift.png", "両方の期間に日照時間と全天日射量の値がある地点")
