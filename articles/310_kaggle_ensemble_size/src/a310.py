"""310：アンサンブルは、何本混ぜると効かなくなるか"""
from common import *
import numpy as np
d = load(); b = load("blend.csv"); c = load("corr.csv")
P = dict(zip(d.version, d.private)); U = dict(zip(d.version, d.public))
cv = dict(zip(b.step.astype(str), b.cv))
single = {"cat": 0.96094, "lgb": 0.96068, "xgb": 0.96064, "nn": 0.96022}
res = {"single_cv": single,
 "cv_steps": [{"n": int(k), "cv": cv[k], "gain": round(cv[k] - cv[str(int(k) - 1)], 5) if k != "1" else None} for k in ["1", "2", "3", "4"]],
 "cv_total_gain": round(cv["4"] - cv["1"], 5), "share_second_model": round((cv["2"] - cv["1"]) / (cv["4"] - cv["1"]), 3),
 "nested_minus_plain": round(cv["4n"] - cv["4"], 5), "stack_lr_minus_blend": round(cv["S1"] - cv["4"], 5), "stack_lgb_minus_blend": round(cv["S2"] - cv["4"], 5)}
refit_steps = [
 ("CatBoost だけ（4回分の平均）", "v25s"), ("LightGBM＋CatBoost・1回分", "v12"), ("同じ2種類・3回分の平均", "v17"), ("同じ2種類・4回分の平均", "v17b"),
 ("＋XGBoost 0.15", "v22"), ("＋NN 0.15", "v20"), ("4種類を CV の比率で", "v25")]
res["refit_steps"] = [{"what": w, "version": v, "public": U[v], "private": P[v]} for w, v in refit_steps]
res["private_single_to_best"] = round(P["v17b"] - P["v25s"], 5); res["public_single_to_best"] = round(U["v22"] - U["v25s"], 5)
res["xgb_added"] = {"cv": round(cv["3"] - cv["2"], 5), "public": round(U["v22"] - U["v17b"], 5), "private": round(P["v22"] - P["v17b"], 5)}
res["nn_added"] = {"cv_weight015": "+0.00003〜0.00004（v13 の記録）", "public": round(U["v20"] - U["v17b"], 5), "private": round(P["v20"] - P["v17b"], 5)}
res["early_three_models"] = {"cv": round(0.9588 - 0.95868, 5), "public": round(U["v2"] - U["v1"], 5), "private": round(P["v2"] - P["v1"], 5)}
res["rank_corr"] = dict(zip(c.pair, c.rank_corr))
save_json(res, "a310_main.json")
pd.DataFrame(res["refit_steps"]).to_csv(out("results", "a310_refit_steps.csv"), index=False)
# 図1 CV：本数ごと
fig, ax = plt.subplots(figsize=(8, 4.4), dpi=150)
lab = ["CatBoost\nだけ", "＋LightGBM", "＋XGBoost", "＋NN", "4本\n（入れ子CV）", "4本 stacking\n（ロジスティック）", "4本 stacking\n（LightGBM）"]
val = [cv[k] for k in ["1", "2", "3", "4", "4n", "S1", "S2"]]
col = ["#2980b9"] * 4 + ["#7f8c8d"] * 3
ax.bar(range(7), [v - 0.9608 for v in val], bottom=0.9608, color=col)
for i, v in enumerate(val): ax.text(i, v + 0.000004, f"{v:.5f}", ha="center", fontsize=9)
ax.set_xticks(range(7)); ax.set_xticklabels(lab, fontsize=8.5); ax.set_ylim(0.9608, 0.96115)
ax.set_ylabel("正直な CV の AUC（縦軸は 0.9608 から）"); ax.set_title("混ぜる本数と CV：伸びの7割は2本目で出た"); ax.ticklabel_format(axis="y", useOffset=False)
fig.tight_layout(); fig.savefig(out("figures", "a310_cv_steps.png")); plt.close(fig)
# 図2 refit 版の Public / Private（縦軸は別々）
labs = ["CatBoost\nだけ", "LightGBM\n＋CatBoost\n1回分", "同じ2種類\n3回分の平均", "同じ2種類\n4回分の平均", "＋XGBoost\n0.15", "＋NN\n0.15", "4種類を\nCV の比率で"]
fig, axes = plt.subplots(2, 1, figsize=(9, 6.4), dpi=150, sharex=True)
x = np.arange(len(refit_steps))
for ax, vals, base, colr, name in [(axes[0], [U[v] for _, v in refit_steps], 0.9606, "#2980b9", "Public"), (axes[1], [P[v] for _, v in refit_steps], 0.9616, "#c0392b", "Private")]:
    ax.bar(x, [v - base for v in vals], .6, bottom=base, color=colr)
    for i, v in enumerate(vals): ax.text(i, v + 0.000004, f"{v:.5f}", ha="center", fontsize=9)
    ax.set_ylim(base, base + 0.00027); ax.set_ylabel(f"{name}（縦軸は {base} から）"); ax.ticklabel_format(axis="y", useOffset=False); ax.grid(axis="y", alpha=.3)
axes[1].set_xticks(x); axes[1].set_xticklabels(labs, fontsize=8.5)
axes[0].set_title("全データで学び直した版：混ぜ方ごとの Public と Private")
fig.tight_layout(); fig.savefig(out("figures", "a310_refit_steps.png")); plt.close(fig)
# 図3 表：順位相関と足した結果
rows = [["同じ作り方の refit どうし", "0.998〜0.999", "3本の平均で Public +0.00002・Private +0.00001"],
        ["特徴量を変えた refit（v18）と他の refit", "0.9968〜0.9979", "4本目に足して Public +0.00001・Private +0.00003"],
        ["refit の平均と XGBoost", "0.9928", "0.15 混ぜて Public +0.00004・Private −0.00001"],
        ["refit の平均と NN", "0.9765", "0.15 混ぜて Public −0.00003・Private −0.00001"]]
table_png(rows, ["混ぜた相手", "予測の順位相関", "混ぜた結果"], out("figures", "a310_corr.png"), widths=[.36, .16, .46], fs=9, title="予測の違いの大きさと、混ぜた結果")
print(json.dumps(res, ensure_ascii=False)[:1600])
