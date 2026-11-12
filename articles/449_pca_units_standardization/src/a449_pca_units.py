"""449 指標の単位をそろえないまま主成分分析をすると、第1主成分はどれだけ変わるのか
架空の店300店・指標8本（単位と桁が違う）と、SSDSE-B の都道府県データ8項目。seed 449"""
import json
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from common import *

rng = np.random.default_rng(449)
NAMES = ["売上高（円）", "従業員数（人）", "売場面積（㎡）", "客単価（円）", "粗利率（%）", "リピート率（0〜1）", "営業年数（年）", "在庫回転（回）"]
LOGV = [0, 1, 2, 3]                      # 対数に直す指標（右に裾が長いもの）


def make(n=300):
    size, quality = rng.standard_normal(n), rng.standard_normal(n)
    e = rng.standard_normal((n, 8))
    X = np.column_stack([
        np.exp(np.log(8e7) + 0.7 * size + 0.15 * quality + 0.25 * e[:, 0]),     # 売上高（円）
        np.exp(np.log(12) + 0.6 * size + 0.30 * e[:, 1]),                       # 従業員数
        np.exp(np.log(300) + 0.5 * size + 0.35 * e[:, 2]),                      # 売場面積
        np.exp(np.log(1800) + 0.25 * quality + 0.20 * e[:, 3]),                 # 客単価
        30 + 4 * quality + 3 * e[:, 4],                                         # 粗利率
        np.clip(0.4 + 0.08 * quality + 0.06 * e[:, 5], 0.02, 0.98),             # リピート率
        np.clip(12 + 6 * e[:, 6], 0.5, None),                                   # 営業年数
        np.clip(8 + 1.0 * quality - 0.8 * size + 1.5 * e[:, 7], 0.5, None)])    # 在庫回転
    return X, size, quality


def pca1(M):
    """列を中心化して第1主成分（重み・得点・寄与率）"""
    Z = M - M.mean(0); U, s, Vt = np.linalg.svd(Z, full_matrices=False)
    w = Vt[0]; w = w * np.sign(w[np.argmax(np.abs(w))])
    return w, Z @ w, s[0] ** 2 / (s ** 2).sum()


def three(X, logv):
    raw = X.copy()
    std = (X - X.mean(0)) / X.std(0, ddof=1)
    L = X.copy(); L[:, logv] = np.log(L[:, logv]); lstd = (L - L.mean(0)) / L.std(0, ddof=1)
    return {"そのまま": raw, "標準化": std, "対数にしてから標準化": lstd}


# ---- 1. 1回分の例
X, size, quality = make()
pd.DataFrame(X, columns=NAMES).round(4).to_csv(DATA / "example_stores.csv", index=False)
rows, scores = [], {}
for k, M in three(X, LOGV).items():
    w, sc, ev = pca1(M); scores[k] = sc
    for nm, wi in zip(NAMES, w): rows.append(dict(method=k, variable=nm, weight=wi, weight_sq_share=wi ** 2))
    rows.append(dict(method=k, variable="（第1主成分の寄与率）", weight=ev, weight_sq_share=np.nan))
ex = pd.DataFrame(rows); ex.round(4).to_csv(RES / "example_weights.csv", index=False)
rank = {f"{a} と {b}": float(spearmanr(scores[a], scores[b])[0]) for a, b in [("そのまま", "標準化"), ("そのまま", "対数にしてから標準化"), ("標準化", "対数にしてから標準化")]}
corr_latent = {k: dict(size=float(abs(np.corrcoef(sc, size)[0, 1])), quality=float(abs(np.corrcoef(sc, quality)[0, 1]))) for k, sc in scores.items()}

# ---- 2. 1,000回：桁の大きい1本だけで決まる割合、順位の相関
REP = 1000; acc = []
for _ in range(REP):
    Xr, sz, ql = make(); T = three(Xr, LOGV); r = {}
    ws = {k: pca1(M) for k, M in T.items()}
    acc.append(dict(raw_top_share=float((ws["そのまま"][0] ** 2).max()), raw_top_is_sales=int(np.argmax(ws["そのまま"][0] ** 2) == 0),
                    std_top_share=float((ws["標準化"][0] ** 2).max()), log_top_share=float((ws["対数にしてから標準化"][0] ** 2).max()),
                    rho_raw_std=float(spearmanr(ws["そのまま"][1], ws["標準化"][1])[0]), rho_std_log=float(spearmanr(ws["標準化"][1], ws["対数にしてから標準化"][1])[0]),
                    corr_size_raw=float(abs(np.corrcoef(ws["そのまま"][1], sz)[0, 1])), corr_size_std=float(abs(np.corrcoef(ws["標準化"][1], sz)[0, 1])),
                    corr_size_log=float(abs(np.corrcoef(ws["対数にしてから標準化"][1], sz)[0, 1])),
                    top10_overlap_raw_std=len(set(np.argsort(-ws["そのまま"][1])[:30]) & set(np.argsort(-np.sign(np.corrcoef(ws["標準化"][1], ws["そのまま"][1])[0, 1]) * ws["標準化"][1])[:30])) / 30))
