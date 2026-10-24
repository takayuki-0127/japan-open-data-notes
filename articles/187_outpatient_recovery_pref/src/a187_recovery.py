"""病院の外来患者数は、コロナ前（2019年）の水準にどこまで戻ったか：都道府県別（2015〜2025年）"""
from common import *

d = load("hospital_outpatient_pref_2015_2025.csv")
w = d.pivot(index="pref", columns="year", values="outpatient")
order = d.drop_duplicates("pref").set_index("pref").code
w = w.loc[order.sort_values().index]
idx = w.div(w[2019], axis=0) * 100                       # 2019年=100
p = pd.DataFrame({
    "idx2020": idx[2020], "idx2022": idx[2022], "idx2025": idx[2025],
    "best_2021_25": idx[[2021, 2022, 2023, 2024, 2025]].max(axis=1),
    "best_year": idx[[2021, 2022, 2023, 2024, 2025]].idxmax(axis=1),
    "pre_trend": ((w[2019] / w[2015]) ** (1 / 4) - 1) * 100,   # 2015→2019 年率（%）
})
p["post_rate"] = ((w[2025] / w[2019]) ** (1 / 6) - 1) * 100   # 2019→2025 年率（%）
p["trend_2025"] = (1 + p.pre_trend / 100) ** 6 * 100           # 2015〜19年のペースが続いた場合の2025年（2019=100）
p["gap_vs_trend"] = p.idx2025 - p.trend_2025
p["rebound_2022"] = (w[2022] - w[2020]) / (w[2019] - w[2020]) * 100   # 2020年の落ち込みのうち2022年までに戻った割合
p.round(2).to_csv(RES / "a187_pref_recovery.csv")
idx.round(2).to_csv(RES / "a187_index_2019_100.csv")

pr = p.drop("全国")
nat = p.loc["全国"]
L = [f"全国 2019=100: " + " ".join(f"{y}:{idx.loc['全国', y]:.1f}" for y in idx.columns),
     f"全国 2015→2019 年率{nat.pre_trend:+.2f}% / 2019→2025 年率{nat.post_rate:+.2f}% / 2025 傾向線{nat.trend_2025:.1f} 実際{nat.idx2025:.1f} 差{nat.gap_vs_trend:+.1f} / 2022までの戻り{nat.rebound_2022:.0f}%",
     f"県 2020 最小 {pr.idx2020.idxmin()} {pr.idx2020.min():.1f} 最大 {pr.idx2020.idxmax()} {pr.idx2020.max():.1f} 中央値 {pr.idx2020.median():.1f}",
     f"県 2025 最小 {pr.idx2025.idxmin()} {pr.idx2025.min():.1f} 最大 {pr.idx2025.idxmax()} {pr.idx2025.max():.1f} 中央値 {pr.idx2025.median():.1f} / 100以上 {int((pr.idx2025>=100).sum())}県 / 95以上 {int((pr.idx2025>=95).sum())}県 / 90未満 {int((pr.idx2025<90).sum())}県",
     "2025 上位5: " + ", ".join(f"{k}{v:.1f}" for k, v in pr.idx2025.nlargest(5).items()),
     "2025 下位5: " + ", ".join(f"{k}{v:.1f}" for k, v in pr.idx2025.nsmallest(5).items()),
     f"最もよく戻った年（2021〜25）の内訳: " + str(pr.best_year.value_counts().sort_index().to_dict()),
     f"2021〜25の最高でも100未満 {int((pr.best_2021_25<100).sum())}県",
     f"2015→2019 年率 中央値{pr.pre_trend.median():+.2f}% 範囲 {pr.pre_trend.idxmin()}{pr.pre_trend.min():+.2f}%〜{pr.pre_trend.idxmax()}{pr.pre_trend.max():+.2f}%",
     f"pre_trend と idx2025 の相関 r={pr.pre_trend.corr(pr.idx2025):.2f}; idx2020 と idx2025 r={pr.idx2020.corr(pr.idx2025):.2f}",
     f"傾向線との差 中央値{pr.gap_vs_trend.median():+.1f} 範囲 {pr.gap_vs_trend.idxmin()}{pr.gap_vs_trend.min():+.1f}〜{pr.gap_vs_trend.idxmax()}{pr.gap_vs_trend.max():+.1f}; 傾向線より上 {int((pr.gap_vs_trend>0).sum())}県",
     "2020落ち込み 大きい5: " + ", ".join(f"{k}{v:.1f}" for k, v in pr.idx2020.nsmallest(5).items()),
     "2020落ち込み 小さい5: " + ", ".join(f"{k}{v:.1f}" for k, v in pr.idx2020.nlargest(5).items()),
     ]
