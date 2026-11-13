"""557 効き方が層で違うのに、交互作用を入れずに回帰すると、全体の係数は何を表すのか（正解の分かるデータで試す）

架空の店 600店を3つの層（駅前・住宅地・郊外）に分ける。施策（売り場の変更）の効き方は層で違い、
施策をした店の割合も層で違う。層のダミーだけを入れて交互作用を入れない回帰の係数が、
どの平均（店の割合で平均した効果・施策した店の効果）に近いかを数える。
"""
import json
import numpy as np, pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import save, RES, SQL, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED, N, REPS = 557, 600, 2000
rng = np.random.default_rng(SEED)
SRC = "架空のデータ（作成者が乱数で作成、seed 557）"
LAYERS = ["駅前", "住宅地", "郊外"]
EFFECT = np.array([2.0, 5.0, 10.0])     # 層ごとの本当の効果（1日の売上、万円）
BASE = np.array([50.0, 40.0, 30.0])     # 施策なしの1日の売上の平均（万円）
SD = 6.0


def make(share=(1/3, 1/3, 1/3), p=(0.5, 0.1, 0.05), n=N):
    counts = np.round(np.array(share) * n).astype(int); counts[-1] = n - counts[:-1].sum()
    g = np.repeat(np.arange(3), counts)
    while True:  # どの層にも施策あり・なしの店が少なくとも1店ずつあるように引き直す
        t = (rng.random(n) < np.array(p)[g]).astype(float)
        if all(0 < t[g == k].sum() < (g == k).sum() for k in range(3)): break
    y = BASE[g] + EFFECT[g] * t + rng.normal(0, SD, n)
    return g, t, y


def ols(X, y):
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b; s2 = e @ e / (len(y) - X.shape[1])
    V = s2 * np.linalg.inv(X.T @ X)
    return b, V


def estimates(g, t, y):
    n = len(y); D = np.column_stack([(g == k).astype(float) for k in range(3)])
    out = {}
    out["simple"] = y[t == 1].mean() - y[t == 0].mean()                # 単純な差
    b, V = ols(np.column_stack([t, D]), y)                               # 層のダミーだけ（交互作用なし）
    out["dummy"], out["dummy_se"] = b[0], np.sqrt(V[0, 0])
    b, V = ols(np.column_stack([D, D * t[:, None]]), y)                  # 交互作用あり（層ごとの効果）
    eff = b[3:]; Ve = V[3:, 3:]
    w_all = D.mean(0); w_tr = D[t == 1].mean(0)
    out["layer_eff"] = eff.tolist()
    out["inter_all"], out["inter_all_se"] = w_all @ eff, np.sqrt(w_all @ Ve @ w_all)
    out["inter_tr"] = w_tr @ eff
    # 交互作用なしの係数が暗に使っている重み：層の店数 × 施策した割合 ×（1 − 施策した割合）
    pk = np.array([t[g == k].mean() for k in range(3)]); nk = D.sum(0)
    w = nk * pk * (1 - pk); out["implicit_w"] = (w / w.sum()).tolist()
    out["formula"] = (w / w.sum()) @ np.array([y[(g == k) & (t == 1)].mean() - y[(g == k) & (t == 0)].mean() for k in range(3)])
    out["ate_true"] = w_all @ EFFECT; out["att_true"] = w_tr @ EFFECT
    return out


# ---- 1. 例の1回
g, t, y = make()
ex = estimates(g, t, y)
df = pd.DataFrame({"layer": np.array(LAYERS)[g], "treated": t.astype(int), "sales": y.round(3)})
df.to_csv(RES / "example_stores.csv", index=False)
con = duckdb.connect(config={"threads": 1})
con.register("stores", pd.read_csv(RES / "example_stores.csv"))
sql_res = con.execute(open(SQL / "a557_no_interaction.sql", encoding="utf-8").read()).df()
sql_res.to_csv(RES / "sql_check.csv", index=False)
# CSV に丸めた値で Python 側も計算し直して比較
g2 = df.layer.map({k: i for i, k in enumerate(LAYERS)}).to_numpy(); ex2 = estimates(g2, df.treated.to_numpy().astype(float), df.sales.to_numpy())
sql_check = dict(python_dummy=ex2["dummy"], sql_dummy=float(sql_res["dummy_coef"].iloc[0]),
                 python_ate=ex2["inter_all"], sql_ate=float(sql_res["ate_by_store_share"].iloc[0]))

