"""04_figures.py : 図4枚（PNG）。日付などのメタデータは入れない（オフライン）。"""
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
F = ROOT / "figures"
F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a63d2"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省「家計調査（家計収支編）」二人以上の世帯のうち勤労者世帯 第3-2表・第3-11表、「消費者物価指数」（e-Stat）をもとに作成者が加工して作成"
META = {"Software": None}
POCKET = "こづかい(使途不明)"


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
rq = json.load(open(R / "requestion.json", encoding="utf-8"))
ser = pd.read_csv(R / "series.csv")
bg = pd.read_csv(R / "by_group.csv")
yrs = ser["year"]

# 図1 こづかいと交際費（勤労者世帯）
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.grid(axis="y", color=GRID, lw=0.8)
ax.plot(yrs, ser["pocket_real"] / 1e4, color=C[0], lw=2.2, label="こづかい（使途不明）実質")
ax.plot(yrs, ser[POCKET] / 1e4, color=C[0], lw=1.3, ls="--", label="こづかい（使途不明）名目")
ax.plot(yrs, ser["kosai_real"] / 1e4, color=C[1], lw=2.2, label="交際費 実質")
ax.plot(yrs, ser["交際費"] / 1e4, color=C[1], lw=1.3, ls="--", label="交際費 名目")
ax.text(2025.3, ser["pocket_real"].iloc[-1] / 1e4, f"{ser[POCKET].iloc[-1]:,.0f}円", fontsize=9, color=C[0], va="center")
ax.text(2000.0, ser["pocket_real"].iloc[0] / 1e4 + 0.15, f"2000年 {ser[POCKET].iloc[0]:,.0f}円（名目）", fontsize=9, color=C[0])
ax.axvline(2017.5, color=INK2, lw=0.8, ls=":")
ax.text(2017.6, 0.15, "2018年1月\n家計簿の改正", fontsize=8.6, color=INK2, va="bottom")
ax.set_xlim(1999.5, 2027.3)
ax.set_ylim(0, 4.0)
ax.set_ylabel("1世帯・1か月あたり（万円）")
ax.set_xlabel("年")
ax.legend(loc="upper right", frameon=False, fontsize=9.2, bbox_to_anchor=(0.93, 1.0))
h1 = main["H1"]
ax.set_title(f"こづかい（使途不明）は実質で{abs(h1['change_pct']):.0f}%減った。交際費の減り方（{abs(main['H2']['kosai_change_pct']):.0f}%）より大きい",
             loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：実質は2025年の物価（持家の帰属家賃を除く総合）に直した値。減り方は2000〜02年平均と2023〜25年平均の比較。\n" + SRC,
         fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig1_pocket_trend.png")

# 図2 年齢階級別（実質）
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.grid(axis="y", color=GRID, lw=0.8)
lab = {"age_u29": "〜29歳", "age_30s": "30〜39歳", "age_40s": "40〜49歳", "age_50s": "50〜59歳", "age_60s": "60〜69歳"}
for i, (g, l) in enumerate(lab.items()):
    s = bg[bg.group == g]
    ax.plot(s["year"], s["pocket_real"] / 1e4, color=C[i], lw=2.0 if g != "age_u29" else 1.3,
            ls="-" if g != "age_u29" else "--", label=f"{l}（{main['H3']['by_age'][g]['change_pct']:.0f}%）")
ax.set_xlim(1999.5, 2025.8)
ax.set_ylim(0, 5.6)
ax.set_ylabel("1世帯・1か月あたり（万円、2025年の物価で実質）")
ax.set_xlabel("年")
ax.legend(loc="upper right", frameon=False, fontsize=9.2, title="世帯主の年齢（2000〜02→2023〜25の変化）", title_fontsize=8.8)
ax.set_title("どの年齢の世帯でも7〜9割減った", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：〜29歳は標本が少ない（2023〜25年は年に約90世帯）ので点線。70歳以上は標本が少ないので省いた。\n" + SRC,
         fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig2_by_age.png")

# 図3 共働き・夫のみ有業（実質）と、世帯の構成の変化
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.grid(axis="y", color=GRID, lw=0.8)
dv = main["dual_vs_husband_only"]
for i, (g, l) in enumerate([("dual", "夫婦共働き世帯"), ("husband_only", "夫のみ有業の世帯")]):
    s = bg[bg.group == g]
    ax.plot(s["year"], s["pocket_real"] / 1e4, color=C[i], lw=2.2, label=f"{l}（{dv[g]['change_pct']:.0f}%）")
ws = dv["shift_share"]
ax.text(2009.0, 3.6, f"共働きの割合（2つの型の中）：{ws['weights_p0']['dual']*100:.0f}% → {ws['weights_p1']['dual']*100:.0f}%\n"
        f"構成の変化の効果：{ws['composition']:+,.0f}円（全体の変化 {ws['change']:+,.0f}円）", fontsize=9.2, color=INK)
ax.set_xlim(1999.5, 2025.8)
ax.set_ylim(0, 4.6)
ax.set_ylabel("1世帯・1か月あたり（万円、2025年の物価で実質）")
ax.set_xlabel("年")
ax.legend(loc="upper right", frameon=False, fontsize=9.5)
ax.set_title("共働きでも夫のみ有業でも同じように減り、2つの差もほぼ消えた", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：割合と効果は2000〜02年平均と2023〜25年平均の比較（世帯数分布で重みづけ）。\n" + SRC, fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig3_dual_vs_husband_only.png")

# 図4 民間調査との比較（2010年＝100、名目）
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.grid(axis="y", color=GRID, lw=0.8)
for i, (g, l) in enumerate([("workers_all", "家計調査：勤労者世帯のこづかい（使途不明）"), ("husband_only", "家計調査：夫のみ有業の世帯")]):
    s = bg[(bg.group == g) & (bg.year >= 2010)]
    base = s.loc[s.year == 2010, POCKET].iloc[0]
    ax.plot(s["year"], s[POCKET] / base * 100, color=[C[0], C[2]][i], lw=2.2 if i == 0 else 1.4, ls="-" if i == 0 else "--", label=l)
ax.plot([2010, 2022], [100, rq["sbi_2022"] / rq["sbi_2010"] * 100], color=C[1], lw=1.6, ls=":", marker="o", ms=6,
        label="民間調査：男性会社員のお小遣い（本人に聞いた額）")
ax.text(2022.2, rq["sbi_2022"] / rq["sbi_2010"] * 100 + 2, f"{rq['sbi_change_2010_2022_pct']:+.1f}%", fontsize=9.5, color=C[1])
v22 = rq["workers_all_2022"] / rq["workers_all_2010"] * 100
ax.annotate(f"2022年 {rq['workers_all_change_2010_2022_pct']:+.1f}%", xy=(2022, v22), xytext=(2018.3, 30), fontsize=9.5,
            color=C[0], arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xlim(2009.5, 2025.8)
ax.set_ylim(0, 115)
ax.set_ylabel("2010年＝100（名目）")
ax.set_xlabel("年")
ax.legend(loc="lower left", frameon=False, fontsize=9.2)
ax.set_title("同じ2010→2022年で、本人に聞いたお小遣いは−8%、家計簿の「こづかい」は−55%", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：民間調査はSBI新生銀行「会社員のお小遣い調査」（インターネット調査）の2010・2022年の2点。家計調査とは定義も対象も違う。\n" + SRC,
         fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig4_survey_compare.png")
print("figures ok")
