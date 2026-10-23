"""P2：排出はどこに集中しているか（上位1%・10%の事業所のシェア、ジニ係数）、排出から移動（廃棄物・下水道）へのシフト、都道府県別"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

F, S = load()
CONST = set(pd.read_csv(RES / "p1_constant_substances.csv")["sub"])
S = S[S["sub"].isin(CONST)].merge(F[["fy", "rid", "pref", "ind"]], on=["fy", "rid"], how="left")
fac = S.groupby(["fy", "rid"]).agg(release=("release", "sum"), transfer=("transfer", "sum")).reset_index()


def gini(x):
    x = np.sort(np.asarray(x)); n = len(x)
    return (2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum())


rows = []
for fy, g in fac.groupby("fy"):
    r = np.sort(g.release.values)[::-1]; n = len(r); T = r.sum()
    rows.append({"fy": fy, "n": n, "top1": r[:max(1, n // 100)].sum() / T * 100, "top10": r[:n // 10].sum() / T * 100,
                 "top100": r[:100].sum() / T * 100, "gini": gini(r), "zero_share": (r == 0).mean() * 100,
                 "release": T / 1e6, "transfer": g.transfer.sum() / 1e6, "sewer": S[S.fy == fy].sewer.sum() / 1e6, "offsite": S[S.fy == fy].offsite.sum() / 1e6})
C = pd.DataFrame(rows); C["release_share"] = C.release / (C.release + C.transfer) * 100
C.to_csv(RES / "p2_concentration.csv", index=False, encoding="utf-8-sig"); print(C.round(2).to_string())

# 都道府県（所在地）：2003→2024
P = S.groupby(["pref", "fy"]).release.sum().unstack() / 1e3
Pd = pd.DataFrame({"2003": P[2003], "2024": P[2024]}); Pd["chg"] = (Pd["2024"] / Pd["2003"] - 1) * 100
Pd = Pd.sort_values("2024", ascending=False); Pd.to_csv(RES / "p2_prefecture.csv", encoding="utf-8-sig"); print(Pd.round(0).head(10)); print(Pd.chg.describe().round(1))
# 2024年度の業種別シェア
I = S[S.fy == 2024].groupby("ind").release.sum().sort_values(ascending=False) / 1e3
(I / I.sum() * 100).head(10).to_csv(RES / "p2_industry_share_2024.csv", encoding="utf-8-sig"); print((I / I.sum() * 100).head(6).round(1))

# 図1：ローレンツ曲線
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for fy, col in [(2003, LIGHT), (2013, GRAY), (2024, BLUE)]:
    r = np.sort(fac[fac.fy == fy].release.values)[::-1]; cum = np.cumsum(r) / r.sum()
    axes[0].plot(np.arange(1, len(r) + 1) / len(r) * 100, cum * 100, color=col, lw=2, label=f"{fy}年度（ジニ係数{gini(r):.3f}）")
axes[0].set_xscale("log"); axes[0].set_xticks([0.1, 1, 10, 100]); axes[0].set_xticklabels(["0.1", "1", "10", "100"]); axes[0].minorticks_off()
axes[0].set_xlabel("排出量が多い順の事業所の割合（%、対数目盛）"); axes[0].set_ylabel("全体の排出量に占める割合（%）"); axes[0].legend(frameon=False, fontsize=9)
axes[0].set_title("上位の事業所に集中する排出", loc="left", fontsize=11.5)
axes[1].plot(C.fy, C.top1, "o-", color=BLUE, ms=3.5, lw=2, label="上位1%の事業所")
axes[1].plot(C.fy, C.top10, "o-", color=ORANGE, ms=3.5, lw=2, label="上位10%の事業所")
axes[1].set_ylim(0, 100); axes[1].set_ylabel("排出量のシェア（%）"); axes[1].set_xlabel("年度"); axes[1].legend(frameon=False, fontsize=9)
axes[1].set_title("上位の事業所のシェアの推移", loc="left", fontsize=11.5)
note(axes[0], SOURCE + "\n24年続けて対象の物質に限る", -0.2); fig.savefig(FIG / "p2_lorenz.png"); plt.close(fig)

# 図2：排出と移動
fig, ax = plt.subplots(figsize=(8.4, 4))
ax.plot(C.fy, C.release, "o-", color=BLUE, lw=2, ms=3.5, label="排出量（大気・水域・土壌・埋立）")
ax.plot(C.fy, C.offsite, "o-", color=ORANGE, lw=2, ms=3.5, label="移動量：事業所の外へ（主に廃棄物）")
ax.plot(C.fy, C.sewer, "o-", color=GREEN, lw=2, ms=3.5, label="移動量：下水道へ")
ax.set_ylim(0, None); ax.set_ylabel("千トン／年"); ax.set_xlabel("年度"); ax.legend(frameon=False, fontsize=9)
ax.set_title("排出は減り、事業所の外への移動が上回るようになった", loc="left", fontsize=12)
note(ax, SOURCE + "\n24年続けて対象の物質に限る", -0.14); fig.savefig(FIG / "p2_release_transfer.png"); plt.close(fig)

# 図3：都道府県
fig, axes = plt.subplots(1, 2, figsize=(10.4, 7.4), sharey=True)
o = Pd.sort_values("2024")
axes[0].barh(range(len(o)), o["2024"] / 1e3, color=BLUE); axes[0].set_xlabel("2024年度の排出量（千トン）")
axes[0].set_yticks(range(len(o))); axes[0].set_yticklabels(o.index, fontsize=7.5)
cols = [ORANGE if v > -50 else GRAY for v in o.chg]
axes[1].barh(range(len(o)), o.chg, color=cols); axes[1].axvline(0, color=INK, lw=.6); axes[1].axvline(-64, color=INK, ls=":", lw=.8)
axes[1].set_xlabel("2003→2024年度の増減（%）")
axes[0].set_title("都道府県別の排出量（所在地）", loc="left", fontsize=11.5); axes[1].set_title("減り方（橙＝減少が50%未満）", loc="left", fontsize=11.5)
note(axes[0], SOURCE + "\n24年続けて対象の物質に限る。点線は全国の減少率", -0.1); fig.savefig(FIG / "p2_prefecture.png"); plt.close(fig)
