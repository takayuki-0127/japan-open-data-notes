"""308：最終提出の2本の選び方を、終了後の Private の点数で確かめる"""
from common import *
from scipy.stats import spearmanr
import itertools
d = load(); s = d.dropna(subset=["public"]).copy()
s["gap"] = s.private - s.public
top = s[s.public > 0.96]; refit = s[s.kind == "refit"]; fold = top[top.kind == "fold"]
P = dict(zip(s.version, s.private)); U = dict(zip(s.version, s.public))
rules = [
 ("CV で選ぶ（記録に書いた2本）", ["v25", "v25s"]),
 ("Public の上位2本（同点は v25）", ["v22", "v25"]),
 ("Public の上位2本（同点は v17b）", ["v22", "v17b"]),
 ("10/19 朝の案（Public 最良＋甘い CV 最良）", ["v22", "v9"]),
 ("fold 版だけの時点の案（v9＋v3）", ["v9", "v3"]),
]
res = {"n_submissions": int(len(s)), "n_versions": int(len(d)),
 "spearman_all": round(float(spearmanr(s.public, s.private)[0]), 3),
 "spearman_top19": round(float(spearmanr(top.public, top.private)[0]), 3), "n_top": int(len(top)),
 "spearman_refit": round(float(spearmanr(refit.public, refit.private)[0]), 3), "n_refit": int(len(refit)),
 "refit_public_range": round(float(refit.public.max() - refit.public.min()), 5),
 "refit_private_range": round(float(refit.private.max() - refit.private.min()), 5),
 "gap_mean": round(float(s.gap.mean()), 5), "gap_min": round(float(s.gap.min()), 5), "gap_max": round(float(s.gap.max()), 5),
 "refit_minus_fold_private": round(float(refit.private.mean() - fold.private.mean()), 5),
 "refit_minus_fold_public": round(float(refit.public.mean() - fold.public.mean()), 5),
 "best_private": float(s.private.max()), "best_private_versions": list(s[s.private == s.private.max()].version),
 "rules": [{"rule": r, "pair": p, "final": max(P[v] for v in p), "each": [P[v] for v in p]} for r, p in rules]}
# 2本の全組み合わせ：最終点（高い方）の分布
pairs = [max(P[a], P[b]) for a, b in itertools.combinations(refit.version, 2)]
res["all_refit_pairs"] = {"n": len(pairs), "min": min(pairs), "max": max(pairs), "share_best": round(sum(x == max(pairs) for x in pairs) / len(pairs), 3)}
hon = s[s.cv_type.isin(["honest", "honest_fold_equiv"]) & (s.kind == "refit")]
res["cv_vs_private_refit"] = {"n": int(len(hon)), "spearman": round(float(spearmanr(hon.cv, hon.private)[0]), 3)}
res["blend_minus_single"] = {"cv": round(0.96107 - 0.96094, 5), "public": round(U["v25"] - U["v25s"], 5), "private": round(P["v25"] - P["v25s"], 5)}
save_json(res, "a308_main.json")
s[["version", "kind", "cv", "cv_type", "public", "private", "gap"]].round(5).to_csv(out("results", "a308_scores.csv"), index=False)
# 図1 Public と Private
fig, ax = plt.subplots(figsize=(7.5, 5.5), dpi=150)
for k, c, lab in [("fold", "#7f8c8d", "fold 平均の版"), ("refit", "#c0392b", "全データで学び直した版（refit）")]:
    t = top[top.kind == k]; ax.scatter(t.public, t.private, c=c, s=45, label=lab, zorder=3)
off = {"v25": (6, 6), "v25s": (6, -12), "v22": (6, -4), "v17b": (-30, 8), "v9": (6, 4), "v3": (6, -12), "v10": (-22, -12), "v12": (-24, -4)}
for v, o in off.items():
    ax.annotate(v.replace("v25s", "v25 単体"), (U[v], P[v]), xytext=o, textcoords="offset points", fontsize=9)
ax.set_xlabel("Public の点数（期間中に見える）"); ax.set_ylabel("Private の点数（終了後に分かる）")
ax.set_title("Public と Private の点数（0.96 以上の19回の提出）"); ax.grid(alpha=.3); ax.legend(loc="lower right")
ax.ticklabel_format(useOffset=False); fig.tight_layout(); fig.savefig(out("figures", "a308_public_private.png")); plt.close(fig)
# 図2 選び方ごとの最終点
fig, ax = plt.subplots(figsize=(8.5, 4.2), dpi=150)
lab = [r for r, _ in rules][::-1]; val = [max(P[v] for v in p) for _, p in rules][::-1]
ax.barh(lab, [v - 0.9615 for v in val], left=0.9615, color=["#95a5a6", "#95a5a6", "#95a5a6", "#95a5a6", "#c0392b"])
for i, v in enumerate(val): ax.text(v + 0.000003, i, f"{v:.5f}", va="center", fontsize=10)
ax.axvline(s.private.max(), color="k", ls=":", lw=1); ax.set_xlim(0.9615, 0.96176)
ax.set_xlabel("2本のうち高い方の Private の点数（横軸は 0.9615 から。点線は全提出の最高）")
ax.set_title("選び方を変えても、最終の点数の差は 0.00009 以内"); ax.ticklabel_format(axis="x", useOffset=False)
fig.tight_layout(); fig.savefig(out("figures", "a308_rules.png")); plt.close(fig)
# 図3 候補の表
rows = [[n, f"{c}", f"{U[v]:.5f}", f"{P[v]:.5f}"] for n, v, c in [
 ("v25 ブレンド（CV 最良のブレンド）", "v25", "0.96107"), ("v25 単体（CV 最良の単体・CatBoost）", "v25s", "0.96094"),
 ("v22（Public 最良）", "v22", "0.96104"), ("v17b（refit 4本の平均）", "v17b", "—"), ("v9（甘い CV で最良）", "v9", "0.96141（甘い）"), ("v3（fold 版で Public 最良）", "v3", "0.96120（甘い）")]]
table_png(rows, ["候補", "CV", "Public", "Private"], out("figures", "a308_candidates.png"), widths=[.46, .2, .14, .14], title="最終提出の候補：CV・Public・Private")
print(json.dumps(res, ensure_ascii=False)[:900])