# ---- 2. 2,000回くり返す（基本の設定）
R = [estimates(*make()) for _ in range(REPS)]
keys = ["simple", "dummy", "inter_all", "inter_tr", "formula"]
mc = {k: np.array([r[k] for r in R]) for k in keys}
ate = np.mean([r["ate_true"] for r in R]); att = np.mean([r["att_true"] for r in R])
cover_dummy = np.mean([abs(r["dummy"] - r["ate_true"]) <= 1.96 * r["dummy_se"] for r in R])
cover_inter = np.mean([abs(r["inter_all"] - r["ate_true"]) <= 1.96 * r["inter_all_se"] for r in R])
summ = pd.DataFrame([dict(method=k, mean=v.mean(), p05=np.percentile(v, 5), p95=np.percentile(v, 95)) for k, v in mc.items()])
summ.round(4).to_csv(RES / "methods_summary.csv", index=False)
impw = np.mean([r["implicit_w"] for r in R], 0)

# ---- 3. 駅前で施策をした割合を動かす（住宅地0.1・郊外0.05 は固定）
rows = []
for pa in [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9]:
    rr = [estimates(*make(p=(pa, 0.1, 0.05))) for _ in range(REPS // 4)]
    rows.append(dict(p_station=pa, dummy=np.mean([r["dummy"] for r in rr]), ate=np.mean([r["ate_true"] for r in rr]),
                     att=np.mean([r["att_true"] for r in rr]), inter_all=np.mean([r["inter_all"] for r in rr])))
byp = pd.DataFrame(rows); byp.round(4).to_csv(RES / "by_p_station.csv", index=False)

# ---- 4. 施策をした割合が層で同じなら
same = [estimates(*make(p=(0.2, 0.2, 0.2))) for _ in range(REPS // 4)]
same_res = dict(dummy=np.mean([r["dummy"] for r in same]), ate=np.mean([r["ate_true"] for r in same]))

# ---- 5. 郊外の店の割合を動かす（施策の割合は基本どおり）
rows = []
for sc in [0.2, 1/3, 0.5, 0.7]:
    sh = ((1 - sc) / 2, (1 - sc) / 2, sc)
    rr = [estimates(*make(share=sh)) for _ in range(REPS // 4)]
    rows.append(dict(share_suburb=sc, dummy=np.mean([r["dummy"] for r in rr]), ate=np.mean([r["ate_true"] for r in rr])))
bys = pd.DataFrame(rows); bys.round(4).to_csv(RES / "by_share_suburb.csv", index=False)

main = dict(example=dict({k: ex[k] for k in ["simple", "dummy", "inter_all", "inter_tr", "formula", "ate_true", "att_true"]},
                         layer_eff=ex["layer_eff"], implicit_w=ex["implicit_w"]),
            sql_check=sql_check,
            mc=dict(ate=ate, att=att, **{k + "_mean": float(v.mean()) for k, v in mc.items()},
                    cover_dummy_for_ate=cover_dummy, cover_inter_for_ate=cover_inter, implicit_w=impw.tolist(),
                    store_share=[1/3] * 3),
            same_p=same_res)
json.dump(main, open(RES / "a557_main.json", "w"), ensure_ascii=False, indent=1, default=float)

# ---- 図1：層ごとの効果と、2つの重み
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
x = np.arange(3)
ax[0].bar(x, EFFECT, color=LIGHT, label="本当の効果")
ax[0].plot(x, ex["layer_eff"], "o", color=BLUE, label="交互作用ありの推定（例の1回）")
ax[0].axhline(ate, color=GREEN, ls="--", lw=1.2); ax[0].text(2.5, ate + 0.15, f"店の割合で平均 {ate:.1f}", color=GREEN, va="bottom", fontsize=9)
ax[0].axhline(mc["dummy"].mean(), color=ORANGE, lw=1.6); ax[0].text(2.5, mc["dummy"].mean() - 0.15, f"交互作用なし {mc['dummy'].mean():.1f}", color=ORANGE, va="top", fontsize=9)
ax[0].set_xticks(x, [f"{l}\n（施策 {p:.0%}）" for l, p in zip(LAYERS, [0.5, 0.1, 0.05])]); ax[0].set_ylabel("施策の効果（1日の売上、万円）")
ax[0].set_title("層ごとの効果"); ax[0].legend(frameon=False, fontsize=8.5, loc="upper left"); ax[0].set_xlim(-0.6, 3.9); ax[0].set_ylim(0, 13)
wd = 0.38
ax[1].bar(x - wd / 2, [1/3] * 3, wd, color=GREEN, label="店の割合")
ax[1].bar(x + wd / 2, impw, wd, color=ORANGE, label="交互作用なしの係数が使う重み")
for i in range(3):
    ax[1].text(i - wd / 2, 1/3 + 0.01, f"{1/3:.0%}", ha="center", fontsize=9); ax[1].text(i + wd / 2, impw[i] + 0.01, f"{impw[i]:.0%}", ha="center", fontsize=9)
ax[1].set_xticks(x, LAYERS); ax[1].set_ylabel("重み"); ax[1].set_ylim(0, 0.8); ax[1].set_title("3つの層をどの重みで平均しているか")
ax[1].legend(frameon=False, fontsize=8.5)
save(fig, "a557_layers.png", SRC + "。重みは2,000回の平均")

# ---- 図2：駅前で施策をした割合を動かす
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.plot(byp.p_station, byp.ate, "--", color=GREEN, label="店の割合で平均した本当の効果")
ax.plot(byp.p_station, byp.att, ":", color=GRAY, label="施策した店の本当の効果")
ax.plot(byp.p_station, byp.dummy, "o-", color=ORANGE, label="交互作用なしの係数")
ax.plot(byp.p_station, byp.inter_all, "s", color=BLUE, ms=5, label="交互作用あり → 店の割合で平均")
ax.set_xlabel("駅前で施策をした店の割合（住宅地10%・郊外5%は固定）"); ax.set_ylabel("効果（1日の売上、万円）")
ax.set_xticks(byp.p_station, [f"{v:.0%}" for v in byp.p_station]); ax.legend(frameon=False, fontsize=8.5); ax.set_ylim(0, 8)
ax.set_title("交互作用なしの係数は、施策をした割合しだいで動く")
save(fig, "a557_vary_p.png", SRC + "。各条件500回の平均")

# ---- 図3：方法ごとの推定の分布
lab = {"simple": "単純な差\n（層を入れない）", "dummy": "層のダミーだけ\n（交互作用なし）", "inter_all": "交互作用あり\n→店の割合で平均", "inter_tr": "交互作用あり\n→施策した店で平均"}
fig, ax = plt.subplots(figsize=(8, 4.2))
for i, k in enumerate(lab):
    v = mc[k]; ax.boxplot(v, positions=[i], widths=0.5, showfliers=False, patch_artist=True, whis=(5, 95),
                          boxprops=dict(facecolor=LIGHT, color=BLUE), medianprops=dict(color=INK))
    ax.text(i + 0.3, np.percentile(v, 75), f"平均\n{v.mean():.2f}", ha="left", va="center", fontsize=9)
ax.axhline(ate, color=GREEN, ls="--", lw=1.2); ax.text(3.75, ate + 0.15, f"店の割合で平均 {ate:.2f}", color=GREEN, va="bottom", fontsize=8.5)
ax.axhline(att, color=GRAY, ls=":", lw=1.2); ax.text(3.75, att - 0.15, f"施策した店 {att:.2f}", color=GRAY, va="top", fontsize=8.5)
ax.set_xticks(range(4), list(lab.values()), fontsize=9); ax.set_xlim(-0.6, 4.5); ax.set_ylabel("推定した効果（万円）")
ax.set_title("同じデータで、4つの方法の答え")
save(fig, "a557_methods.png", SRC + "。600店×2,000回。箱は四分位、ひげは5〜95%")
print(json.dumps(main, ensure_ascii=False, default=float, indent=0)[:2500]); print(byp.round(2)); print(bys.round(2)); print(summ.round(2))
