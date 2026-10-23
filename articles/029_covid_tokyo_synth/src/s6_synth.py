"""S6：コロナで東京への転入超過はどれだけ減ったか。合成コントロール法（水準をそろえた版）で「コロナがなかった東京」を作る"""
from common import *
from scipy.optimize import minimize
d, _ = read("SSDSE-B-2026"); d = d.rename(columns={d.columns[0]: "year"})
d["net"] = (d.A5101 - d.A5102) / d.A1101 * 1000          # 転入超過（人口1,000人あたり、日本人の移動）
P = d.pivot(index="year", columns="Prefecture", values="net")
PRE, POST = list(range(2012, 2020)), list(range(2020, 2024))
NEAR = ["埼玉県", "千葉県", "神奈川県"]                    # 東京から移った人の受け皿になりうるので、比較の候補から外す

def synth(target, donors):
    """前の期間の平均を引いてから、ウェイト（0以上・合計1）で前の期間の動きを再現する"""
    Y = P - P.loc[PRE].mean()
    y0, X0 = Y.loc[PRE, target].values, Y.loc[PRE, donors].values
    k = len(donors); f = lambda w: ((y0 - X0 @ w) ** 2).sum()
    r = minimize(f, np.ones(k) / k, bounds=[(0, 1)] * k, constraints={"type": "eq", "fun": lambda w: w.sum() - 1}, method="SLSQP", options={"maxiter": 500})
    w = pd.Series(r.x, index=donors)
    gap = Y[target] - Y[donors] @ w
    pre, post = np.sqrt((gap.loc[PRE] ** 2).mean()), np.sqrt((gap.loc[POST] ** 2).mean())
    return w, gap, pre, post

donors = [c for c in P.columns if c not in ["東京都"] + NEAR]
w, gap, pre, post = synth("東京都", donors)
synth_level = P.loc[PRE, "東京都"].mean() + (P[donors] - P.loc[PRE, donors].mean()) @ w
print(w[w > 0.01].sort_values(ascending=False).round(3)); print(gap.round(2)); print("RMSPE pre/post", round(pre, 3), round(post, 3))

# プラセボ：ほかの県にも同じことをして、東京のずれが特別かどうか
rows = []
for t in donors:
    _, g, a, b = synth(t, [c for c in donors if c != t]); rows.append((t, a, b, b / a, g.loc[POST].mean()))
pl = pd.DataFrame(rows, columns=["pref", "rmspe_pre", "rmspe_post", "ratio", "gap_post_mean"])
pl.loc[len(pl)] = ["東京都", pre, post, post / pre, gap.loc[POST].mean()]
pl = pl.sort_values("rmspe_post", ascending=False).reset_index(drop=True)   # 前の期間の当てはまりがほぼ0の県が多く、比で順位をつけると不安定なので、後の期間のずれの大きさで比べる
rank = int(pl.index[pl.pref == "東京都"][0]) + 1
print(pl.head(8).round(2)); print("東京の順位", rank, "/", len(pl))
# 1都3県も含めた場合（感度）
w2, gap2, pre2, post2 = synth("東京都", [c for c in P.columns if c != "東京都"])
lost = (gap.loc[POST] * P.loc[POST].index.map(lambda y: d[(d.year == y) & (d.Prefecture == "東京都")].A1101.iloc[0]) / 1000)
s = {"tokyo_2019": P.loc[2019, "東京都"], "tokyo_2021": P.loc[2021, "東京都"], "tokyo_2023": P.loc[2023, "東京都"],
     "gap_2020": gap[2020], "gap_2021": gap[2021], "gap_2022": gap[2022], "gap_2023": gap[2023], "gap_post_mean": gap.loc[POST].mean(),
     "rmspe_pre": pre, "rmspe_post": post, "ratio": post / pre, "rank_by_post_rmspe": rank, "second_post_rmspe": pl.rmspe_post.iloc[1], "second_pref": pl.pref.iloc[1], "n_units": len(pl), "perm_p": rank / len(pl),
     "lost_people_2020_23": lost.sum(), "gap_post_mean_with_near": gap2.loc[POST].mean(),
     "near_2019_mean": P.loc[2019, NEAR].mean(), "near_2021_mean": P.loc[2021, NEAR].mean()}
pd.Series(s).to_csv(RES / "s6_summary.csv", header=["value"]); print(pd.Series(s))
w[w > 0.001].sort_values(ascending=False).round(3).to_csv(RES / "s6_weights.csv", header=["weight"], encoding="utf-8-sig")
pl.round(3).to_csv(RES / "s6_placebo.csv", index=False, encoding="utf-8-sig")
pd.DataFrame({"tokyo": P["東京都"], "synthetic": synth_level, "gap": gap}).round(3).to_csv(RES / "s6_path.csv", encoding="utf-8-sig")

SRC = source("SSDSE-県別推移（SSDSE-B-2026）")
fig, ax = plt.subplots(figsize=(9, 4.4))
ax.plot(P.index, P["東京都"], marker="o", color=ORANGE, label="東京都（実際）")
ax.plot(P.index, synth_level, marker="o", color=BLUE, ls="--", label="合成した東京（コロナがなかった場合の目安）")
ax.axvspan(2019.5, 2023.5, color="#f1efe8", zorder=0); ax.text(2019.6, 6.9, "2020年以降", fontsize=9, color="#52514e")
ax.set_ylim(0, 7.5); ax.set_ylabel("転入超過（人口1,000人あたり）"); ax.legend(frameon=False, loc="lower left", fontsize=9)
ax.set_title("2021年、東京の転入超過は「合成した東京」より5人少なかった", loc="left")
fig.text(0.01, -0.04, SRC + "（日本人の移動。比較の候補から埼玉・千葉・神奈川を除く）", fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "s6_synth.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4.4))
for t in donors:
    _, g, a, _b = synth(t, [c for c in donors if c != t])
    ax.plot(g.index, g, color=GRAY, lw=0.6, alpha=0.5)
ax.plot(gap.index, gap, color=ORANGE, lw=2.4, label="東京都")
ax.axhline(0, color=INK, lw=0.7); ax.axvline(2019.5, color=INK, lw=0.6, ls=":")
ax.set_ylabel("実際 − 合成（人口1,000人あたり）"); ax.legend(frameon=False, loc="lower left")
ax.set_title(f"ほかの43道府県で同じことをしても、東京ほど大きくずれた県はない", loc="left")
fig.text(0.01, -0.04, SRC + "（灰色＝各道府県を「処置を受けた県」とみなしたプラセボ）", fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "s6_placebo.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.plot(P.index, P["東京都"], marker="o", color=ORANGE, label="東京都")
for c, col in zip(NEAR, [BLUE, "#3aa07a", "#7a5bd6"]): ax.plot(P.index, P[c], marker=".", color=col, label=c)
ax.axhline(0, color=INK, lw=0.6); ax.set_ylabel("転入超過（人口1,000人あたり）"); ax.legend(frameon=False, ncol=4, fontsize=9, loc="lower left")
ax.set_title("東京が減った2020〜21年、周りの3県は増えた", loc="left")
fig.text(0.01, -0.05, SRC + "（日本人の移動）", fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "s6_near.png"); plt.close(fig)
