"""W2：国籍・地域ごとの季節パターン（STL の季節成分 → k-means でグループ分け）"""
from common import *
from statsmodels.tsa.seasonal import STL
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

port, nat = load()
x = nat[~nat.nat.isin(REGIONS)].copy()
x["date"] = pd.to_datetime(dict(year=x.year, month=x.month, day=1))
w = x.pivot_table(index="date", columns="nat", values="n").fillna(0)
NTOP = 20
top = w.loc["2025"].sum().sort_values(ascending=False).head(NTOP).index.tolist()
MON = list(range(1, 13))


def profile(s):
    """対数の系列を STL で分け、季節成分を月ごとに平均（% のずれに直す）"""
    r = STL(np.log(s), period=12, robust=True).fit()
    seas = pd.Series(r.seasonal.values, index=s.index).groupby(s.index.month).mean()
    seas -= seas.mean()
    return (np.exp(seas) - 1) * 100


pre = pd.DataFrame({k: profile(w.loc["2013":"2019", k]) for k in top}).T[MON]
post = pd.DataFrame({k: profile(w.loc["2023":"2026-07", k]) for k in top}).T[MON]

# k-means：形（ベクトルの長さ1にそろえる）でまとめる
Z = np.log1p(pre.values / 100); Z = Z / np.linalg.norm(Z, axis=1, keepdims=True)
sil = {}
for k in range(2, 7):
    km = KMeans(k, n_init=100, random_state=0).fit(Z); sil[k] = silhouette_score(Z, km.labels_)
K = 4
km = KMeans(K, n_init=100, random_state=0).fit(Z)
lab = pd.Series(km.labels_, index=top)
# グループに名前をつける（いちばん多い月で順番を決める）
peak = pre.groupby(lab).mean().idxmax(axis=1).sort_values()
ren = {g: i + 1 for i, g in enumerate(peak.index)}
lab = lab.map(ren)
# 2023年以降の形がどのグループの平均に近いか
cent = pre.groupby(lab).mean()
Zc = np.log1p(cent.values / 100); Zc = Zc / np.linalg.norm(Zc, axis=1, keepdims=True)
Zp = np.log1p(post.values / 100); Zp = Zp / np.linalg.norm(Zp, axis=1, keepdims=True)
post_lab = pd.Series(cent.index[np.argmax(Zp @ Zc.T, axis=1)], index=top)

res = pd.DataFrame({"group": lab, "group_2023_26": post_lab,
                    "peak_month": pre.idxmax(1), "low_month": pre.idxmin(1),
                    "amplitude_pt": (pre.max(1) - pre.min(1)).round(1),
                    "corr_pre_post": [round(np.corrcoef(pre.loc[k], post.loc[k])[0, 1], 2) for k in top],
                    "entries_2025": w.loc["2025", top].sum().astype(int)})
res = res.sort_values(["group", "entries_2025"], ascending=[True, False])
res.to_csv(RES / "w2_groups.csv", encoding="utf-8-sig")
pre.round(1).to_csv(RES / "w2_profile_2013_19.csv", encoding="utf-8-sig")
post.round(1).to_csv(RES / "w2_profile_2023_26.csv", encoding="utf-8-sig")
pd.Series(sil).round(3).rename("silhouette").to_csv(RES / "w2_silhouette.csv", encoding="utf-8-sig")
print("silhouette", {k: round(v, 3) for k, v in sil.items()})
print(res.to_string())
print(cent.round(0).to_string())
print(pre.loc[res.index].round(0).astype(int).to_string())

# 図1：ヒートマップ
fig, ax = plt.subplots(figsize=(9, 7))
P = pre.loc[res.index]
vmax = 60
im = ax.imshow(P.clip(-vmax, vmax).values, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
ax.set_xticks(range(12)); ax.set_xticklabels([f"{m}月" for m in MON])
ax.set_yticks(range(len(P))); ax.set_yticklabels([f"{k}（G{res.loc[k,'group']}）" for k in P.index], fontsize=9)
for i in range(len(P)):
    for j in range(12):
        v = P.values[i, j]
        ax.text(j, i, f"{v:+.0f}", ha="center", va="center", fontsize=6.5, color="white" if abs(v) > 35 else INK)
for b in np.where(np.diff(res.group.values) != 0)[0]:
    ax.axhline(b + 0.5, color=INK, lw=1.2)
cb = fig.colorbar(im, ax=ax, shrink=0.6); cb.set_label("その国の年平均からのずれ（%）")
ax.set_title("国籍・地域別の季節パターン（2013〜2019年、STLの季節成分）", loc="left", fontsize=12)
note(ax, SOURCE + "。2025年の入国者数の上位20か国・地域", y=-0.06)
fig.savefig(FIG / "w2_heatmap.png"); plt.close(fig)

# 図2：グループごとの形
fig, axs = plt.subplots(1, K, figsize=(11, 4), sharey=True)
gcol = [BLUE, ORANGE, GREEN, PURPLE, RED, GRAY]
for g, ax in zip(cent.index, axs):
    mem = res.index[res.group == g]
    for k in mem: ax.plot(MON, pre.loc[k], color=gcol[g - 1], alpha=0.25, lw=1)
    ax.plot(MON, cent.loc[g], color=gcol[g - 1], lw=2.5)
    ax.axhline(0, color=GRAY, lw=0.8); ax.set_xticks([1, 4, 7, 10, 12])
    ax.set_title(f"G{g}（{len(mem)}か国・地域）", loc="left", fontsize=11)
    names = list(mem); txt = "\n".join("・".join(names[i:i + 3]) for i in range(0, len(names), 3))
    ax.text(0.02, -0.17, txt, transform=ax.transAxes, fontsize=8, va="top")
    ax.set_xlabel("月", fontsize=9)
axs[0].set_ylabel("年平均からのずれ（%）")
fig.suptitle("k-meansで4つに分けた季節の形（2013〜2019年）", x=0.06, ha="left", fontsize=13)
fig.text(0.06, -0.2, SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "w2_clusters.png"); plt.close(fig)

# 図3：コロナ前と2023年以降
SEL = ["台湾", "韓国", "中国", "米国", "タイ", "オーストラリア"]
fig, axs = plt.subplots(2, 3, figsize=(10, 6), sharex=True)
for k, ax in zip(SEL, axs.flat):
    ax.plot(MON, pre.loc[k], color=GRAY, lw=2, label="2013〜19年")
    ax.plot(MON, post.loc[k], color=BLUE, lw=2, label="2023〜26年")
    ax.axhline(0, color=GRAY, lw=0.6)
    ax.set_title(f"{k}（相関 {res.loc[k,'corr_pre_post']:.2f}）", loc="left", fontsize=11)
    ax.set_xticks([1, 3, 5, 7, 9, 11])
axs[0, 0].legend(frameon=False, fontsize=8)
fig.supylabel("年平均からのずれ（%）", fontsize=10)
fig.suptitle("季節の形はコロナの後も同じか", x=0.06, ha="left", fontsize=13)
fig.text(0.06, -0.02, SOURCE + "。2023〜26年は2023年1月〜2026年7月", fontsize=7.5, color=GRAY)
fig.tight_layout()
fig.savefig(FIG / "w2_prepost.png"); plt.close(fig)
