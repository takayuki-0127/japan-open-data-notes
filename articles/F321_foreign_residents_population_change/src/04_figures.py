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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2 = "#52514e"
SRC = "出典：総務省「人口推計」第5表・参考表（都道府県別、日本人・外国人別）をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))

def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7.2, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

# fig1 全国：日本人と外国人の前年差
N = pd.read_csv(RES / "national_stock.csv").set_index("year").loc[2011:]
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.bar(N.index - 0.2, N["日本人の前年差"], width=0.4, color=C[0], label="日本人の増減")
ax.bar(N.index + 0.2, N["外国人の前年差"], width=0.4, color=C[1], label="外国人の増減")
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xticks(N.index, [str(y) if y % 2 == 0 else "" for y in N.index])
ax.set_ylabel("前年10月からの増減（千人）"); ax.set_xlabel("年（各年10月1日）")
ax.set_title(f"2020年10月〜24年9月、外国人の増加は日本人の減少の{M['全国_要素']['埋め合わせ率_2021_2024_%']:.0f}%にあたる", loc="left")
ax.legend(frameon=False, loc="lower left")
fig.subplots_adjust(bottom=0.19, left=0.1, right=0.98, top=0.9)
save(fig, "fig1_national_change.png", "外国人＝総人口−日本人人口（千人単位の差）。2015年・2020年の棒は国勢調査に合わせた水準の切り替えを含む")

# fig2 地方別の埋め合わせ率（北から南）
RG = pd.read_csv(RES / "by_region_2021_2024.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(RG))
ax.bar(x, RG["埋め合わせ率_%"], color=C[1], width=0.6)
for i, v in enumerate(RG["埋め合わせ率_%"]):
    ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=9, color=INK2)
ax.axhline(M["H2"]["三大都市圏_埋め合わせ率_%"], color=C[0], lw=1.2, ls="--")
ax.axhline(M["H2"]["地方圏_埋め合わせ率_%"], color=C[2], lw=1.2, ls="--")
ax.text(6.45, M["H2"]["三大都市圏_埋め合わせ率_%"] + 1.5, f"三大都市圏 {M['H2']['三大都市圏_埋め合わせ率_%']:.1f}%", ha="right", fontsize=8.5, color=INK2)
ax.text(4.5, M["H2"]["地方圏_埋め合わせ率_%"] + 1.5, f"地方圏 {M['H2']['地方圏_埋め合わせ率_%']:.1f}%", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(x, RG["地方"])
ax.set_ylabel("外国人の増加 ÷ 日本人の減少（%）")
ax.set_title("外国人の増加が日本人の減少を埋める割合は、関東で高く地方圏で低い", loc="left")
ax.set_ylim(0, 95)
fig.subplots_adjust(bottom=0.19, left=0.1, right=0.98, top=0.9)
save(fig, "fig2_offset_by_region.png", "2020年10月〜2024年9月の出生・死亡・県間移動・出入国の合計。地方は北から南の順。三大都市圏＝東京圏・名古屋圏・大阪圏の11都府県")

# fig3 県別：外国人の国外との増減と県間の増減（北から南）
CP = pd.read_csv(RES / "components_2021_2024.csv")
CP = CP[CP.pref > 0].sort_values("pref")
fig, ax = plt.subplots(figsize=(8, 9.2))
y = np.arange(len(CP))[::-1]
ax.barh(y + 0.2, CP["国外_外国人"] / 1000, height=0.4, color=C[1], label="国外との増減（入国−出国）")
ax.barh(y - 0.2, CP["県間_外国人"] / 1000, height=0.4, color=C[0], label="ほかの県との増減（転入−転出）")
ax.set_yticks(y, CP["県"]); ax.tick_params(axis="y", labelsize=8.5)
ax.set_xscale("symlog", linthresh=5)
ax.set_xticks([-10, -5, 0, 5, 10, 50, 100, 200], ["−10", "−5", "0", "5", "10", "50", "100", "200"])
ax.axvline(0, color="#0b0b0b", lw=0.8)
ax.set_xlabel("外国人の増減（千人、2020年10月〜2024年9月の合計。5千人より外側は対数目盛）")
ax.set_title("外国人は国外から全県で増え、ほかの県へ出ていく分はその一部（北から南の順）", loc="left", fontsize=10.5)
ax.legend(frameon=False, loc="lower right", fontsize=8.5)
ax.grid(axis="y", visible=False)
fig.subplots_adjust(bottom=0.1, left=0.1, right=0.98, top=0.95)
save(fig, "fig3_pref_foreign_components.png")

# fig4 問い直し：地方圏の日本人の減り方と外国人の入り方
q = M["問い直し"]
labs = ["日本人の\n自然増減", "日本人の\nほかの県との増減", "外国人の\n国外との増減", "外国人の\nほかの県との増減"]
keys = ["地方圏_日本人_自然", "地方圏_日本人_県間", "地方圏_外国人_国外", "地方圏_外国人_県間"]
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(4)
for k, (per, lab, c) in enumerate([("2016_2019", "2015年10月〜2019年9月", C[3]), ("2021_2024", "2020年10月〜2024年9月", C[1])]):
    v = np.array([q[per][kk] for kk in keys]) / 1000
    ax.bar(x + (k - 0.5) * 0.38, v, width=0.38, color=c, label=lab)
    for i, vv in enumerate(v):
        ax.text(x[i] + (k - 0.5) * 0.38, vv + (25 if vv >= 0 else -25), f"{vv:,.0f}", ha="center",
                va="bottom" if vv >= 0 else "top", fontsize=8, color=INK2)
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xticks(x, labs, fontsize=9)
ax.set_ylabel("4年間の合計（千人）")
ax.set_ylim(-2100, 500)
ax.set_title("地方圏：外国人の流入は日本人の県外流出に近い規模、自然減にはまだ遠い", loc="left")
ax.legend(frameon=False, loc="lower right")
fig.subplots_adjust(bottom=0.2, left=0.1, right=0.98, top=0.9)
save(fig, "fig4_chiho_components.png", "地方圏＝三大都市圏（11都府県）を除く36道県。2015年・2020年の国勢調査の年をはさむため、期間は4年ずつ")
print("figures ok")
