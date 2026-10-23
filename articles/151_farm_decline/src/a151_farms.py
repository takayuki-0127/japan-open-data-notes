"""農業経営体は5年（2020→2025年）で何割減ったか。都道府県ごとの減り方と、何と一緒に動いていたか"""
from common import *

d = load("pref_2020_2025.csv").set_index("pref")
age = load("national_age.csv")
d["chg"] = d.k25 / d.k20 - 1
d["chg_ind"] = d.ind25 / d.ind20 - 1
d["chg_corp"] = d.corp25 / d.corp20 - 1
d["old75_20"] = d.age75p20 / d.ind20            # 2020年の個人経営体のうち、経営主75歳以上の割合
d["nosucc25"] = d.succ_no / d.succ_tot          # 2025年、後継者を確保していない個人経営体の割合
d["corp_share25"] = d.corp25 / d.k25
d.to_csv(RES / "a151_pref.csv", encoding="utf-8")
p = d.drop(index="全国")
n = d.loc["全国"]
L = [f"全国 農業経営体 {n.k20:,.0f}→{n.k25:,.0f}（{n.chg:.1%}）、個人 {n.ind20:,.0f}→{n.ind25:,.0f}（{n.chg_ind:.1%}）、団体 {n.grp20:,.0f}→{n.grp25:,.0f}（{n.grp25/n.grp20-1:+.1%}）、法人 {n.corp20:,.0f}→{n.corp25:,.0f}（{n.chg_corp:+.1%}）",
     f"法人の割合 {n.corp20/n.k20:.1%}→{n.corp25/n.k25:.1%}",
     f"都道府県の減少率 中央値 {p.chg.median():.1%}、最大 {p.chg.idxmin()} {p.chg.min():.1%}、最小 {p.chg.idxmax()} {p.chg.max():.1%}",
     "減少率の大きい順:\n" + p.chg.sort_values().head(8).round(3).to_string(),
     "減少率の小さい順:\n" + p.chg.sort_values(ascending=False).head(8).round(3).to_string(),
     f"相関 減少率×2020年75歳以上割合 r={p.chg.corr(p.old75_20):.2f}、×2025年後継者なし割合 r={p.chg.corr(p.nosucc25):.2f}、×2025年法人割合 r={p.chg.corr(p.corp_share25):.2f}",
     f"全国 後継者を確保していない割合（2025、個人経営体） {n.nosucc25:.1%}",
     f"経営主の年齢 最頻 2020 {age.loc[age.y2020.idxmax(),'age']}、2025 {age.loc[age.y2025.idxmax(),'age']}；75歳以上 2020 {n.age75p20/n.ind20:.1%} 2025 {n.age75p25/n.ind25:.1%}；65歳以上 2020 {n.age65p20/n.ind20:.1%} 2025 {n.age65p25/n.ind25:.1%}"]
a = age.set_index("age")
L.append("年齢階層別の減少率:\n" + (a.y2025 / a.y2020 - 1).round(3).to_string())
(RES / "a151_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：都道府県別の減少率
s = p.chg.sort_values()
fig, ax = plt.subplots(figsize=(9.5, 9))
cols = [ORANGE if v <= s.quantile(0.25) else (GREEN if v >= s.quantile(0.75) else BLUE) for v in s]
ax.barh(range(len(s)), s.values * 100, color=cols, height=0.7)
ax.axvline(n.chg * 100, color=INK, lw=1, ls="--")
ax.text(n.chg * 100 - 0.4, len(s) - 0.3, f"全国 {n.chg:.1%}", ha="right", va="top", fontsize=10)
ax.set_yticks(range(len(s))); ax.set_yticklabels(s.index, fontsize=8.5)
ax.set_xlabel("農業経営体数の増減率（2020→2025年、%）")
ax.set_title("都道府県別の農業経営体の減り方（2020→2025年）")
save(fig, "a151_pref.png")

# 図2：経営主の年齢階層別（個人経営体）
fig, ax = plt.subplots(figsize=(9.5, 4.4))
x = np.arange(len(age))
ax.bar(x - 0.2, age.y2020 / 1e4, width=0.4, color=GRAY, label="2020年")
ax.bar(x + 0.2, age.y2025 / 1e4, width=0.4, color=BLUE, label="2025年")
ax.set_xticks(x); ax.set_xticklabels(age.age, rotation=45, fontsize=9)
ax.set_ylabel("個人経営体（万）"); ax.legend(frameon=False)
ax.set_title("経営主の年齢別の個人経営体数")
save(fig, "a151_age.png")

# 図3：減少率と後継者がいない割合
fig, ax = plt.subplots(figsize=(9.5, 5))
ax.scatter(p.nosucc25 * 100, p.chg * 100, s=p.k20 / 400, color=BLUE, alpha=0.6, edgecolor="white")
for name in list(s.index[:4]) + list(s.index[-4:]) + ["北海道", "東京"]:
    ax.annotate(name, (p.nosucc25[name] * 100, p.chg[name] * 100), fontsize=8.5, xytext=(4, 2), textcoords="offset points")
ax.set_xlabel("後継者を確保していない個人経営体の割合（2025年、%）"); ax.set_ylabel("農業経営体の増減率（2020→2025年、%）")
ax.set_title(f"減り方と後継者のいない割合（相関 {p.chg.corr(p.nosucc25):.2f}、円の大きさ＝2020年の経営体数）")
save(fig, "a151_succ.png")
