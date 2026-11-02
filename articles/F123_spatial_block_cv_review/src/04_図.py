"""F123 04 図と集計：これまでの記事の「ランダム vs 場所」の横並び（図1）と、3つのデータでの新しい交差検証（図2〜5）"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, save, BLUE, ORANGE, GRAY, INK, GREEN, PURPLE

# ---- 図1：これまでの記事の数字（各記事の README から転記）
PRIOR = [  # 記事, 対象, 指標, 小さいほど良いか, ランダム, 場所, 場所の分け方
    ("F03", "地価・LightGBM", "外れの中央値（%）", True, 13.7, 18.7, "20km四方"),
    ("F03", "地価・LightGBM", "外れの中央値（%）", True, 13.7, 25.0, "都道府県"),
    ("F03", "地価・線形回帰", "外れの中央値（%）", True, 29.5, 30.0, "20km四方"),
    ("F75", "首都圏の地価・地図だけのGP", "外れの中央値（%）", True, 14.7, 27.6, "20km四方"),
    ("F75", "首都圏の地価・特徴量の線形回帰", "外れの中央値（%）", True, 24.5, 26.5, "20km四方"),
    ("F74", "気温・距離だけ（IDW）", "RMSE（℃）", True, 1.23, 1.50, "100km四方"),
    ("F74", "気温・回帰クリギング", "RMSE（℃）", True, 0.54, 0.58, "100km四方"),
    ("F74", "気温・LightGBM", "RMSE（℃）", True, 0.74, 0.89, "予報区"),
    ("F107", "出生率・線形回帰", "R²", False, 0.376, 0.318, "都道府県"),
    ("F107", "出生率・LightGBM", "R²", False, 0.497, 0.321, "都道府県"),
    ("F107", "出生率・GraphSAGE型", "R²", False, 0.674, 0.438, "都道府県"),
    ("F107", "出生率・LightGBM＋隣の出生率", "R²", False, 0.738, 0.077, "都道府県"),
]
pr = pd.DataFrame(PRIOR, columns=["記事", "対象", "指標", "小さいほど良い", "ランダム", "場所", "分け方"])
# 悪化の度合い：誤差は「何倍になったか−1」、R² は「説明できた割合が何%減ったか」
pr["悪化（%）"] = np.where(pr["小さいほど良い"], (pr["場所"] / pr["ランダム"] - 1) * 100, (1 - pr["場所"] / pr["ランダム"]) * 100)
pr.to_csv(RES / "prior_articles.csv", index=False)
fig, ax = plt.subplots(figsize=(8.6, 5.4))
p2 = pr.iloc[::-1].reset_index(drop=True)
cols = {"F03": BLUE, "F75": GREEN, "F74": PURPLE, "F107": ORANGE}
ax.barh(range(len(p2)), p2["悪化（%）"], color=[cols[a] for a in p2["記事"]])
for i, r in p2.iterrows():
    u = "%" if "%" in r["指標"] else ("℃" if "℃" in r["指標"] else "")
    fmt = (lambda v: f"{v:.2f}") if u == "" or u == "℃" else (lambda v: f"{v:.1f}")
    ax.text(r["悪化（%）"] + 1.5, i, f"{fmt(r['ランダム'])}→{fmt(r['場所'])}{u if u!='%' else '%'}（{r['分け方']}）", va="center", fontsize=8.5, color=INK)
ax.set_yticks(range(len(p2))); ax.set_yticklabels([f"{a} {b}" for a, b in zip(p2["記事"], p2["対象"])], fontsize=9)
ax.set_xlabel("ランダムに分けた検証と比べた悪化（%）　誤差は増えた割合、R² は減った割合")
ax.set_xlim(0, 135)
ax.set_title("これまでの記事：場所で分けて確かめると、どれだけ悪くなったか")
save(fig, "fig1_prior_articles.png")

# ---- 新しい交差検証の結果
cv = pd.concat([pd.read_csv(RES / f"cv_{n}.csv") for n in ["地価", "出生率", "気温"]])
# 気温の「LightGBM（特徴量だけ）」は標高しか使えず位置の情報がない（R²<0）ので、図からは外す（表には残す）
SKIP = {("気温", "LightGBM（特徴量だけ）")}
cv.to_csv(RES / "cv_all.csv", index=False)
ERR = {"地価": "med_ape", "出生率": "rmse", "気温": "rmse"}
LAB = {"地価": "外れの中央値（%）", "出生率": "RMSE（合計特殊出生率）", "気温": "RMSE（℃）"}
MOD = ["LightGBM（特徴量＋座標）", "LightGBM（特徴量だけ）", "線形回帰", "近くの地点の平均（座標だけ）"]
MC = dict(zip(MOD, [BLUE, GREEN, PURPLE, ORANGE]))
base = cv[(cv.buffer_km == 0)]
agg = base.groupby(["dataset", "model", "scheme", "size_km"], dropna=False).agg(
    err_mean=("rmse", "mean"), r2=("r2", "mean"), nn=("nn_km_median", "mean"),
    medape=("med_ape", "mean"), err_sd=("rmse", "std")).reset_index()
agg["err"] = np.where(agg.dataset == "地価", agg.medape * 100, agg.err_mean)
agg.to_csv(RES / "cv_summary.csv", index=False)

# 図2：ブロックの大きさと誤差（モデルごと）
fig, axs = plt.subplots(1, 3, figsize=(12, 4.2))
for ax, n in zip(axs, ["地価", "出生率", "気温"]):
    a = agg[agg.dataset == n]
    for m in MOD:
        if (n, m) in SKIP: continue
        r0 = a[(a.model == m) & (a.scheme == "random")]["err"].values[0]
        b = a[(a.model == m) & (a.scheme == "block")].sort_values("size_km")
        xs = [0] + list(b["size_km"]); ys = [r0] + list(b["err"])
        ax.plot(range(len(xs)), ys, "-o", color=MC[m], label=m, ms=4)
        pf = a[(a.model == m) & (a.scheme == "pref")]["err"]
        if len(pf): ax.plot(len(xs), pf.values[0], "s", color=MC[m], ms=6)
    ax.set_xticks(range(len(xs) + 1)); ax.set_xticklabels(["ランダム"] + [f"{int(s)}km" for s in b["size_km"]] + ["都道府県" if n != "気温" else "予報区"], rotation=40, fontsize=8.5)
    ax.set_title(n); ax.set_ylabel(LAB[n])
axs[0].legend(fontsize=7.5, frameon=False, loc="upper left")
fig.suptitle("ブロックを大きくするほど、誤差はどう増えるか（5分割×3回の平均）", y=1.02)
save(fig, "fig2_block_size.png")

# 図3：テストの地点から一番近い学習地点までの距離（中央値）と誤差の増え方
fig, axs = plt.subplots(1, 3, figsize=(12, 4.0))
for ax, n in zip(axs, ["地価", "出生率", "気温"]):
    a = agg[(agg.dataset == n)]
    for m in MOD:
        if (n, m) in SKIP: continue
        aa = a[(a.model == m) & (a.scheme != "pref")].copy()   # ランダムとブロック（大きさ順）だけ
        r0 = aa[aa.scheme == "random"]["err"].values[0]
        aa["ratio"] = aa["err"] / r0
        aa = aa.sort_values("size_km", na_position="first")
        ax.plot(aa["nn"], aa["ratio"], "-o", color=MC[m], ms=4, label=m)
    ax.axhline(1, color=GRAY, lw=0.8); ax.set_xscale("log")
    ax.set_title(n); ax.set_xlabel("一番近い学習地点までの距離（中央値, km）"); ax.set_ylabel("ランダムのときの何倍の誤差か")
axs[0].legend(fontsize=7.5, frameon=False)
fig.suptitle("ブロックを大きくして近くの学習地点が遠ざかるほど、誤差は増える（ランダム＝1）", y=1.02)
save(fig, "fig3_distance.png")

# 図4：モデルの順位はランダムと場所で入れ替わるか
fig, axs = plt.subplots(1, 3, figsize=(12, 4.0))
SZ = {"地価": 20, "出生率": 50, "気温": 100}
rank_rows = []
for ax, n in zip(axs, ["地価", "出生率", "気温"]):
    a = agg[agg.dataset == n]
    v1 = a[a.scheme == "random"].set_index("model")["err"]
    v2 = a[(a.scheme == "block") & (a.size_km == SZ[n])].set_index("model")["err"]
    v3 = a[a.scheme == "pref"].set_index("model")["err"]
    for m in MOD:
        if (n, m) in SKIP: continue
        ax.plot([0, 1, 2], [v1[m], v2[m], v3[m]], "-o", color=MC[m], label=m)
        rank_rows.append(dict(dataset=n, model=m, random=v1[m], block=v2[m], pref=v3[m],
                              rank_random=int(v1.rank()[m]), rank_block=int(v2.rank()[m]), rank_pref=int(v3.rank()[m])))
    ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["ランダム", f"{SZ[n]}km四方", "都道府県" if n != "気温" else "予報区"])
    ax.set_title(n); ax.set_ylabel(LAB[n])
axs[0].legend(fontsize=7.5, frameon=False)
fig.suptitle("どのモデルが一番か：分け方で答えは変わるか", y=1.02)
save(fig, "fig4_ranking.png")
pd.DataFrame(rank_rows).to_csv(RES / "ranking.csv", index=False)

# 図5：緩衝帯（テストの周りの学習地点を外す）
buf = cv[(cv.scheme == "block") & (cv.seed == cv.seed.min())]
fig, axs = plt.subplots(1, 3, figsize=(12, 4.0))
brow = []
for ax, n in zip(axs, ["地価", "出生率", "気温"]):
    b = buf[(buf.dataset == n) & (buf.size_km == SZ[n])]
    for m in MOD:
        if (n, m) in SKIP: continue
        bb = b[b.model == m].sort_values("buffer_km")
        e = bb.med_ape * 100 if n == "地価" else bb.rmse
        ax.plot(bb["buffer_km"], e, "-o", color=MC[m], label=m)
        for bk, ee in zip(bb["buffer_km"], e): brow.append(dict(dataset=n, model=m, buffer_km=bk, err=ee))
    ax.set_title(f"{n}（{SZ[n]}km四方＋緩衝帯）"); ax.set_xlabel("テストの周りで学習から外した距離（km）"); ax.set_ylabel(LAB[n])
axs[0].legend(fontsize=7.5, frameon=False)
fig.suptitle("ブロックの境目の近さを消すと、誤差はさらに増えるか", y=1.02)
save(fig, "fig5_buffer.png")
pd.DataFrame(brow).to_csv(RES / "buffer.csv", index=False)

# 乱数の種でのばらつき
sd = base[base.scheme.isin(["random", "block"])].groupby(["dataset", "model", "scheme", "size_km"], dropna=False)["rmse"].agg(["mean", "std"]).reset_index()
sd.to_csv(RES / "seed_sd.csv", index=False)
print(agg.to_string())
print(pd.DataFrame(rank_rows).to_string())
print(pd.DataFrame(brow).to_string())
print(sd.groupby("dataset")["std"].max())
