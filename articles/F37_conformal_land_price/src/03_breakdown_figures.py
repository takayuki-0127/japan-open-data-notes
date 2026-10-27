"""地域・用途別の当たり方と、図6枚
結果：results/coverage_by_group.csv、figures/f01〜f06"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, REGION

d = load()
P = pd.read_csv(RES / "conformal_points.csv.gz", dtype={"code": str})
meta = d[["code", "land_use_class", "pref", "lat", "lon", "dist_metro", "city", "log_pass_3km"]].copy()
meta["region"] = meta["pref"].map(REGION)
meta["area"] = np.where(meta["dist_metro"] <= 50, "三大都市圏（中心から50km以内）", "それ以外")
P = P.merge(meta, on="code")
P["land_use_class"] = P["land_use_class"].astype(str)
MAIN = "外側:block20／較正:block20"
LAB = {"外側:random／較正:random": "ランダムに分ける", "外側:block20／較正:random": "場所で分ける／較正はランダム",
       "外側:block20／較正:block20": "場所で分ける／較正も場所で"}
MLAB = {"split": "分割（幅は一定）", "norm": "正規化（幅を地点ごとに）", "cqr": "CQR（分位点回帰）"}


def cover(df, m, t):
    return ((df["y"] >= df[f"{m}_lo{t}"]) & (df["y"] <= df[f"{m}_hi{t}"]))


# --- 地域・用途別（目標90%） ---
rows = []
for s, g in P.groupby("setting"):
    for key in ("land_use_class", "region", "area"):
        for k, gg in g.groupby(key):
            if len(gg) < 100:
                continue
            for m in ("split", "norm", "cqr"):
                rows.append(dict(setting=s, group=key, value=k, method=m, n=len(gg), coverage=cover(gg, m, 90).mean(),
                                 width_ratio_median=np.median(np.exp(gg[f"{m}_hi90"] - gg[f"{m}_lo90"])),
                                 above=(gg["y"] > gg[f"{m}_hi90"]).mean(), below=(gg["y"] < gg[f"{m}_lo90"]).mean()))
G = pd.DataFrame(rows)
G.to_csv(RES / "coverage_by_group.csv", index=False, float_format="%.4f")
# 外れが多い市区町村（場所で分ける・正規化・90%）：件数20以上
mm = P[P.setting == MAIN].copy(); mm["miss"] = ~cover(mm, "norm", 90)
cityrate = mm.groupby("city").agg(n=("miss", "size"), miss=("miss", "mean"), above=("y", lambda s: 0)).query("n>=20")
cityrate["above"] = mm.groupby("city").apply(lambda g: (g["y"] > g["norm_hi90"]).mean())
cityrate.sort_values("miss", ascending=False).to_csv(RES / "_miss_by_city.csv", float_format="%.4f")
print(G[(G.setting == MAIN) & (G.method == "norm")].round(3).to_string())

C = pd.read_csv(RES / "coverage_main.csv")

# 図1：予測と区間の例（場所で分ける、20地点、正規化と分割）
ex = P[P.setting == MAIN].sample(20, random_state=7).sort_values("pred").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9, 5.2))
x = np.arange(len(ex))
ax.vlines(x - 0.15, np.exp(ex["split_lo90"]) / 1e4, np.exp(ex["split_hi90"]) / 1e4, color=LIGHT, lw=5, label="分割コンフォーマル 90%")
ax.vlines(x + 0.15, np.exp(ex["cqr_lo90"]) / 1e4, np.exp(ex["cqr_hi90"]) / 1e4, color=GREEN, lw=5, label="CQR 90%（分位点回帰）")
ins = cover(ex, "cqr", 90)
ax.scatter(x[ins], np.exp(ex["y"][ins]) / 1e4, color=INK, zorder=3, s=22, label="実際の価格（CQR の区間の中）")
ax.scatter(x[~ins], np.exp(ex["y"][~ins]) / 1e4, color=ORANGE, zorder=3, s=40, marker="D", label="実際の価格（CQR の区間の外）")
ax.set_yscale("log"); ax.set_ylabel("1㎡あたりの価格（万円、対数目盛）"); ax.set_xticks([])
ax.set_xlabel("無作為に選んだ20地点（予測の低い順）")
ax.set_title("予測区間の例：場所で分けた検証で、まだ見ていない地点に付けた90%区間")
ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "f01_interval_examples.png")

# 図2：区間に入った割合（目標90%、手法×分け方）
c9 = C[C.target == 90]
fig, ax = plt.subplots(figsize=(9, 4.8))
settings = list(LAB); methods = ["split", "norm", "cqr"]; w = 0.26
for i, m in enumerate(methods):
    v = [c9[(c9.setting == s) & (c9.method == m)]["coverage"].values[0] * 100 for s in settings]
    b = ax.bar(np.arange(3) + (i - 1) * w, v, w, color=[LIGHT, BLUE, GREEN][i], label=MLAB[m])
    for xx, vv in zip(np.arange(3) + (i - 1) * w, v):
        ax.text(xx, vv + 0.4, f"{vv:.1f}", ha="center", fontsize=9)
ax.axhline(90, color=ORANGE, ls="--", lw=1.2); ax.set_xlim(-0.5, 2.62); ax.text(2.6, 90.3, "目標 90%", color=ORANGE, fontsize=9, ha="right")
ax.set_xticks(np.arange(3)); ax.set_xticklabels([LAB[s].replace("／", "\n") for s in settings])
ax.set_ylim(75, 96); ax.set_ylabel("区間に入った割合（%）")
ax.set_title("90%区間に、本当に9割入ったか（検証用の地点、2万5千地点）")
ax.legend(frameon=False, fontsize=9, loc="lower left")
save(fig, "f02_coverage_by_split.png")

# 図3：区間の幅（上限÷下限）の分布（場所で分ける）
mm = P[P.setting == MAIN]
fig, ax = plt.subplots(figsize=(9, 4.6))
bins = np.linspace(1, 8, 71)
for m, col in zip(methods, [GRAY, BLUE, GREEN]):
    r = np.exp(mm[f"{m}_hi90"] - mm[f"{m}_lo90"])
    ax.hist(r.clip(upper=7.95), bins=bins, histtype="step", lw=2, color=col, label=f"{MLAB[m]}（中央値 {np.median(r):.2f}倍）")
ax.set_xlabel("90%区間の幅（上限 ÷ 下限、倍。8倍以上は右端にまとめた）"); ax.set_ylabel("地点の数")
ax.set_title("区間の幅（場所で分けた検証）：分割は検証の回ごとに全地点で同じ幅")
ax.legend(frameon=False, fontsize=9)
save(fig, "f03_width_distribution.png")

# 図4：外れた地点の地図（場所で分ける・正規化90%）
fig, ax = plt.subplots(figsize=(7.5, 7.5))
ok = cover(mm, "split", 90)
ax.scatter(mm["lon"][ok], mm["lat"][ok], s=1, color="#d9d8d3", label="区間の中")
up = mm["y"] > mm["split_hi90"]; lo = mm["y"] < mm["split_lo90"]
ax.scatter(mm["lon"][up], mm["lat"][up], s=3, color=ORANGE, label=f"上に外れた（{up.mean()*100:.1f}%）")
ax.scatter(mm["lon"][lo], mm["lat"][lo], s=3, color=BLUE, label=f"下に外れた（{lo.mean()*100:.1f}%）")
ax.set_aspect(1.25); ax.axis("off")
ax.set_title("90%区間から外れた地点（場所で分けた検証・分割コンフォーマル）")
ax.legend(frameon=False, fontsize=9, loc="lower right", markerscale=4)
save(fig, "f04_miss_map.png")

# 図5：目標を変えたとき（分割・正規化）
fig, ax = plt.subplots(figsize=(7.5, 5))
for s, col, mk in zip(settings, [GRAY, ORANGE, BLUE], ["o", "s", "D"]):
    for m, ls in (("split", ":"), ("norm", "-")):
        c = C[(C.setting == s) & (C.method == m)].sort_values("target")
        ax.plot(c["target"], c["coverage"] * 100, ls=ls, marker=mk, color=col, label=f"{LAB[s]}・{MLAB[m][:2]}")
ax.plot([78, 97], [78, 97], color=INK, lw=0.8)
ax.set_xlabel("目標（%）"); ax.set_ylabel("実際に入った割合（%）"); ax.set_xticks([80, 90, 95])
ax.set_title("目標を80・90・95%に変えたときの当たり方（線上なら目標どおり）")
ax.legend(frameon=False, fontsize=8)
save(fig, "f05_target_levels.png")
print("figs done")
