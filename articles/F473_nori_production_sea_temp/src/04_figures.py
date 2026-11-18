"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; D = ROOT / "data"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "IPAexGothic"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand; break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#8a5cd1", "#c2410c"]
INK2, GRID = "#52514e", "#e4e3df"
META = {"Software": None}
S_P = "出典：農林水産省「漁業・養殖業生産統計」をもとに作成者が加工して作成"
S_T = "出典：農林水産省「漁業・養殖業生産統計」、気象庁「海面水温の長期変化傾向（日本近海）」「過去の気象データ検索」をもとに作成者が加工して作成"
M = json.load(open(R / "main.json", encoding="utf-8"))
Q = json.load(open(R / "requestion.json", encoding="utf-8"))


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note, src):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + src, fontsize=7.6, color=INK2)


def resid(d, y, x):
    """県の平均と共通の年の直線を除いた残り（y と x の両方）"""
    d = d.copy()
    for c in (y, x):
        d[c + "_r"] = d[c] - d.groupby("pref")[c].transform("mean")
    t = d.season - d.season.mean()
    for c in (y, x):
        b = np.polyfit(t, d[c + "_r"], 1)
        d[c + "_r"] = d[c + "_r"] - np.polyval(b, t)
    return d


# 図1：全国（暦年、1956〜2024年）
L = pd.read_csv(D / "nori_national_long.csv")
lg = M["long"]
fig, ax = plt.subplots(figsize=(8.8, 4.9))
ax.plot(L.year, L.nori_t / 1e4, color=C[0], lw=2)
ax.scatter([lg["peak_year"], 2024], [lg["peak_t"] / 1e4, lg["y2024"] / 1e4], color=C[1], zorder=3)
ax.annotate(f"{lg['peak_year']}年 {lg['peak_t']/1e4:.1f}万t", (lg["peak_year"], lg["peak_t"] / 1e4), xytext=(-10, 8), textcoords="offset points", ha="right", fontsize=9, color=INK2)
ax.annotate(f"2024年 {lg['y2024']/1e4:.1f}万t\n（{lg['last_year_at_or_below_2024_level']}年以来の少なさ）", (2024, lg["y2024"] / 1e4), xytext=(-8, -34), textcoords="offset points", ha="right", fontsize=9, color=INK2)
ax.set_ylabel("のり類の収獲量（生換算、万t）"); ax.set_ylim(0, 55); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.set_title(f"のりの生産は{lg['peak_year']}年の山から6割減（全国、暦年）", fontsize=11.5, loc="left")
fig.subplots_adjust(bottom=0.15, top=0.9, left=0.08, right=0.97)
foot(fig, "注：生換算重量（干す前の重さに換算した量）。暦年（1〜12月）", S_P)
save(fig, "fig1_national_long.png")

# 図2：産地のまとまり（2004〜08年の期の平均＝100）
G = pd.read_csv(R / "groups_season.csv").set_index("season")
H = pd.read_csv(R / "h2_groups.csv").set_index("group")
fig, ax = plt.subplots(figsize=(8.8, 5.6))
for k, g in enumerate(["東北", "東京湾", "伊勢・三河湾", "瀬戸内海", "有明海"]):
    v = 100 * G[g] / G.loc[2004:2008, g].mean()
    ax.plot(v.index, v.values, color=C[k], lw=2.2 if g in ("瀬戸内海", "有明海") else 1.4, label=f"{g}（{H.loc[g,'change_pct']:+.0f}%）")
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.set_xticks(range(2004, 2024, 2)); ax.set_ylim(0, 140); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.set_ylabel("2004〜08年の期の平均＝100"); ax.set_xlabel("期（その年の7月〜翌年6月）", fontsize=9.5)
ax.legend(frameon=False, fontsize=9, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.13), title="産地（北から南。括弧は2019〜23年の期の平均の変化）", title_fontsize=8.5, handlelength=1.5, columnspacing=1.0)
ax.set_title("有明海と瀬戸内海は2〜3割減、東京湾・伊勢三河湾・東北は5〜8割減", fontsize=11.5, loc="left")
fig.subplots_adjust(bottom=0.3, top=0.9, left=0.08, right=0.97)
foot(fig, "注：東北＝宮城、東京湾＝千葉、伊勢・三河湾＝愛知・三重、瀬戸内海＝兵庫・岡山・香川、有明海＝福岡・佐賀・熊本\n（県の値なので湾の外の分を含む）。秘匿の値は板のりの枚数などで埋めた", S_P)
save(fig, "fig2_by_area.png")

