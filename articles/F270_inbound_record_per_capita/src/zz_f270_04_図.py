"""F270 04 図：figures/ に6枚。"""
import os, json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP"], "axes.unicode_minus": False, "figure.dpi": 110,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25})
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "..", "results"); FG = os.path.join(HERE, "..", "figures"); os.makedirs(FG, exist_ok=True)
S = pd.read_csv(os.path.join(R, "A_series.csv"), index_col=0)
M = json.load(open(os.path.join(R, "main.json")))
SRC = "出典：観光庁「訪日外国人消費動向調査」「インバウンド消費動向調査」、JNTO、総務省「消費者物価指数」、FRED をもとに作成"
YRS = list(S.index); MAIN = [y for y in YRS if y != 2022]
C1, C2, C3, C4 = "#1f5fa8", "#d1495b", "#2a9d8f", "#888888"
def save(fig, name):
    fig.text(0.01, 0.005, SRC, fontsize=7, color="#666")
    fig.savefig(os.path.join(FG, name), dpi=150, bbox_inches="tight"); plt.close(fig)

# 図1：訪日客数と1人あたり支出（名目・実質の円）
fig, ax = plt.subplots(figsize=(9, 4.8)); ax2 = ax.twinx()
ax.bar(MAIN, S.loc[MAIN, "arrivals"] / 1e4, color="#cfd8e3", width=0.7, label="訪日外客数（左軸、万人）")
ax2.plot(MAIN, S.loc[MAIN, "pc_nom"] / 1e4, "-o", color=C1, label="1人あたり支出・名目（右軸、万円）")
ax2.plot(MAIN, S.loc[MAIN, "pc_real"] / 1e4, "-s", color=C2, label="1人あたり支出・実質（2020年の物価、万円）")
ax2.scatter([2022], [S.loc[2022, "pc_nom"] / 1e4], color=C1, facecolor="white", zorder=5, label="2022年（入国制限中、参考）")
for y in [2024, 2025]:
    ax2.annotate(f"{S.loc[y,'pc_nom']/1e4:.1f}", (y, S.loc[y, "pc_nom"] / 1e4), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8, color=C1)
    ax2.annotate(f"{S.loc[y,'pc_real']/1e4:.1f}", (y, S.loc[y, "pc_real"] / 1e4), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=8, color=C2)
ax.axvspan(2019.5, 2022.5, color="#f2f2f2", zorder=0); ax.text(2021, 4100, "2020〜2022年\n（入国制限）", ha="center", fontsize=8, color="#777")
ax.set_ylabel("訪日外客数（万人）"); ax2.set_ylabel("1人あたり支出（万円）"); ax2.set_ylim(10, 25); ax2.grid(False)
ax.set_xticks(YRS); ax.tick_params(axis="x", labelsize=8)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8, frameon=False)
ax.set_title("訪日客は2025年が最多。1人あたりの支出は名目では最多、物価で割ると2024年を下回った", fontsize=11)
save(fig, "f270_1_arrivals_per_capita.png")

# 図2：4つのものさし（2019年=100）
fig, ax = plt.subplots(figsize=(9, 4.8))
for col, lab, c, m in [("pc_nom", "名目の円", C1, "o"), ("pc_real", "実質の円（日本の消費者物価で割る）", C2, "s"),
                       ("pc_usd_nom", "名目のドル（年平均の為替）", C3, "^"), ("pc_usd_real", "実質のドル（米国の物価でも割る）", C4, "D")]:
    v = S.loc[MAIN, col] / S.loc[2019, col] * 100
    ax.plot(MAIN, v, "-" + m, color=c, label=lab)
    ax.annotate(f"{v.loc[2025]:.0f}", (2025, v.loc[2025]), textcoords="offset points", xytext=(8, -3), fontsize=8, color=c)
ax.axhline(100, color="#999", lw=0.8)
ax.set_xticks(MAIN); ax.tick_params(axis="x", labelsize=8); ax.set_ylabel("2019年＝100")
ax.legend(fontsize=8, frameon=False, loc="upper left")
ax.set_title("同じ1人あたりの支出でも、ものさしで向きが変わる（2019年＝100）", fontsize=11)
save(fig, "f270_2_four_yardsticks.png")

# 図3：「過去最多」の年（訪日客数とものさしごと）
rows = [("訪日外客数", M["arrival_record_years"]), ("1人あたり・名目の円", M["per_capita_record_years"]["pc_nom"]),
        ("1人あたり・実質の円", M["per_capita_record_years"]["pc_real"]), ("1人あたり・実質の円（旅行の物価）", M["per_capita_record_years"]["pc_real_travel"]),
        ("1人あたり・実質のドル", M["per_capita_record_years"]["pc_usd_real"]), ("1泊あたり・実質の円", M["per_capita_record_years"]["pc_real_per_night"])]
fig, ax = plt.subplots(figsize=(9, 3.6))
for i, (lab, ys) in enumerate(rows):
    for y in MAIN[1:]:
        hit = y in ys
        ax.scatter(y, -i, s=150, marker="s", color=(C1 if i == 0 else C2) if hit else "#eeeeee", edgecolor="#bbb")
