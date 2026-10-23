"""P1：2050年に人口が半分以下になる市町村はいくつか。将来推計（2020→2050年）の変化を「出生と死亡（封鎖人口）」と「人の移動」に分ける"""
from common import *
p = munis(read_pop("kekkahyo1.xlsx")).set_index("code"); c = munis(read_pop("sankoichiran.xlsx")).set_index("code")
o = pd.read_excel(RAW / "kekkahyo3_3.xlsx", header=None, skiprows=5).iloc[:, :11]; o.columns = ["code", "kind", "pref", "muni"] + YRS
o = o[o.code.notna()]; o["code"] = o.code.astype(int).astype(str).str.zfill(5); o = o.set_index("code")
d = p[["kind", "pref", "muni", 2020, 2050]].rename(columns={2020: "pop2020", 2050: "proj2050"})
d["closed2050"] = c[2050]; d["old2020"] = o[2020]; d["old2050"] = o[2050]
d["idx"] = d.proj2050 / d.pop2020 * 100
d["natural"] = (d.closed2050 / d.pop2020 - 1) * 100          # 出生と死亡だけの変化（人の移動がないと仮定）
d["migration"] = (d.proj2050 - d.closed2050) / d.pop2020 * 100  # 人の移動による差
d["total"] = d.idx - 100
d.round(2).to_csv(RES / "p1_munis.csv", encoding="utf-8-sig")
bins = pd.cut(d.idx, [0, 50, 60, 70, 80, 90, 100, 1000], right=False, labels=["50未満", "50〜60", "60〜70", "70〜80", "80〜90", "90〜100", "100以上"])
dist = bins.value_counts().sort_index(); dist.to_csv(RES / "p1_dist.csv", header=["n"], encoding="utf-8-sig"); print(dist)
d["type"] = np.select([(d.natural >= 0) & (d.migration >= 0), (d.natural < 0) & (d.migration >= 0), (d.natural >= 0) & (d.migration < 0)], ["自然増・転入増", "自然減・転入増", "自然増・転出増"], "自然減・転出増")
tp = d.groupby("type").agg(n=("idx", "size"), median_idx=("idx", "median"), pop2020=("pop2020", "sum")); tp.to_csv(RES / "p1_types.csv", encoding="utf-8-sig"); print(tp)
top = d.sort_values("idx", ascending=False)[["pref", "muni", "pop2020", "idx", "natural", "migration"]]
top.head(15).round(1).to_csv(RES / "p1_top.csv", encoding="utf-8-sig"); top.tail(15).round(1).to_csv(RES / "p1_bottom.csv", encoding="utf-8-sig")
print(top.head(10).round(1).to_string()); print(top.tail(10).round(1).to_string())
big = d[d.pop2020 >= 300000].sort_values("migration")[["pref", "muni", "pop2020", "idx", "natural", "migration"]]; big.round(1).to_csv(RES / "p1_big_cities.csv", encoding="utf-8-sig")
print(big.round(1).tail(8).to_string()); print(big.round(1).head(5).to_string())
nat = {"pop2020": d.pop2020.sum(), "proj2050": d.proj2050.sum(), "closed2050": d.closed2050.sum()}
s = {"n_munis": len(d), "n_below50": int((d.idx < 50).sum()), "n_below70": int((d.idx < 70).sum()), "n_above100": int((d.idx >= 100).sum()), "median_idx": d.idx.median(),
     "share_natural_neg": (d.natural < 0).mean() * 100, "n_natural_pos": int((d.natural >= 0).sum()), "n_migration_pos": int((d.migration >= 0).sum()),
     "corr_nat_mig": d[["natural", "migration"]].corr().iloc[0, 1], "median_old2050": d.old2050.median(), "n_old2050_over50": int((d.old2050 >= 50).sum()),
     "total_index": nat["proj2050"] / nat["pop2020"] * 100, "total_closed_index": nat["closed2050"] / nat["pop2020"] * 100}
pd.Series(s).to_csv(RES / "p1_summary.csv", header=["value"]); print(pd.Series(s).round(2))

fig, ax = plt.subplots(figsize=(9, 4)); ax.bar(range(len(dist)), dist.values, color=[ORANGE] + [BLUE] * 5 + [GREEN])
for i, v in enumerate(dist.values): ax.text(i, v + 8, f"{v}", ha="center", fontsize=9)
ax.set_xticks(range(len(dist)), dist.index); ax.set_xlabel("2050年の人口（2020年＝100）"); ax.set_ylabel("市町村の数")
ax.set_title(f"2050年に人口が半分未満になる市町村は{s['n_below50']}、増えるのは{s['n_above100']}", loc="left")
fig.text(0.01, -0.05, SOURCE + f"（{len(d):,}市町村。政令市は市全体、東京23区は区ごと、福島県浜通り地域を除く）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "p1_dist.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.5, 6))
cols = {"自然減・転出増": BLUE, "自然減・転入増": ORANGE, "自然増・転入増": GREEN, "自然増・転出増": PURPLE}
for t, g in d.groupby("type"): ax.scatter(g.natural, g.migration, s=np.clip(np.sqrt(g.pop2020) / 15, 2, 60), color=cols[t], alpha=0.5, lw=0, label=f"{t}（{len(g)}）")
ax.axhline(0, color=INK, lw=0.6); ax.axvline(0, color=INK, lw=0.6)
for code_ in d.sort_values("pop2020", ascending=False).head(8).index.tolist() + d.sort_values("migration", ascending=False).head(3).index.tolist():
    r = d.loc[code_]; ax.annotate(r.muni, (r.natural, r.migration), xytext=(3, 2), textcoords="offset points", fontsize=8)
ax.set_xlabel("出生と死亡だけの変化（%、2020→2050年）"); ax.set_ylabel("人の移動による差（%ポイント）"); ax.legend(frameon=False, fontsize=8.5, loc="lower left")
ax.set_title("ほとんどの市町村は自然減。人口を支えるのは転入", loc="left")
fig.text(0.01, -0.03, SOURCE + "（封鎖人口＝人の移動がないと仮定した推計。円の大きさは2020年の人口）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "p1_decompose.png"); plt.close(fig)