sim = pd.DataFrame(acc); sim.round(4).to_csv(RES / "simulation_1000.csv", index=False)

# ---- 3. 売上高の単位だけを変える（円・千円・百万円・億円・10億円）
rows = []
for unit, div in [("円", 1), ("千円", 1e3), ("百万円", 1e6), ("億円", 1e8), ("10億円", 1e9)]:
    Xu = X.copy(); Xu[:, 0] = Xu[:, 0] / div
    w, sc, ev = pca1(Xu); ws, scs, evs = pca1((Xu - Xu.mean(0)) / Xu.std(0, ddof=1))
    rows.append(dict(sales_unit=unit, raw_top_variable=NAMES[int(np.argmax(w ** 2))], raw_top_share=float((w ** 2).max()), raw_sales_share=float(w[0] ** 2),
                     raw_pc1_explained=float(ev), rho_with_yen_raw=float(abs(spearmanr(sc, scores["そのまま"])[0])),
                     std_weight_max_abs_diff=float(np.abs(np.abs(ws) - np.abs(pca1(three(X, LOGV)["標準化"])[0])).max())))
units = pd.DataFrame(rows); units.round(6).to_csv(RES / "sales_unit_sweep.csv", index=False)

# ---- 4. 公的データの例：SSDSE-B 2023年度・47都道府県・8項目（順位は載せない）
P = pd.read_csv(DATA / "ssdse_b_2023_8items.csv"); cols = list(P.columns[2:]); XP = P[cols].astype(float).values
rows, psc = [], {}
for k, M in three(XP, [0, 4, 5]).items():
    w, sc, ev = pca1(M); psc[k] = sc
    for nm, wi in zip(cols, w): rows.append(dict(method=k, variable=nm, weight=wi, weight_sq_share=wi ** 2))
    rows.append(dict(method=k, variable="（第1主成分の寄与率）", weight=ev, weight_sq_share=np.nan))
pub = pd.DataFrame(rows); pub.round(6).to_csv(RES / "public_example_weights.csv", index=False)
XP2 = XP.copy(); XP2[:, 0] /= 1e4; XP2[:, 5] /= 1e4          # 人口を万人、宿泊者数を万人泊に
w2, sc2, ev2 = pca1(XP2)
pub_rank = dict(raw_vs_std=float(abs(spearmanr(psc["そのまま"], psc["標準化"])[0])), raw_vs_logstd=float(abs(spearmanr(psc["そのまま"], psc["対数にしてから標準化"])[0])),
                std_vs_logstd=float(abs(spearmanr(psc["標準化"], psc["対数にしてから標準化"])[0])),
                raw_top=cols[int(np.argmax(pca1(XP)[0] ** 2))], raw_top_share=float((pca1(XP)[0] ** 2).max()),
                raw_man_top=cols[int(np.argmax(w2 ** 2))], raw_man_top_share=float((w2 ** 2).max()), raw_vs_raw_man=float(abs(spearmanr(psc["そのまま"], sc2)[0])))

