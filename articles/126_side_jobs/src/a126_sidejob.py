"""副業をしている人はどんな働き方・年収・職業に多いか（令和4年就業構造基本調査、集計表）"""
from common import *
import statsmodels.api as sm

a = t206()
STAT = ["うち自営業主", "会社などの役員", "正規の職員・従業員", "非正規の職員・従業員"]
LAB = {"うち自営業主": "自営業主", "会社などの役員": "会社などの役員", "正規の職員・従業員": "正規の職員・従業員",
       "非正規の職員・従業員": "非正規の職員・従業員", "総数": "有業者全体"}
INC = [i for i in a["本業の所得"].unique() if i != "総数"]

def rate(df):
    p = df.pivot_table(index=[c for c in df.columns if c not in ("副業", "n")], columns="副業", values="n", sort=False)
    p["rate"] = p["副業あり"] / p["総数"] * 100
    return p.reset_index()

base = rate(a[a["育児"] == "総数"].drop(columns="育児"))
base.round(2).to_csv(RES / "a126_rate_income_status_sex.csv", index=False, encoding="utf-8-sig")

# 1) 本業の所得別の副業者比率
g = base[base["男女"] == "総数"]
fig, ax = plt.subplots(figsize=(9, 5))
for s, c in [("総数", INK), ("正規の職員・従業員", BLUE), ("非正規の職員・従業員", ORANGE), ("うち自営業主", GREEN)]:
    d = g[(g["本業の地位"] == s) & (g["本業の所得"] != "総数")]
    ax.plot(range(len(d)), d.rate, marker="o", color=c, label=LAB[s], lw=2.2 if s == "総数" else 1.5)
ax.set_xticks(range(len(INC))); ax.set_xticklabels([i.replace("万円", "") for i in INC], rotation=60, fontsize=8)
ax.set_xlabel("本業の年間所得（万円）"); ax.set_ylabel("副業がある人の割合（%）")
ax.set_ylim(0, 26)
ax.set_title("副業をする人は、本業の所得が低い人と高い人に多い")
ax.legend(fontsize=9)
note(ax, y=-0.3)
plt.tight_layout(); plt.savefig(FIG / "a126_income.png"); plt.close()

# 2) 働き方・男女別、グループ化したロジスティック回帰
s2 = base[(base["本業の所得"] == "総数") & base["本業の地位"].isin(["総数"] + STAT + ["（別掲）フリーランス"])]
s2.round(2).to_csv(RES / "a126_rate_status_sex.csv", index=False, encoding="utf-8-sig")
m = base[base["男女"].isin(["男", "女"]) & base["本業の地位"].isin(STAT) & (base["本業の所得"] != "総数")].copy()
rows = []
for _, r in m.iterrows():
    rows.append({**r, "y": 1, "w": r["副業あり"]}); rows.append({**r, "y": 0, "w": r["総数"] - r["副業あり"]})
d = pd.DataFrame(rows); d = d[d.w > 0]
X = pd.get_dummies(d[["男女", "本業の地位", "本業の所得"]], drop_first=False).astype(float)
X = X.drop(columns=["男女_男", "本業の地位_正規の職員・従業員", "本業の所得_300～399万円"])
X = sm.add_constant(X)
fit = sm.GLM(d.y, X, family=sm.families.Binomial(), freq_weights=d.w / 100).fit()
orr = np.exp(fit.params).rename("odds_ratio").to_frame()
orr.round(3).to_csv(RES / "a126_logit_odds_ratio.csv", encoding="utf-8-sig")
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1, 1.3]})
ax = axes[0]
order = ["総数"] + STAT + ["（別掲）フリーランス"]
for k, (sx, c) in enumerate([("男", BLUE), ("女", ORANGE)]):
    v = [s2[(s2["本業の地位"] == o) & (s2["男女"] == sx)].rate.iloc[0] for o in order]
    ax.barh(np.arange(len(order)) + (k - 0.5) * 0.38, v, height=0.38, color=c, label=sx)
    for i, vv in enumerate(v): ax.text(vv, i + (k - 0.5) * 0.38, f" {vv:.1f}", va="center", fontsize=8)
ax.set_yticks(range(len(order))); ax.set_yticklabels([LAB.get(o, "フリーランス（別掲）") for o in order], fontsize=9)
ax.invert_yaxis(); ax.set_xlabel("副業がある人の割合（%）"); ax.legend(fontsize=9); ax.set_title("働き方・男女別")
ax = axes[1]
inc_or = [orr.loc[f"本業の所得_{i}", "odds_ratio"] if f"本業の所得_{i}" in orr.index else 1.0 for i in INC]
ax.plot(range(len(INC)), inc_or, marker="o", color=INK)
ax.axhline(1, color=GRAY, lw=1)
ax.set_xticks(range(len(INC))); ax.set_xticklabels([i.replace("万円", "") for i in INC], rotation=60, fontsize=8)
ax.set_ylabel("オッズ比（300〜399万円＝1）"); ax.set_title("男女・働き方をそろえた所得の効果")
note(axes[0], y=-0.2)
plt.tight_layout(); plt.savefig(FIG / "a126_status.png"); plt.close()

# 3) 本業の職業と副業の職業
c = t076()
cnt = c[(c["男女"] == "総数") & (c["本業の地位"] == "総数") & (c["本業の就業日数・時間"] == "総数") & (c["本業の職業"] != "総数")][["本業の職業", "n"]]
b = t084()
gb = b[(b["男女"] == "総数") & (b["本業の地位"] == "総数")]
p = gb.pivot_table(index="本業の職業", columns="副業の職業", values="n", sort=False)
occ = [o for o in p.index if o != "総数"]
same = pd.DataFrame({"本業の職業": occ, "副業がある人": [p.loc[o, "総数"] for o in occ],
                     "同じ職業の割合": [p.loc[o, o] / p.loc[o, "総数"] * 100 for o in occ]})
same = same.merge(cnt.rename(columns={"n": "表76の人数"}), on="本業の職業", how="left")
same["構成比"] = same["副業がある人"] / p.loc["総数", "総数"] * 100
same.round(2).to_csv(RES / "a126_occupation.csv", index=False, encoding="utf-8-sig")
side = (p.loc["総数"].drop("総数") / p.loc["総数", "総数"] * 100).rename("副業の職業の構成比")
side.round(2).to_csv(RES / "a126_side_occupation.csv", encoding="utf-8-sig")
s3 = same[same["本業の職業"] != "分類不能の職業"].sort_values("副業がある人")
fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
axes[0].barh(s3["本業の職業"], s3["副業がある人"] / 1e4, color=BLUE)
for i, v in enumerate(s3["副業がある人"] / 1e4): axes[0].text(v, i, f" {v:.0f}", va="center", fontsize=8)
axes[0].set_xlabel("副業がある人（万人）"); axes[0].set_title("本業の職業別の人数")
axes[1].barh(s3["本業の職業"], s3["同じ職業の割合"], color=ORANGE)
for i, v in enumerate(s3["同じ職業の割合"]): axes[1].text(v, i, f" {v:.0f}%", va="center", fontsize=8)
axes[1].set_xlabel("副業も同じ職業の割合（%）"); axes[1].set_title("副業も本業と同じ職業か")
note(axes[0], y=-0.12)
plt.tight_layout(); plt.savefig(FIG / "a126_occupation.png"); plt.close()

print(s2[["男女", "本業の地位", "総数", "副業あり", "rate"]].round(1).to_string())
print(orr.round(2).to_string())
print(same.round(1).to_string()); print(side.round(1).sort_values().tail(4))
