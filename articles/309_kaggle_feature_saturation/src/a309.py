"""309：特徴量を足していって、どこで伸びが止まったか"""
from common import *
import numpy as np
d = load(); f = load("folds.csv")
P = dict(zip(d.version, d.private)); U = dict(zip(d.version, d.public)); C = dict(zip(d.version, d.cv))
steps = [
 ("v1→v3", "路線の集計・TE・teacher・評価×背景", C["v3"] - C["v1"], U["v3"] - U["v1"], P["v3"] - P["v1"], "甘い CV どうし"),
 ("v3→v4", "TE のキーを2つ追加（＋XGBoost）", C["v4"] - C["v3"], U["v4"] - U["v3"], P["v4"] - P["v3"], "甘い CV どうし"),
 ("v3→v5", "評価の期待値との差（補助タスク・8項目）", C["v5"] - C["v3"], None, None, "甘い CV どうし・未提出"),
 ("v11なし→v15", "特徴量3つ（全体での集計・teacher の差・件数）", 0.96106 - 0.96103, None, None, "正直な CV どうし・未提出"),
 ("v12→v18", "同じ3つを入れて全データで学び直し", None, U["v18"] - U["v12"], P["v18"] - P["v12"], "refit どうし"),
]
res = {"steps": [{"step": a, "what": b, "d_cv": None if c is None else round(c, 5), "d_public": None if u is None else round(u, 5), "d_private": None if p is None else round(p, 5), "note": n} for a, b, c, u, p, n in steps]}
summ = []
for (e, m), t in f.groupby(["experiment", "model"], sort=False):
    summ.append({"experiment": e, "model": m, "mean": round(float(t["diff"].mean()), 6), "n_up": int((t["diff"] > 0).sum()), "min": float(t["diff"].min()), "max": float(t["diff"].max()), "sd": round(float(t["diff"].std(ddof=1)), 6)})
res["fold_diffs"] = summ
xgb = [0.96093, 0.95950, 0.96140, 0.96077, 0.96062]
res["xgb_fold_auc"] = {"values": xgb, "range": round(max(xgb) - min(xgb), 5), "sd": round(float(np.std(xgb, ddof=1)), 5)}
res["threshold"] = 0.00005
res["first_step_share_public"] = round((U["v3"] - U["v1"]) / (d.public.max() - U["v1"]), 3)
res["first_step_share_private"] = round((P["v3"] - P["v1"]) / (d.private.max() - P["v1"]), 3)
res["total_gain"] = {"public": round(d.public.max() - U["v1"], 5), "private": round(d.private.max() - P["v1"], 5)}
res["teacher_auc"] = {"lightgbm": 0.95435, "catboost": 0.95486}
save_json(res, "a309_main.json")
pd.DataFrame(res["steps"]).to_csv(out("results", "a309_steps.csv"), index=False)
# 図1 版ごとの Public / Private（特徴量の版に印）
s = d.dropna(subset=["public"]).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9, 4.6), dpi=150)
x = np.arange(len(s)); ax.plot(x, s.public, "o-", color="#2980b9", label="Public"); ax.plot(x, s.private, "s-", color="#c0392b", label="Private")
for i, r in s.iterrows():
    if r.version in ("v3", "v4", "v18"): ax.axvline(i, color="#f39c12", lw=6, alpha=.25)
ax.set_xticks(x); ax.set_xticklabels(s.version.str.replace("v25s", "v25単"), rotation=60, fontsize=8)
ax.set_ylabel("AUC"); ax.set_title("提出した21回の点数（帯は特徴量を変えた版：v3・v4・v18）"); ax.grid(alpha=.3); ax.legend()
ax.ticklabel_format(axis="y", useOffset=False); fig.tight_layout(); fig.savefig(out("figures", "a309_versions.png")); plt.close(fig)
# 図2 fold ごとの差
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4), dpi=150, sharey=True)
for ax, e in zip(axes, f.experiment.unique()):
    t = f[f.experiment == e]
    for j, (m, c) in enumerate([("lgb", "#2980b9"), ("cat", "#27ae60")]):
        u = t[t.model == m]; ax.bar(u.fold + (j - .5) * .38, u["diff"] * 1e5, width=.36, color=c, label={"lgb": "LightGBM", "cat": "CatBoost"}[m])
    ax.axhline(5, color="k", ls=":", lw=1); ax.axhline(0, color="k", lw=.8); ax.set_title(e); ax.set_xlabel("fold"); ax.grid(axis="y", alpha=.3)
axes[0].set_ylabel("足した後 − 足す前（AUC の差 ×10万）"); axes[0].legend(fontsize=9)
fig.suptitle("fold ごとの差（点線は採用の基準 +0.00005）"); fig.tight_layout(); fig.savefig(out("figures", "a309_folds.png")); plt.close(fig)
# 図3 表
fm = lambda v: "—" if v is None else f"{v:+.5f}"
rows = [[a, b, fm(c), fm(u), fm(p)] for a, b, c, u, p, n in steps]
table_png(rows, ["比べた版", "足したもの", "CV の差", "Public の差", "Private の差"], out("figures", "a309_steps.png"), widths=[.13, .47, .12, .13, .13], fs=9, title="特徴量を足したときの点数の差")
print(json.dumps(res, ensure_ascii=False)[:1500])