big = ["東京", "神奈川", "大阪", "愛知", "埼玉", "千葉", "京都", "兵庫", "福岡"]
L.append("大都市圏9都府県 2020 平均{:.1f} 2025 平均{:.1f} / 他38道県 2020 平均{:.1f} 2025 平均{:.1f}".format(
    pr.loc[big].idx2020.mean(), pr.loc[big].idx2025.mean(), pr.drop(big).idx2020.mean(), pr.drop(big).idx2025.mean()))
psy = d.pivot(index="pref", columns="year", values="outpatient_psych")
L.append(f"全国 精神科病院の外来 2019→2020 {psy.loc['全国',2020]/psy.loc['全国',2019]-1:+.1%} 2019→2025 {psy.loc['全国',2025]/psy.loc['全国',2019]-1:+.1%}")
(RES / "a187_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：全国と都道府県の幅（2019年=100）
fig, ax = plt.subplots(figsize=(10, 4.4))
yrs = idx.columns.values
for k in pr.index:
    ax.plot(yrs, idx.loc[k], color=LIGHT, lw=0.8, alpha=0.7)
ax.plot(yrs, idx.loc["全国"], color=BLUE, lw=2.6, marker="o", ms=4, label="全国")
for k, c in [(pr.idx2025.idxmax(), GREEN), (pr.idx2025.idxmin(), ORANGE)]:
    ax.plot(yrs, idx.loc[k], color=c, lw=1.8, label=k)
ax.axhline(100, color=GRAY, lw=0.8, ls=":")
ax.set_xticks(yrs); ax.set_ylabel("2019年=100"); ax.set_ylim(80, 112)
ax.set_title("病院の外来患者延数（2019年=100）：細線は各都道府県")
ax.legend(frameon=False, loc="lower left")
save(fig, "a187_index.png")

# 図2：2025年の水準（2019年=100）を県別に
s = pr.sort_values("idx2025")
fig, ax = plt.subplots(figsize=(10, 9.5))
ax.hlines(range(len(s)), s.idx2020, s.idx2025, color=LIGHT, lw=1.2)
ax.scatter(s.idx2020, range(len(s)), color=GRAY, s=16, label="2020年")
ax.scatter(s.idx2025, range(len(s)), color=BLUE, s=22, label="2025年", zorder=3)
ax.axvline(100, color=GRAY, lw=0.8, ls=":"); ax.axvline(nat.idx2025, color=BLUE, lw=0.8, ls="--")
ax.text(nat.idx2025 + 0.2, len(s) - 0.5, f"全国 {nat.idx2025:.1f}", color=BLUE, fontsize=9)
ax.set_yticks(range(len(s))); ax.set_yticklabels(s.index, fontsize=8.5)
ax.set_xlabel("2019年=100"); ax.set_title("都道府県別の外来患者延数：2020年と2025年（2019年=100）")
ax.legend(frameon=False, loc="lower right")
save(fig, "a187_pref_2025.png")

# 図3：コロナ前の減り方と2025年の水準
fig, ax = plt.subplots(figsize=(8.5, 6))
ax.scatter(pr.pre_trend, pr.idx2025, color=BLUE, s=26)
for k, r in pr.iterrows():
    if r.idx2025 > 94.8 or r.idx2025 < 87 or r.pre_trend < -1.6 or r.pre_trend > 0.15:
        ax.annotate(k, (r.pre_trend, r.idx2025), fontsize=8.5, xytext=(3, 3), textcoords="offset points")
xs = np.linspace(pr.pre_trend.min(), pr.pre_trend.max(), 50)
ax.plot(xs, (1 + xs / 100) ** 6 * 100, color=GRAY, lw=1, ls="--", label="2015〜19年のペースが続いた場合")
ax.set_xlabel("2015→2019年の年率（%）"); ax.set_ylabel("2025年（2019年=100）")
ax.set_title(f"コロナ前の減り方と2025年の水準（相関係数 {pr.pre_trend.corr(pr.idx2025):.2f}）")
ax.legend(frameon=False, loc="lower right")
save(fig, "a187_trend.png")
