"""04 図（オフライン）：results の CSV から図を4枚作る。"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
from matplotlib import font_manager

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f:
        font_manager.fontManager.addfont(f)
ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "svg.hashsalt": "f3"})
SRC = "出典：法務省「出入国管理統計」（e-Stat）をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))

def save(fig, name, src=SRC):
    fig.text(0.01, 0.01, src, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

# 図1 月の戻り率と、ドル・円・外国パック旅行費
mr = pd.read_csv(RES / "monthly_ratio.csv")
x = np.arange(len(mr))
fig, axs = plt.subplots(2, 1, figsize=(8, 6.2), sharex=True, gridspec_kw={"height_ratios": [1.4, 1]})
ax = axs[0]
ax.plot(x, mr.ratio_to_2019 * 100, color=C1, lw=2, marker="o", ms=4)
ax.axhline(100, color=INK2, lw=1, ls="--"); ax.text(0, 101.5, "2019年の同じ月と同じ水準", fontsize=8.5, color=INK2)
ax.set_ylim(0, 110); ax.set_ylabel("出国者数（2019年同月＝100）")
ax.set_title(f"出国者数は2025年でも2019年の{M['R_total_2025']*100:.0f}%。円安の中でも、月ごとに少しずつ戻ってきた", loc="left", fontsize=11)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.text(len(mr) - 1, mr.ratio_to_2019.iloc[-1] * 100 + 6, f"{mr.ratio_to_2019.iloc[-1]*100:.0f}", ha="center", fontsize=9, color=INK)
ax.text(0, mr.ratio_to_2019.iloc[0] * 100 - 9, f"{mr.ratio_to_2019.iloc[0]*100:.0f}", ha="center", fontsize=9, color=INK)
ax = axs[1]
ax.plot(x, mr.usdjpy_vs_2019 * 100, color=C2, lw=2, label="ドル・円（円安ほど上）")
cp = (mr.cpi_fp_vs_2019 * 100).where(mr.ym >= 202401)  # 2021〜2023年は価格調査が止まり2020年の値で代用されていたので描かない
ax.plot(x, cp, color=C3, lw=2, label="外国パック旅行費の物価指数（2024年1月から）")
ax.axhline(100, color=INK2, lw=1, ls="--")
ax.set_ylabel("2019年同月＝100"); ax.set_ylim(60, 220); ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(frameon=False, fontsize=8.5, loc="upper left")
ax.set_xticks([i for i in x if mr.month[i] in (1, 7)])
ax.set_xticklabels([f"{mr.year[i]}年{mr.month[i]}月" for i in x if mr.month[i] in (1, 7)], fontsize=8.5)
fig.subplots_adjust(left=0.1, right=0.97, top=0.93, bottom=0.13, hspace=0.12)
save(fig, "fig1_monthly_recovery.png", "出典：法務省「出入国管理統計」、日本銀行「時系列統計データ」、総務省「消費者物価指数」をもとに作成者が加工して作成。\n外国パック旅行費は2021〜2023年に価格の調査が止まっていたため、2024年1月からだけを描いた")

# 図2 年齢・男女別の戻り率
t = pd.read_csv(RES / "requestion_sex_age.csv")
order = ["0〜19歳", "20代", "30代", "40代", "50代", "60歳以上"]
fig, ax = plt.subplots(figsize=(8, 4.8))
y = np.arange(len(order)); h = 0.38
for k, (sex, c) in enumerate([("男", C1), ("女", C2)]):
    v = t[t.sex == sex].set_index("ageg").count_ratio_2025.reindex(order) * 100
    ax.barh(y + (k - 0.5) * h * 1.05, v, height=h, color=c, label=("男性" if sex == "男" else "女性"))
    for yi, vi in zip(y, v):
        ax.text(vi + 1, yi + (k - 0.5) * h * 1.05, f"{vi:.0f}", va="center", fontsize=8.5, color=INK)
ax.axvline(M["R_total_2025"] * 100, color=INK2, lw=1, ls="--")
ax.text(M["R_total_2025"] * 100 + 0.8, 5.95, f"全体 {M['R_total_2025']*100:.0f}", fontsize=8.5, color=INK2)
ax.set_yticks(y); ax.set_yticklabels(order); ax.set_ylim(6.15, -0.6)
ax.set_xlim(0, 100); ax.set_xlabel("2025年の出国者数（2019年＝100）")
ax.set_title("いちばん戻っていないのは30〜50代の男性。20代は男女とも85〜86まで戻った", loc="left", fontsize=11)
ax.legend(frameon=False, loc="lower right"); ax.grid(axis="x", color=GRID, lw=0.8)
fig.subplots_adjust(left=0.12, right=0.97, top=0.9, bottom=0.17)
save(fig, "fig2_age_sex.png")

# 図3 地域（北から南）
reg = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
pr = pd.read_csv(RES / "ratio_by_pref.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
for i, rg in enumerate(reg):
    g = pr[pr.region == rg]
    jit = np.linspace(-0.25, 0.25, len(g)) if len(g) > 1 else [0]
    ax.scatter(np.array(jit) + i, g.ratio * 100, s=[45 if m else 22 for m in g.metro], color=[C2 if m else C1 for m in g.metro],
               edgecolor="white", linewidth=0.8, zorder=3)
    ax.plot([i - 0.32, i + 0.32], [M["R_region"][rg] * 100] * 2, color=INK, lw=2, zorder=4)
ax.scatter([], [], s=45, color=C2, label="大都市圏の都府県（埼玉・千葉・東京・神奈川・愛知・京都・大阪・兵庫）")
ax.scatter([], [], s=22, color=C1, label="それ以外の道県")
ax.plot([], [], color=INK, lw=2, label="地方ごとの合計")
ax.set_xticks(range(len(reg))); ax.set_xticklabels(reg)
ax.set_ylim(50, 90); ax.set_ylabel("2025年の出国者数（2019年＝100）"); ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_title(f"大都市圏は{M['R_metro']*100:.0f}、それ以外は{M['R_nonmetro']*100:.0f}。住む地域でも戻り方が違う（地方は北から南へ）", loc="left", fontsize=11)
ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=1)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.12)
save(fig, "fig3_region.png", SRC + "。住所地は旅券を取った都道府県")

# 図4 空港
apt = pd.read_csv(RES / "ratio_by_airport.csv")
apt = apt[apt.port != "その他"]
apt = apt[apt.n2019 >= 30000]  # 2019年に3万人以上が出国した空港
fig, ax = plt.subplots(figsize=(8, 4.8))
y = np.arange(len(apt))
big = apt.port.isin(["成田", "羽田", "関西", "中部"])
ax.barh(y, apt.ratio * 100, color=np.where(big, C2, C1), height=0.65)
for yi, (v, n19) in enumerate(zip(apt.ratio * 100, apt.n2019)):
    ax.text(min(v, 140) + 1.5, yi, f"{v:.0f}（2019年 {n19/1e4:.1f}万人）" if n19 < 1e6 else f"{v:.0f}（2019年 {n19/1e4:.0f}万人）", va="center", fontsize=8, color=INK)
ax.set_yticks(y); ax.set_yticklabels(apt.port); ax.invert_yaxis()
ax.axvline(100, color=INK2, lw=1, ls="--")
ax.set_xlim(0, 175); ax.set_xlabel("2025年の出国者数（2019年＝100）。空港は北から南の順")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=C2, label="4大空港（成田・羽田・関西・中部）"), Patch(color=C1, label="それ以外の空港")], frameon=False, fontsize=8.5, loc="lower right")
ax.set_title(f"羽田は{M['R_airport']['羽田']*100:.0f}まで戻り、成田は{M['R_airport']['成田']*100:.0f}、中部は{M['R_airport']['中部']*100:.0f}。地方空港がまとめて遅いわけではない", loc="left", fontsize=11)
ax.grid(axis="x", color=GRID, lw=0.8)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.16)
save(fig, "fig4_airport.png", SRC + "。2019年に3万人以上が出国した空港（長崎・熊本は2019年が小さいため除いた）")
print("figures done")
