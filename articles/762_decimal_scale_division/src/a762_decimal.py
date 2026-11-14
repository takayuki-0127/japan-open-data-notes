"""762 申込率を小数の桁の少ない DECIMAL に入れると、率はどれだけ丸まり、店の順位はどれだけ入れ替わるのか

架空の80店の1か月の来店数と申込み数（申込率はおよそ1〜6%）。申込率を
  そのまま（浮動小数）、比で小数2桁 DECIMAL(5,2)、小数3桁 DECIMAL(6,3)、小数4桁 DECIMAL(7,4)、%で小数1桁 DECIMAL(5,1)
の列に入れたときの丸まり方と、店を申込率で並べたときの順位の入れ替わり・同点を数える。
DuckDB（1スレッド）の CAST の結果を、Python の四捨五入（Decimal の ROUND_HALF_UP）と照らし合わせる。seed 762。
"""
import json
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の店の来店数と申込み数（作成者が乱数で作成、seed 762）"
rng = np.random.default_rng(762)
NS = 80
visitors = rng.integers(2000, 20000, NS)
rate = np.clip(rng.normal(0.032, 0.011, NS), 0.008, 0.07)
apps = rng.binomial(visitors, rate)
S = pd.DataFrame({"store_id": [f"店{i + 1:02d}" for i in range(NS)], "visitors": visitors, "applications": apps})
S.to_csv(DATA / "stores.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("stores", S)
q = [x for x in (SQL / "02_decimal_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
D = con.execute(q[0]).df()
T = con.execute(q[1]).df()
# Python の四捨五入と照らし合わせる
hu = lambda a, b, nd, mul=1: float((Decimal(int(a) * mul) / Decimal(int(b))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))
assert all(abs(float(D.rate_dec2[i]) - hu(S.applications[i], S.visitors[i], 2)) < 1e-12 for i in range(NS))
assert all(abs(float(D.rate_dec4[i]) - hu(S.applications[i], S.visitors[i], 4)) < 1e-12 for i in range(NS))
assert all(abs(float(D.pct_dec1[i]) - hu(S.applications[i], S.visitors[i], 1, 100)) < 1e-12 for i in range(NS))
true_pct = D.rate_double * 100
M = {"dec2": D.rate_dec2.astype(float) * 100, "dec3": D.rate_dec3.astype(float) * 100, "dec4": D.rate_dec4.astype(float) * 100, "pct1": D.pct_dec1.astype(float)}
LAB = {"dec2": "比・小数2桁 DECIMAL(5,2)", "dec3": "比・小数3桁 DECIMAL(6,3)", "dec4": "比・小数4桁 DECIMAL(7,4)", "pct1": "%・小数1桁 DECIMAL(5,1)"}
true_rank = true_pct.rank(ascending=False, method="first")
res = {}
for k, v in M.items():
    err = (v - true_pct).abs()
    rk = v.rank(ascending=False, method="min")
    ties = v.value_counts()
    # 上位10店：丸めた値で「10位以内」に入る店の数（同点で10位を超えることがある）
    in_top = int((rk <= 10).sum())
    res[k] = {"label": LAB[k], "distinct_values": int(v.nunique()), "mean_abs_err_pt": round(float(err.mean()), 4), "max_abs_err_pt": round(float(err.max()), 4),
              "max_rel_err_pct": round(float((err / true_pct).max() * 100), 1), "stores_sharing_a_value": int(ties[ties > 1].sum()),
              "largest_tie": int(ties.max()), "spearman_vs_true": round(float(spearmanr(v, true_pct).statistic), 4),
              "stores_ranked_top10_or_tied": in_top, "mean_of_stored_minus_true_mean_pt": round(float(v.mean() - true_pct.mean()), 4)}
out = {"stores": NS, "rate_pct_range": [round(float(true_pct.min()), 2), round(float(true_pct.max()), 2)],
       "rate_pct_median": round(float(true_pct.median()), 2), "methods": res,
       "dec2_values_seen": sorted(set(float(x) for x in D.rate_dec2)),
       "duckdb_double_for_decimal_division": True}
json.dump(out, open(RES / "a762_main.json", "w"), ensure_ascii=False, indent=1)
D.assign(rate_true_pct=true_pct.round(4)).to_csv(RES / "stored_rates.csv", index=False)

# 図1：本当の率と、小数2桁に入れた率
fig, ax = plt.subplots(figsize=(7, 4.6))
ax.scatter(true_pct, M["dec2"], s=22, color=ORANGE, label=LAB["dec2"], zorder=3)
ax.scatter(true_pct, M["pct1"], s=10, color=BLUE, label=LAB["pct1"], zorder=4)
lim = [0, true_pct.max() * 1.1]; ax.plot(lim, lim, color=GRAY, lw=0.8, ls="--")
ax.set_xlabel("本当の申込率（%）"); ax.set_ylabel("列に入れた申込率（%）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("比を小数2桁で持つと、申込率は1ポイントきざみの階段になる")
save(fig, "a762_steps.png", SRC)
# 図2：誤差と同点
fig, ax = plt.subplots(figsize=(8, 3.8))
ks = list(M); x = np.arange(len(ks))
ax.bar(x - 0.18, [res[k]["max_rel_err_pct"] for k in ks], 0.36, color=ORANGE, label="いちばん大きいずれ（本当の率に対する%）")
ax.bar(x + 0.18, [res[k]["stores_sharing_a_value"] / NS * 100 for k in ks], 0.36, color=LIGHT, label="ほかの店と同じ値になった店（%）")
for i, k in enumerate(ks):
    ax.text(i - 0.18, res[k]["max_rel_err_pct"] + 1, f"{res[k]['max_rel_err_pct']:.1f}", ha="center", fontsize=9)
    ax.text(i + 0.18, res[k]["stores_sharing_a_value"] / NS * 100 + 1, f"{res[k]['stores_sharing_a_value'] / NS * 100:.0f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([LAB[k].replace(" DEC", "\nDEC") for k in ks], fontsize=8.5); ax.set_ylabel("%"); ax.set_ylim(0, 105)
ax.legend(frameon=False, fontsize=9); ax.set_title("小数の桁が足りないと、ずれも同点も大きい")
save(fig, "a762_errors.png", SRC)
# 図3：小数2桁の値ごとの店の数
fig, ax = plt.subplots(figsize=(7.5, 3.6))
ax.bar([f"{float(v) * 100:.0f}%" for v in T.rate_dec2], T.n_stores, color=ORANGE)
for i, n in enumerate(T.n_stores):
    ax.text(i, n + 0.4, str(n), ha="center")
ax.set_xlabel("小数2桁の列に入った申込率"); ax.set_ylabel("店の数")
ax.set_title(f"80店が{res['dec2']['distinct_values']}つの値にまとまり、いちばん多い値に{res['dec2']['largest_tie']}店が並ぶ")
save(fig, "a762_ties.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
