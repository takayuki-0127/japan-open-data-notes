"""04 図：figures/*.png"""
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from common import DATA, RES, FIG

FIG.mkdir(exist_ok=True)
R = json.load(open(RES / "results.json"))
C = {"TRUE": "#202124", "A": "#1a73e8", "B": "#9aa0a6", "C": "#d93025", "D1": "#e37400", "D2": "#c58af9", "D3": "#188038"}

# ---------------------------------------------------------------- 図1 F94：「小さい町ほど減る」傾き、本当の値と扱い方
m = pd.read_csv(RES / "f94_methods_2000_2025.csv").set_index("key")
keys = ["TRUE", "A", "B", "C", "D1", "D3"]
lab = {"TRUE": "本当の値\n（旧市町村）", "A": "A 再集計", "B": "B 変化なし\nだけ", "C": "C コード\n突合", "D1": "D1 按分\n（人口比）", "D3": "D3 按分\n（伸び延長）"}
fig, ax = plt.subplots(figsize=(8.2, 4.6))
x = np.arange(len(keys))
v = m.loc[keys, "slope"].values
ax.bar(x, v, color=[C[k] for k in keys], alpha=0.85)
ax.errorbar(x, v, yerr=[v - m.loc[keys, "slope_lo"], m.loc[keys, "slope_hi"] - v], fmt="none", ecolor="black", capsize=4)
p20 = R["f94_2020_published"]
for i, k in enumerate(keys):
    ax.text(i, m.loc[k, "slope_hi"] + 0.5, f"{v[i]:.1f}", ha="center", fontsize=10)
    if k in p20:
        ax.plot(i, p20[k]["slope"], marker="D", color="white", markeredgecolor="black", ms=7, zorder=5)
ax.plot([], [], marker="D", color="white", markeredgecolor="black", ls="none", label="F94 の値（2000→2020年）")
ax.set_xticks(x); ax.set_xticklabels([lab[k] for k in keys], fontsize=9)
ax.set_ylabel("人口10倍あたりの増減率の差（%ポイント）")
ax.set_title("2000→2025年「小さい町ほど減る」の傾き：本当の値は、どの扱い方よりも急だった", fontsize=11)
ax.legend(loc="upper right", fontsize=9); ax.set_ylim(0, 30)
fig.tight_layout(); fig.savefig(FIG / "fig1_f94_slope_truth.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- 図2 F94：按分した増減率と本当の増減率（合併した旧市町村）
old = pd.read_csv(DATA / "old_units_2025.csv", dtype={"code": str})
cw = pd.read_csv(DATA / "f94_crosswalk_2000_2020.csv", dtype={"code2000": str, "code2020": str})
o = old.merge(cw[["code2000", "code2020", "merged"]], left_on="code", right_on="code2000")
o = o[(o.pop2000 > 0) & o.merged].copy()
p25 = old.merge(cw[["code2000", "code2020"]], left_on="code", right_on="code2000").groupby("code2020").pop2025.sum()
o["true"] = (o.pop2025 / o.pop2000 - 1) * 100
w1 = o.pop2000 / o.groupby("code2020").pop2000.transform("sum")
g = (o.pop2000 / o.pop1995).clip(0.5, 2.0).fillna(1.0); w3 = o.pop2000 * g ** 5; w3 = w3 / w3.groupby(o.code2020).transform("sum")
o["D1"] = (w1 * p25.reindex(o.code2020).values / o.pop2000 - 1) * 100
o["D3"] = (w3 * p25.reindex(o.code2020).values / o.pop2000 - 1) * 100
acc = pd.read_csv(RES / "f94_alloc_accuracy.csv").set_index("key")
fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.6), sharex=True, sharey=True)
for ax, k, t in [(axes[0], "D1", "D1 2000年人口の比で割り戻す"), (axes[1], "D3", "D3 1995→2000年の伸びを延ばして割り戻す")]:
    ax.scatter(o.true, o[k], s=6, alpha=0.35, color=C[k])
    ax.plot([-80, 80], [-80, 80], color="black", lw=0.8)
    ax.set_xlim(-75, 60); ax.set_ylim(-75, 60)
    ax.set_title(f"{t}\n平均の外れ {acc.loc[k, 'mae']:.1f}%pt・偏り {acc.loc[k, 'bias']:+.1f}%pt", fontsize=10)
    ax.set_xlabel("本当の増減率（2000→2025年、%）")