# 図3：秋の水温・気温と生産（県の平均と年の直線を除いた残り）
P = pd.read_csv(R / "panel_major.csv")
fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.9), sharey=True)
for ax, x, lab, key in [(axs[0], "sst", "秋（10〜12月）の海面水温の平年差（℃）", "主（10県、秋の海面水温、共通の年の直線）"),
                        (axs[1], "air", "10〜11月の気温の平年差（℃、近くの気象台）", "10〜11月の気温（近くの気象台）")]:
    d = resid(P, "logt", x)
    ax.scatter(d[x + "_r"], 100 * d["logt_r"], s=14, color=C[0], alpha=0.5, edgecolor="none")
    rb = next(r for r in M["robustness"] if r["name"] == key)
    xs = np.linspace(d[x + "_r"].min(), d[x + "_r"].max(), 10)
    ax.plot(xs, 100 * rb["b"] * xs, color=C[1], lw=2)
    ax.text(0.03, 0.05, f"1℃あたり {rb['pct']:+.1f}%\n95%区間 {100*(np.exp(rb['lo'])-1):+.1f}〜{100*(np.exp(rb['hi'])-1):+.1f}%", transform=ax.transAxes, fontsize=9, color=INK2)
    ax.axhline(0, color=GRID); ax.axvline(0, color=GRID)
    ax.set_xlabel(lab, fontsize=9.5)
axs[0].set_ylabel("生産のずれ（県の平均と年の直線からの差、%）")
fig.suptitle("秋の沖合の水温とは関係がはっきりせず、気温の高い秋はやや少ない（10県×20期）", fontsize=11.5, x=0.01, ha="left")
fig.subplots_adjust(bottom=0.2, top=0.88, left=0.09, right=0.98, wspace=0.08)
foot(fig, "注：線は県の固定効果と共通の年の直線を入れた回帰の傾き。区間は期でクラスター。海面水温は沖合の海域（東シナ海北部、四国・東海沖、関東の南、三陸沖）の値", S_T)
save(fig, "fig3_temp_vs_production.png")

# 図4：年内（7〜12月）にとれた割合と、10〜11月の気温
d = pd.read_csv(R / "requestion_h2share.csv")
d = d.rename(columns={"h2share": "y"})
dd = resid(d.assign(logt=d.y), "logt", "air")
fig, ax = plt.subplots(figsize=(8.8, 4.9))
ax.scatter(dd["air_r"], dd["logt_r"], s=16, color=C[2], alpha=0.6, edgecolor="none")
xs = np.linspace(dd.air_r.min(), dd.air_r.max(), 10)
ax.plot(xs, Q["air"]["b"] * xs, color=C[1], lw=2)
ax.text(0.03, 0.06, f"1℃あたり {Q['air']['b']:+.1f}ポイント（95%区間 {Q['air']['lo']:+.1f}〜{Q['air']['hi']:+.1f}）\n全体の平均は{Q['mean_share']:.0f}%", transform=ax.transAxes, fontsize=9, color=INK2)
ax.axhline(0, color=GRID); ax.axvline(0, color=GRID)
ax.set_xlabel("10〜11月の気温の平年差（℃、近くの気象台。県の平均と年の直線を除いた残り）")
ax.set_ylabel("年内（7〜12月）にとれた割合のずれ（ポイント）")
ax.set_title("秋が暖かい期は、年内にとれる板のりの割合が小さい（10県）", fontsize=11.5, loc="left")
fig.subplots_adjust(bottom=0.2, top=0.9, left=0.09, right=0.97)
foot(fig, "注：割合＝板のりの枚数の7〜12月÷養殖年（7月〜翌年6月）。秘匿で枚数のない県×期は除いた", S_T)
save(fig, "fig4_harvest_timing.png")
print("ok")
