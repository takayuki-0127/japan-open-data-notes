"""訪問介護の「近くにない」問題：事業所が0〜1か所の市区町村、最寄りの事業所までの距離、日曜対応"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from sklearn.neighbors import BallTree
from common import *

x = load(); K = len(SNAPS)
h = x[x.svc == "訪問介護"].copy()
# 市区町村の一覧：どちらかのサービスが一度でも所在した市区町村（5桁コード）
mun = x.drop_duplicates("muni")[["muni", "pref", "city", "mtype"]].set_index("muni")
cnt = h.groupby(["muni", "k"]).size().unstack(fill_value=0).reindex(mun.index, fill_value=0)
z = pd.DataFrame({"k": range(K), "snap": SNAPS, "zero": [(cnt[k] == 0).sum() for k in range(K)],
                  "one": [(cnt[k] == 1).sum() for k in range(K)], "n_muni": len(mun)})
z.to_csv(RES / "k2_zero_one.csv", index=False, encoding="utf-8-sig"); print(z)
# 0か所の市区町村の内訳（最新時点）
last = cnt[K - 1]; first = cnt[0]
trans = pd.crosstab(pd.cut(first, [-1, 0, 1, 2, 1e9], labels=["0", "1", "2", "3以上"]), pd.cut(last, [-1, 0, 1, 2, 1e9], labels=["0", "1", "2", "3以上"]))
trans.to_csv(RES / "k2_transition.csv", encoding="utf-8-sig"); print(trans)
zero_list = mun[last == 0].assign(n_2020=first[last == 0]).sort_index()
zero_list.to_csv(RES / "k2_zero_munis_2026-06.csv", encoding="utf-8-sig")
print(zero_list.mtype.value_counts())

# 最寄りの「ほかの」訪問介護事業所までの距離（各時点）
R = 6371.0
dist = []
for k in range(K):
    a = h[(h.k == k) & h.lat.between(20, 46) & h.lon.between(122, 154)]
    pts = np.radians(a[["lat", "lon"]].values)
    tree = BallTree(pts, metric="haversine")
    dd, _ = tree.query(pts, k=2)
    a = a.assign(nn_km=dd[:, 1] * R)
    dist.append(a[["id", "k", "nn_km", "mtype", "pref", "muni"]])
D = pd.concat(dist)
iso = D.groupby("k").nn_km.agg(median="median", over5=lambda s: (s > 5).mean() * 100, over10=lambda s: (s > 10).mean() * 100, n_over10=lambda s: (s > 10).sum())
iso.to_csv(RES / "k2_isolation.csv", encoding="utf-8-sig"); print(iso.round(2))

# 孤立している事業所は撤退しやすいか（k1と同じ撤退の定義）
pres = {k: set(h[h.k == k].id) for k in range(K)}
after = {k: set().union(*[pres[j] for j in range(k + 1, K)]) for k in range(K - 1)}
P = D[D.k < K - 1].copy()
P["exit"] = [int(i not in after[k]) for i, k in zip(P.id, P.k)]
P = P.merge(h[["id", "k", "csize_c", "ctype"]], on=["id", "k"])
P["dist_c"] = pd.cut(P.nn_km, [-.01, .5, 2, 5, 10, 1e9], labels=["0.5km未満", "0.5〜2km", "2〜5km", "5〜10km", "10km以上"]).astype(str)
X = pd.concat([pd.get_dummies(P.dist_c, prefix="距離", dtype=float).drop(columns="距離_0.5〜2km"),
               pd.get_dummies(P.csize_c, prefix="規模", dtype=float).drop(columns="規模_20か所以上"),
               pd.get_dummies(P.ctype, prefix="種別", dtype=float).drop(columns="種別_社会福祉法人"),
               pd.get_dummies(P.mtype, prefix="地域", dtype=float).drop(columns="地域_市"),
               pd.get_dummies(P.k, prefix="k", dtype=float).drop(columns="k_0")], axis=1)
m = sm.Logit(P.exit, sm.add_constant(X)).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(P.id)[0]})
OR = pd.DataFrame({"var": m.params.index, "or": np.exp(m.params), "lo": np.exp(m.conf_int()[0]), "hi": np.exp(m.conf_int()[1]), "p": m.pvalues}).reset_index(drop=True)
OR.to_csv(RES / "k2_isolation_exit_or.csv", index=False, encoding="utf-8-sig"); print(OR[OR["var"].str.startswith("距離")].round(3))
raw = P.groupby("dist_c").exit.agg(["mean", "size"]); raw["mean"] *= 100; print(raw.round(2)); raw.to_csv(RES / "k2_exit_by_distance.csv", encoding="utf-8-sig")

# 日曜対応：時点別、法人規模・地域別
sun_t = h.groupby("k")[["sat", "sun"]].mean() * 100; sun_t.index = SNAPS; sun_t.to_csv(RES / "k2_weekend_trend.csv", encoding="utf-8-sig"); print(sun_t.round(1))
hl = h[h.k == K - 1]
sun_g = pd.concat({"法人規模": hl.groupby("csize_c").sun.mean(), "地域": hl.groupby("mtype").sun.mean(), "法人種別": hl.groupby("ctype").sun.mean()}) * 100
sun_g.to_csv(RES / "k2_sunday_by_group.csv", encoding="utf-8-sig"); print(sun_g.round(1))

# 図1：0か所・1か所の市区町村
fig, ax = plt.subplots(figsize=(7.8, 3.7))
ax.plot(z.k, z.zero, "o-", color=ORANGE, lw=2, label="訪問介護が0か所")
ax.plot(z.k, z.one, "s-", color=BLUE, lw=2, label="1か所だけ")
for _, r in z.iterrows():
    if r.k in (0, K - 1): ax.text(r.k, r.zero + 4, f"{r.zero}", ha="center", color=ORANGE, fontsize=9); ax.text(r.k, r.one + 4, f"{r.one}", ha="center", color=BLUE, fontsize=9)
ax.set_xticks(range(K)); ax.set_xticklabels([s.replace("-", "/") if i % 2 == 0 else "" for i, s in enumerate(SNAPS)], fontsize=8.5)
ax.set_ylabel("市区町村の数"); ax.set_ylim(0, None); ax.legend(frameon=False)
ax.set_title(f"訪問介護の事業所が0か所・1か所の市区町村（対象{len(mun):,}市区町村）", loc="left", fontsize=12)
note(ax, SOURCE + "\n対象は訪問介護か通所介護の事業所が一度でも所在した市区町村（政令市は区ごと）", -0.14)
fig.savefig(FIG / "k2_zero_one.png"); plt.close(fig)

# 図2：最寄り距離の分布（最新時点）と距離別の撤退率
fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.9))
d_ = D[D.k == K - 1]
bins = np.r_[0, np.logspace(-1.3, 1.7, 40)]
for mt, col in [("特別区・政令市", BLUE), ("市", GREEN), ("町村", ORANGE)]:
    axes[0].hist(d_[d_.mtype == mt].nn_km.clip(upper=50), bins=bins, histtype="step", lw=1.8, color=col, density=True, label=f"{mt}（中央値{d_[d_.mtype == mt].nn_km.median():.2f}km）")
axes[0].set_xscale("log"); axes[0].set_xticks([0.1, 0.5, 1, 2, 5, 10, 50]); axes[0].set_xticklabels(["0.1", "0.5", "1", "2", "5", "10", "50"]); axes[0].minorticks_off()
axes[0].set_xlabel("いちばん近い別の訪問介護事業所までの直線距離（km）"); axes[0].set_ylabel("密度"); axes[0].legend(frameon=False, fontsize=8.5)
axes[0].set_title("最寄りの事業所までの距離（2026年6月末）", loc="left", fontsize=11)
order = ["0.5km未満", "0.5〜2km", "2〜5km", "5〜10km", "10km以上"]
r_ = raw.loc[order]
axes[1].bar(range(5), r_["mean"], color=[LIGHT, LIGHT, BLUE, BLUE, ORANGE])
for i, (v, n) in enumerate(zip(r_["mean"], r_["size"])): axes[1].text(i, v + .05, f"{v:.1f}%\n(n={n:,})", ha="center", fontsize=8)
axes[1].set_xticks(range(5)); axes[1].set_xticklabels(order, fontsize=8.5); axes[1].set_ylabel("半年間の撤退率（%）")
axes[1].set_title("最寄り距離別の撤退率（2020〜2026年）", loc="left", fontsize=11); axes[1].set_ylim(0, r_["mean"].max() * 1.3)
note(axes[0], SOURCE, -0.2); fig.savefig(FIG / "k2_distance.png"); plt.close(fig)

# 図3：日曜対応
fig, ax = plt.subplots(figsize=(7.8, 3.6))
grp = [("法人規模", ["1か所", "2〜4か所", "5〜19か所", "20か所以上"]), ("地域", ["特別区・政令市", "市", "町村"])]
labs, vals, cols = [], [], []
for gname, keys in grp:
    for kk in keys: labs.append(kk); vals.append(sun_g.loc[(gname, kk)]); cols.append(BLUE if gname == "法人規模" else GREEN)
ax.barh(range(len(labs))[::-1], vals, color=cols)
for i, v in enumerate(vals): ax.text(v + .5, len(labs) - 1 - i, f"{v:.0f}%", va="center", fontsize=9)
ax.set_yticks(range(len(labs))[::-1]); ax.set_yticklabels(labs); ax.set_xlabel("利用可能曜日に日曜日を含む事業所の割合（%）"); ax.set_xlim(0, 100)
ax.set_title("日曜日も来てくれる訪問介護事業所の割合（2026年6月末）", loc="left", fontsize=12)
note(ax, SOURCE + "\n青＝法人の事業所数（同じサービス・同じ時点で同じ法人名）、緑＝所在地の種類", -0.17)
fig.savefig(FIG / "k2_sunday.png"); plt.close(fig)
