"""図1〜5"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap
from common import monthly, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

d = monthly()
mc = pd.read_csv(RES / "monthly_counterfactual.csv", parse_dates=["date"])
cp = pd.read_csv(RES / "cumulative_path.csv", parse_dates=["date"])

# 図1：実際と「なかった場合」（SARIMA、95%・80%区間）
s = mc[mc.model == "SARIMA"]
fig, ax = plt.subplots(figsize=(9, 4.6))
h = d.loc["2015":"2019"]
ax.plot(h.index, h.births / 1e4, color=INK, lw=1.6, label="実際（学習に使った期間）")
ax.fill_between(s.date, s.lo95 / 1e4, s.hi95 / 1e4, color=LIGHT, alpha=0.55, lw=0, label="なかった場合の95%区間")
ax.fill_between(s.date, s.lo80 / 1e4, s.hi80 / 1e4, color=LIGHT, alpha=0.9, lw=0, label="同 80%区間")
ax.plot(s.date, s.cf / 1e4, color=BLUE, lw=2, label="なかった場合（SARIMA の予測）")
ax.plot(s.date, s.actual / 1e4, color=ORANGE, lw=2, label="実際（2020年以降）")
j = s[s.date == "2021-01-01"].iloc[0]
ax.scatter([j.date], [j.actual / 1e4], s=60, color=ORANGE, edgecolor="white", zorder=5)
ax.annotate(f"2021年1月\n実際 {j.actual/1e4:.2f}万人\n予測 {j.cf/1e4:.2f}万人（−{(1-j.actual/j.cf)*100:.1f}%）",
            (j.date, j.actual / 1e4), xytext=(30, -62), textcoords="offset points", fontsize=9,
            arrowprops=dict(arrowstyle="-", color=GRAY))
ax.axvline(pd.Timestamp("2020-01-01"), color=GRAY, lw=0.8, ls="--")
ax.set_ylabel("月の出生数（万人）"); ax.set_ylim(3.5, 9.5)
ax.set_title("出生数：実際と「コロナがなかった場合」の予測（2010〜19年で学習）", loc="left")
ax.legend(fontsize=8.5, frameon=False, loc="lower left", ncol=2); ax.grid(axis="y", color="#e6e6e6", lw=0.6)
save(fig, "f01_counterfactual.png")

# 図2：累積の差
fig, ax = plt.subplots(figsize=(9, 4.4))
for name, col in [("SARIMA", BLUE), ("3モデル統合", GREEN)]:
    c = cp[(cp.model == name) & (cp.date <= "2022-12-01")]
    ax.fill_between(c.date, c.lo95 / 1e4, c.hi95 / 1e4, color=col, alpha=0.12, lw=0)
    ax.plot(c.date, c.cum_gap / 1e4, color=col, lw=2, label=f"{name}（線＝点推定、帯＝95%区間）")
ax.axhline(0, color=INK, lw=0.8)
c = cp[(cp.model == "SARIMA") & (cp.date == "2021-02-01")].iloc[0]
ax.annotate("2020年12月〜21年2月の\n3か月で約1.1万人下振れ", (c.date, c.cum_gap / 1e4), xytext=(30, -70),
            textcoords="offset points", fontsize=9, arrowprops=dict(arrowstyle="-", color=GRAY))
ax.set_ylabel("実際 − なかった場合 の累積（万人）")
ax.set_title("2020年1月からの累積の差（2022年まで）：区間はゼロをまたいだまま", loc="left")
ax.legend(fontsize=9, frameon=False, loc="lower left"); ax.grid(axis="y", color="#e6e6e6", lw=0.6)
save(fig, "f02_cumulative.png")

# 図3：モデル・設定ごとの比較（2020年12月〜21年2月、2020〜22年の累積）
rob = pd.read_csv(RES / "robustness.csv")
cg = pd.read_csv(RES / "cumulative_gap.csv")
fig, axes = plt.subplots(1, 2, figsize=(10, 5.2), sharey=True)
order = [(st, m) for st in rob.setting.unique() for m in ["SARIMA", "ETS", "Prophet", "3モデル統合"]]
labels = [f"{st.replace('基本：2010-19学習・日数調整あり', '基本')}｜{m}" for st, m in order]
ypos = np.arange(len(order))[::-1]
win = pd.read_csv(RES / "robustness_window.csv")
for ax, (col, lo, hi, title) in zip(axes, [("gap", "gap_lo95", "gap_hi95", "2020年12月〜21年2月の差"),
                                          ("gap_2020_2022", "gap_2020_2022_lo", "gap_2020_2022_hi", "2020〜22年の累積の差")]):
    for y, (st, m) in zip(ypos, order):
        r = (win if col == "gap" else rob).query("setting == @st and model == @m").iloc[0]
        color = BLUE if m == "SARIMA" else (GREEN if m == "3モデル統合" else GRAY)
        ax.plot([r[lo] / 1e4, r[hi] / 1e4], [y, y], color=color, lw=2, solid_capstyle="round")
        ax.scatter([r[col] / 1e4], [y], color=color, s=36, zorder=3, edgecolor="white")
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_title(title, loc="left", fontsize=11); ax.set_xlabel("実際 − なかった場合（万人、95%区間）")
    ax.grid(axis="x", color="#e6e6e6", lw=0.6)
axes[0].set_yticks(ypos); axes[0].set_yticklabels(labels, fontsize=8)
fig.suptitle("16通り中11通りで冬の落ち込みはゼロより下。3年累積はほぼすべてゼロをまたぐ", x=0.01, ha="left", fontsize=13)
save(fig, "f03_models.png")

# 図4：婚姻件数（実際と2010〜19年の傾向）と、前年の婚姻1件あたりの出生数
a = pd.read_csv(RES / "annual_births_marriages.csv")
mv = pd.read_csv(RES / "marriage_vs_trend.csv")
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
ax = axes[0]
ax.plot(a.year, a.marriages / 1e4, color=INK, lw=1.8, marker="o", ms=3.5, label="実際")
ax.fill_between(mv.year, mv.lo95 / 1e4, mv.hi95 / 1e4, color=LIGHT, alpha=0.8, lw=0, label="2010〜19年の傾向の95%予測区間")
ax.plot(mv.year, mv.trend / 1e4, color=BLUE, lw=2, label="傾向を延ばした値")
ax.set_xlim(2005, 2025.5); ax.set_ylim(40, 80)
ax.set_title("婚姻件数（万件）：2020年に傾向線から外れた", loc="left", fontsize=11)
ax.legend(fontsize=8.5, frameon=False, loc="lower left"); ax.grid(axis="y", color="#e6e6e6", lw=0.6)
ax = axes[1]
ratio = a.births / a.marriages.shift(1)
ax.plot(a.year, ratio, color=ORANGE, lw=2, marker="o", ms=3.5)
ax.axhspan(ratio[(a.year >= 2010) & (a.year <= 2018)].min(), ratio[(a.year >= 2010) & (a.year <= 2018)].max(),
           color=GRAY, alpha=0.15, lw=0)
ax.text(2005.3, ratio[(a.year >= 2010) & (a.year <= 2018)].max() - 0.008, "2010〜18年の幅", fontsize=8.5, color=GRAY)
ax.annotate("2020年は分母の2019年が\n改元の婚姻増で大きい", (2020, ratio[a.year == 2020].iloc[0]), xytext=(-125, -10),
            textcoords="offset points", fontsize=8.5, arrowprops=dict(arrowstyle="-", color=GRAY))
ax.set_xlim(2005, 2025.5)
ax.set_title("出生数 ÷ 前年の婚姻件数", loc="left", fontsize=11); ax.grid(axis="y", color="#e6e6e6", lw=0.6)
save(fig, "f04_marriage.png")

# 図5：都道府県のタイル地図（2020〜22年の差、%）
pg = pd.read_csv(RES / "pref_gap.csv")
pg = pg[(pg.period == "2020-2022") & (pg.window == "2014-2019")]
TILE = {"北海道": (12, 0), "青森": (12, 1), "秋田": (11, 2), "岩手": (12, 2), "福井": (6, 3), "石川": (7, 3), "富山": (8, 3), "新潟": (9, 3), "山形": (11, 3), "宮城": (12, 3),
        "島根": (2, 4), "鳥取": (3, 4), "兵庫": (4, 4), "京都": (5, 4), "滋賀": (6, 4), "岐阜": (7, 4), "長野": (8, 4), "群馬": (9, 4), "栃木": (10, 4), "福島": (11, 4),
        "山口": (1, 5), "広島": (2, 5), "岡山": (3, 5), "大阪": (4, 5), "奈良": (5, 5), "三重": (6, 5), "愛知": (7, 5), "山梨": (8, 5), "埼玉": (9, 5), "茨城": (10, 5),
        "佐賀": (0, 6), "福岡": (1, 6), "愛媛": (2, 6), "香川": (3, 6), "徳島": (4, 6), "和歌山": (5, 6), "静岡": (7, 6), "神奈川": (8, 6), "東京": (9, 6), "千葉": (10, 6),
        "長崎": (0, 7), "熊本": (1, 7), "大分": (2, 7), "高知": (3, 7), "鹿児島": (0, 8), "宮崎": (1, 8), "沖縄": (0, 9)}
cmap = LinearSegmentedColormap.from_list("div", [ORANGE, "#f4f4f2", BLUE])
norm = TwoSlopeNorm(vmin=-6, vcenter=0, vmax=6)
fig, ax = plt.subplots(figsize=(8.6, 6.4))
for _, r in pg.iterrows():
    x, y = TILE[r.pref]
    ax.add_patch(plt.Rectangle((x, -y), 0.94, 0.94, color=cmap(norm(r.gap_pct)), ec="white", lw=1.5))
    ax.text(x + 0.47, -y + 0.6, r.pref, ha="center", va="center", fontsize=7.5, color=INK)
    ax.text(x + 0.47, -y + 0.28, f"{r.gap_pct:+.1f}" + ("*" if r.outside_low or r.outside_high else ""),
            ha="center", va="center", fontsize=7.5, color=INK, fontweight="bold" if r.outside_low else "normal")
ax.set_xlim(-0.2, 13.2); ax.set_ylim(-9.2, 1.1); ax.axis("off")
sm_ = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
cb = fig.colorbar(sm_, ax=ax, orientation="horizontal", fraction=0.04, pad=0.02, shrink=0.5)
cb.set_label("2020〜22年の出生数：実際と傾向の差（%）　* は95%区間の外", fontsize=9)
ax.set_title("都道府県別：ほぼすべての県で傾向より少なめ。ただし区間の外は2県だけ", loc="left", fontsize=12)
save(fig, "f05_pref_map.png")
print("ok")