sh = lambda k: {r.variable: round(float(r.weight_sq_share), 4) for r in ex[(ex.method == k) & ex.weight_sq_share.notna()].itertuples()}
main = dict(example_weight_sq_share={k: sh(k) for k in scores}, example_pc1_explained={k: round(float(ex[(ex.method == k) & ex.weight_sq_share.isna()].weight.iloc[0]), 4) for k in scores},
            example_rank_corr={k: round(v, 3) for k, v in rank.items()}, example_corr_with_latent=corr_latent,
            sim=dict(rep=REP, raw_top_share_ge_99=float((sim.raw_top_share >= 0.99).mean()), raw_top_is_sales=float(sim.raw_top_is_sales.mean()),
                     raw_top_share_min=float(sim.raw_top_share.min()), std_top_share_median=float(sim.std_top_share.median()), log_top_share_median=float(sim.log_top_share.median()),
                     rho_raw_std_median=float(sim.rho_raw_std.abs().median()), rho_raw_std_p05=float(sim.rho_raw_std.abs().quantile(0.05)), rho_std_log_median=float(sim.rho_std_log.abs().median()),
                     corr_size_raw=float(sim.corr_size_raw.median()), corr_size_std=float(sim.corr_size_std.median()), corr_size_log=float(sim.corr_size_log.median()),
                     top10pct_overlap_raw_std=float(sim.top10_overlap_raw_std.mean())),
            sales_unit_sweep=units.round(4).to_dict("records"), public=pub_rank,
            public_weight_sq_share={k: {r.variable: round(float(r.weight_sq_share), 4) for r in pub[(pub.method == k) & pub.weight_sq_share.notna()].itertuples()} for k in psc})
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

SRC = "架空の店300店・指標8本（作成者が乱数で作成、seed 449）"
fig, axes = plt.subplots(1, 3, figsize=(11.5, 4.2), sharey=True)
for ax, (k, c) in zip(axes, [("そのまま", GRAY), ("標準化", BLUE), ("対数にしてから標準化", ORANGE)]):
    d = ex[(ex.method == k) & ex.weight_sq_share.notna()]
    ax.barh(d.variable[::-1], d.weight_sq_share[::-1] * 100, color=c); ax.set_title(k); ax.set_xlim(0, 105); ax.set_xlabel("第1主成分の重みの2乗（%）")
    for y, v in enumerate(d.weight_sq_share[::-1] * 100): ax.text(v + 1.5, y, f"{v:.0f}%" if v >= 0.5 else "0%", va="center", fontsize=9)
fig.suptitle("単位をそろえないと、第1主成分は桁のいちばん大きい指標（売上高）だけで決まる", y=1.02)
save(fig, "a449_pc1_weights.png", SRC)

fig, ax = plt.subplots(figsize=(7.8, 4.4))
ax.bar(units.sales_unit, units.raw_sales_share * 100, color=GRAY, label="売上高の重みの2乗（%）")
for i, r in enumerate(units.itertuples()):
    ax.text(i, r.raw_sales_share * 100 + 2, f"{r.raw_sales_share*100:.0f}%", ha="center", fontsize=10)
    ax.text(i, -13, "重みが最大：\n" + r.raw_top_variable.split("（")[0], ha="center", fontsize=8.5, color=INK)
ax.set_ylim(-18, 112); ax.set_yticks([0, 25, 50, 75, 100]); ax.set_xlabel("売上高を書く単位"); ax.set_ylabel("第1主成分のうち売上高の分（%）")
ax.set_title("同じデータでも、売上高の単位を変えるだけで第1主成分が入れ替わる（そのままの場合）")
save(fig, "a449_sales_unit_sweep.png", SRC + "。標準化した場合の重みは、単位を変えても同じ")

fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.4))
ra = lambda v: pd.Series(v).rank().values
s_std = scores["標準化"] * np.sign(np.corrcoef(scores["標準化"], scores["そのまま"])[0, 1])
s_log = scores["対数にしてから標準化"] * np.sign(np.corrcoef(scores["対数にしてから標準化"], scores["標準化"])[0, 1]) * np.sign(np.corrcoef(scores["標準化"], scores["そのまま"])[0, 1])
axes[0].scatter(ra(scores["そのまま"]), ra(s_std), s=9, color=GRAY); axes[0].set_xlabel("そのままの第1主成分の順位"); axes[0].set_ylabel("標準化した第1主成分の順位")
axes[0].set_title(f"そのまま と 標準化（順位の相関 {abs(rank['そのまま と 標準化']):.2f}）", fontsize=11)
axes[1].scatter(ra(s_std), ra(s_log), s=9, color=BLUE); axes[1].set_xlabel("標準化した第1主成分の順位"); axes[1].set_ylabel("対数にしてから標準化した順位")
axes[1].set_title(f"標準化 と 対数＋標準化（順位の相関 {abs(rank['標準化 と 対数にしてから標準化']):.2f}）", fontsize=11)
fig.suptitle("店の並び順は、単位をそろえるかどうかで変わる", y=1.02)
save(fig, "a449_rank_scatter.png", SRC + "。1回分の例")
print(json.dumps(main, ensure_ascii=False, indent=0)[:4500])
