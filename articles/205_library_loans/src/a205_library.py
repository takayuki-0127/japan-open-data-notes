"""A205 人口あたりの図書館の貸出冊数は、どこが多いか"""
from common import *

d, p = load()
pop = p.set_index("pref")
d23 = d[d.year == 2023].set_index("pref")
d20 = d[d.year == 2020].set_index("pref")
t = pd.DataFrame({
    "libs": d23.libs, "loans": d23.loans, "loans_child": d23.loans_child, "borrowers": d23.borrowers,
    "pop23": pop.p2023 * 1000, "pop20": pop.p2020 * 1000, "loans20": d20.loans})
t["per_cap"] = t.loans / t.pop23
t["per_cap20"] = t.loans20 / t.pop20
t["libs_per100k"] = t.libs / t.pop23 * 1e5
t["child_share"] = t.loans_child / t.loans * 100
t["borrow_per_cap"] = t.borrowers / t.pop23
t["loans_per_lib"] = t.loans / t.libs
t["chg_20_23"] = (t.per_cap / t.per_cap20 - 1) * 100
nat = t.loc["全国"]; pr = t.drop("全国").sort_values("per_cap", ascending=False)
pr.round(3).to_csv(RES / "pref_2023.csv")

# national trend
n = d[d.pref == "全国"].set_index("year")[["libs", "borrowers", "loans", "loans_child"]]
n["child_share"] = n.loans_child / n.loans * 100
n["loans_per_lib"] = n.loans / n.libs
n.round(2).to_csv(RES / "national_trend.csv")

r = np.corrcoef(pr.libs_per100k, pr.per_cap)[0, 1]
r_l = np.corrcoef(np.log(pr.libs_per100k), pr.per_cap)[0, 1]
with open(RES / "summary.txt", "w") as f:
    f.write(f"全国 2023 per_cap={nat.per_cap:.2f} 2020={nat.per_cap20:.2f}\n")
    f.write(f"top5: {[(k, round(v,2)) for k,v in pr.per_cap.head(5).items()]}\n")
    f.write(f"bottom5: {[(k, round(v,2)) for k,v in pr.per_cap.tail(5).items()]}\n")
    f.write(f"max/min ratio {pr.per_cap.max()/pr.per_cap.min():.2f}\n")
    f.write(f"median {pr.per_cap.median():.2f}\n")
    f.write(f"corr libs_per100k vs per_cap r={r:.2f} (log r={r_l:.2f})\n")
    f.write(f"libs_per100k top: {[(k, round(v,2)) for k,v in pr.libs_per100k.sort_values(ascending=False).head(5).items()]}\n")
    f.write(f"libs_per100k bottom: {[(k, round(v,2)) for k,v in pr.libs_per100k.sort_values().head(5).items()]}\n")
    f.write(f"chg 20->23 national {nat.chg_20_23:.1f}% pref up count {(pr.chg_20_23>0).sum()}\n")
    f.write(f"child share national {nat.child_share:.1f}; top {pr.child_share.idxmax()} {pr.child_share.max():.1f}; bottom {pr.child_share.idxmin()} {pr.child_share.min():.1f}\n")
    f.write(n.round(1).to_string() + "\n")
    f.write(pr[["per_cap", "per_cap20", "libs_per100k", "loans_per_lib", "child_share"]].round(2).to_string() + "\n")

# fig1 ranking
fig, ax = plt.subplots(figsize=(7.5, 10))
s = pr.per_cap.sort_values()
cols = [ORANGE if k in s.tail(5).index else (GRAY if k in s.head(5).index else BLUE) for k in s.index]
ax.barh(s.index, s.values, color=cols)
ax.axvline(nat.per_cap, color=INK, lw=1, ls="--"); ax.text(nat.per_cap + 0.05, 0.3, f"全国 {nat.per_cap:.2f}冊", fontsize=9)
for i, v in enumerate(s.values): ax.text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=7.5)
ax.set_xlabel("人口1人あたりの貸出冊数（冊、令和5年度間）"); ax.tick_params(axis="y", labelsize=8.5)
ax.set_title("公立・私立図書館の貸出冊数を人口で割ると（2023年度）")
save(fig, "a205_ranking.png")

# fig2 national trend
fig, ax = plt.subplots(figsize=(8, 4.6))
yrs = n.index.astype(str) + "年度"
ax.bar(yrs, n.loans / 1e6, color=LIGHT, label="貸出冊数（百万冊）")
ax.bar(yrs, n.loans_child / 1e6, color=BLUE, label="うち児童書")
for i, (a, b) in enumerate(zip(n.loans / 1e6, n.loans_child / 1e6)):
    ax.text(i, a + 8, f"{a:.0f}", ha="center", fontsize=10); ax.text(i, b / 2, f"{b:.0f}\n({b/a*100:.1f}%)", ha="center", color="white", fontsize=9)
ax.set_ylabel("百万冊"); ax.set_ylim(0, 760); ax.legend(loc="upper right", frameon=False)
ax.set_title("全国の図書館の貸出冊数（社会教育調査の調査年）")
save(fig, "a205_trend.png")

# fig3 scatter
fig, ax = plt.subplots(figsize=(7.5, 5.2))
ax.scatter(pr.libs_per100k, pr.per_cap, color=BLUE, s=28)
for k in list(pr.per_cap.head(5).index) + list(pr.per_cap.tail(4).index) + list(pr.libs_per100k.sort_values().tail(3).index) + ["大阪府", "北海道", "神奈川県", "愛知県"]:
    ax.annotate(k, (pr.libs_per100k[k], pr.per_cap[k]), fontsize=8, xytext=(3, 3), textcoords="offset points")
ax.set_xlabel("人口10万人あたりの図書館数（館）"); ax.set_ylabel("人口1人あたりの貸出冊数（冊）")
ax.set_title(f"図書館の多さと貸出冊数（2023年度、相関係数 {r:.2f}）")
save(fig, "a205_scatter.png")