ax.set_yticks([-i for i in range(len(rows))]); ax.set_yticklabels([r[0] for r in rows], fontsize=9)
ax.set_xticks(MAIN[1:]); ax.tick_params(axis="x", labelsize=8); ax.grid(False)
ax.set_title("色つき＝それまでの年より大きかった年（1人あたりは2011年以降・2020〜2022年を除く、訪日客数は2003年以降で判定）", fontsize=9.5)
save(fig, "f270_3_record_years.png")

# 図4：国・地域別、2025年は2011〜2019年の最大と比べて何％か（実質の円 と 実質の現地通貨）
cs = pd.read_csv(os.path.join(R, "C_country_summary.csv")).sort_values("local_real_2025_vs_premax")
fig, ax = plt.subplots(figsize=(9, 5.2)); yy = np.arange(len(cs))
ax.barh(yy + 0.2, cs.jpy_real_2025_vs_premax * 100, height=0.38, color=C2, label="実質の円（日本の物価で割る）")
ax.barh(yy - 0.2, cs.local_real_2025_vs_premax * 100, height=0.38, color=C3, label="実質の現地通貨（その国の物価で割る）")
ax.set_yticks(yy); ax.set_yticklabels(cs.nat, fontsize=9); ax.axvline(0, color="#333", lw=0.8)
ax.set_xlabel("2025年の1人あたり支出が、2011〜2019年でいちばん大きかった年と比べて何％か")
ax.legend(fontsize=8, frameon=False, loc="lower right")
ax.set_title("円で見ると13か国中12か国が「過去最多」、訪日客の通貨で見ると2か国だけ", fontsize=11)
save(fig, "f270_4_by_country.png")

# 図5：構成の分解
dec = pd.read_csv(os.path.join(R, "B_decomposition.csv")); dec = dec[dec.weight == "avg"]
order = [(2011, 2019), (2015, 2019), (2019, 2024), (2019, 2025), (2015, 2025), (2024, 2025)]
fig, ax = plt.subplots(figsize=(9, 4.6)); x = np.arange(len(order))
w = [dec[(dec.y0 == a) & (dec.y1 == b)].within.iloc[0] / 1e4 for a, b in order]
m = [dec[(dec.y0 == a) & (dec.y1 == b)].mix.iloc[0] / 1e4 for a, b in order]
ax.bar(x - 0.2, w, width=0.38, color=C1, label="国・地域の中で1人あたりが変わった分")
ax.bar(x + 0.2, m, width=0.38, color="#f4a261", label="来る国・地域の構成が変わった分")
pub = M["robust"]["published_diff"]
for i, (a, b) in enumerate(order):
    ax.annotate(f"{w[i]+m[i]:+.2f}\n（公表値 {pub[f'{a}-{b}']/1e4:+.2f}）", (x[i], max(w[i], m[i], 0) + 0.15), ha="center", fontsize=7.5)
ax.axhline(0, color="#333", lw=0.8); ax.set_xticks(x); ax.set_xticklabels([f"{a}→{b}" for a, b in order], fontsize=9)
ax.set_ylabel("1人あたり支出の変化（万円、名目、組み立てた値）"); ax.set_ylim(-2.8, 9.0); ax.legend(fontsize=8, frameon=False)
ax.set_title("国籍別の値から組み立てた1人あたりの分解。2019→2025年はほぼ国・地域の中の増加、構成の変化はほぼゼロ", fontsize=10)
save(fig, "f270_5_mix_decomposition.png")

# 図6：問い直し（2024→2025年、泊数と1泊あたり）
rn = pd.read_csv(os.path.join(R, "D_reask_nights_by_nat_2024_2025.csv"))
fig, ax = plt.subplots(figsize=(8.6, 5.2))
o = rn[rn.nat != "全体"]
ax.scatter(o.nights_chg * 100, o.per_night_chg * 100, s=o.n_resp_2025 / 12, color=C3, alpha=0.6)
for _, r in o.iterrows():
    ax.annotate(r.nat, (r.nights_chg * 100, r.per_night_chg * 100), fontsize=7.5, xytext=(3, 3), textcoords="offset points")
t = rn[rn.nat == "全体"].iloc[0]
ax.scatter(t.nights_chg * 100, t.per_night_chg * 100, s=160, color=C2, marker="*", zorder=5)
ax.annotate("全国籍", (t.nights_chg * 100, t.per_night_chg * 100), color=C2, fontsize=9, xytext=(-40, -16), textcoords="offset points")
lim = 32; xx = np.linspace(-lim, lim, 10)
ax.plot(xx, -xx, color="#bbb", lw=0.8, ls="--"); ax.text(lim * 0.3, lim * 0.62, "斜めの点線より右上：1人あたりが増えた\n左下：減った", fontsize=8, color="#777")
ax.axhline(0, color="#333", lw=0.6); ax.axvline(0, color="#333", lw=0.6)
ax.set_xlim(-lim, lim); ax.set_ylim(-lim * 0.75, lim * 0.75)
ax.set_xlabel("平均泊数の変化（%、2024→2025年）"); ax.set_ylabel("1泊あたり支出の変化（%、名目）")
ax.set_title("2025年の1人あたりは泊数が延びた分で増え、1泊あたりは下がった（円の大きさ＝回答数）", fontsize=10.5)
save(fig, "f270_6_reask_nights.png")
print(sorted(os.listdir(FG)))