axes[0].set_ylabel("割り戻した増減率（%）")
fig.suptitle(f"合併に関わった旧市町村 {len(o):,}：割り戻しは、周辺の町の減り方を小さく見せていた", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig2_f94_alloc_vs_truth.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- 図3 F94：人口規模ごとの増減率（合併の中心／周辺／合併なし）
t = old.merge(cw[["code2000", "code2020", "merged"]], left_on="code", right_on="code2000")
t = t[t.pop2000 > 0].copy()
t["rate"] = (t.pop2025 / t.pop2000 - 1) * 100
t["core"] = t.pop2000 == t.groupby("code2020").pop2000.transform("max")
t["grp"] = np.where(~t.merged, "合併なし", np.where(t.core, "合併の中心（最大の旧市町村）", "合併の周辺"))
bins = [0, 3000, 10000, 30000, 100000, 1e8]; bl = ["3千人未満", "3千〜1万", "1万〜3万", "3万〜10万", "10万人以上"]
t["size"] = pd.cut(t.pop2000, bins, labels=bl)
med = t.groupby(["size", "grp"], observed=True).rate.median().unstack()
cnt = t.groupby(["size", "grp"], observed=True).size().unstack()
fig, ax = plt.subplots(figsize=(8.4, 4.6))
cols = {"合併なし": "#5f6368", "合併の中心（最大の旧市町村）": "#1a73e8", "合併の周辺": "#e37400"}
xx = np.arange(len(bl)); wd = 0.26
for i, gname in enumerate(cols):
    vals = med[gname].reindex(bl).values
    ax.bar(xx + (i - 1) * wd, vals, wd, color=cols[gname], label=gname)
    for j, vv in enumerate(vals):
        n = cnt[gname].reindex(bl).values[j]
        if not np.isnan(vv) and n >= 5:
            ax.text(xx[j] + (i - 1) * wd, vv - 1.5, f"{vv:.0f}", ha="center", va="top", fontsize=8)
ax.axhline(0, color="black", lw=0.8)
ax.set_xticks(xx); ax.set_xticklabels([f"{b}" for b in bl])
ax.set_xlabel("2000年の人口"); ax.set_ylabel("増減率の中央値（2000→2025年、%）")
ax.set_title("1万人未満の町では、合併して「周辺」になった町のほうが、合併しなかった町より減っていた", fontsize=11)
ax.legend(fontsize=9, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "fig3_f94_core_periphery.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- 図4 F14：計画を作った市町村と似た未作成の差（DID の人口密度の変化）
ev = pd.read_csv(RES / "f14_event_psm_2025.csv")
fig, ax = plt.subplots(figsize=(8.2, 4.4))
labels = ev["期間"].str.replace("（", "\n（", regex=False)
cols = ["#9aa0a6", "#9aa0a6", "#e37400", "#e37400", "#b06000"]
for i, r in ev.iterrows():
    ax.errorbar(i, r["マッチング後の差"], yerr=[[r["マッチング後の差"] - r["95%下"]], [r["95%上"] - r["マッチング後の差"]]],
                fmt="o", color=cols[i], capsize=5, ms=8)
    ax.text(i + 0.08, r["マッチング後の差"], f"{r['マッチング後の差']:+.2f}", fontsize=9, va="center")
ax.axhline(0, color="black", lw=0.8)
ax.axvline(1.5, color="gray", ls=":", lw=1)
ax.set_xticks(range(len(ev))); ax.set_xticklabels(labels, fontsize=8.5)
ax.set_ylabel("作成 − 似た未作成（%ポイント）")
ax.set_title("コンパクトシティの計画：2025年を足しても、中心部の人口密度の差は0をまたいだ", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig4_f14_event.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- 図5 F87：2020→2025年の未婚割合の変化、不詳の扱いで向きが変わる
c = pd.read_csv(RES / "f87_compare_2020_2025.csv")
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), sharey=True)
for ax, sex in zip(axes, ["女", "男"]):
    s = c[c.sex == sex]; xx = np.arange(len(s))
    ax.bar(xx - 0.2, s.chg_excl_unknown, 0.4, color="#9aa0a6", label="原数値（不詳を分母から除く）")
    ax.bar(xx + 0.2, s.chg_hokan, 0.4, color="#1a73e8", label="不詳補完値どうし")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(xx); ax.set_xticklabels([a.replace("-", "〜") for a in s.age], rotation=45, fontsize=8.5)
    ax.set_title(f"{sex}性", fontsize=11); ax.set_xlabel("年齢")
axes[0].set_ylabel("未婚割合の変化（2020→2025年、%ポイント）")
axes[0].legend(fontsize=8.5, loc="upper left")
fig.suptitle("未婚割合は2025年に「増えなくなった」のか：不詳の扱いで答えが逆になる", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig5_f87_unmarried_change.png", dpi=150); plt.close(fig)
print("ok")
