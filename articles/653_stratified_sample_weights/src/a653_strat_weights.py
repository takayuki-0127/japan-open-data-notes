"""653 層ごとに抽出率の違うサンプルを、重みを付けずに平均すると、全体の値はどれだけずれるのか

架空の店2,000店（小1,500・中400・大100）。大きい店ほど少ない数でも全体に効くので、大きい店を多めの割合で抜き出す
（小2%・中10%・大50%、合計120店）。抜き出した店から全体の「1店あたりの月の売上」と「キャッシュレスの割合」を出す。
  W0 重みなしの平均
  W1 抽出率の逆数で重みを付けた平均
  W2 層ごとの平均を、層の店数の割合で合わせる（この設計では W1 と同じ値）
2,000回くり返し、偏り・ばらつき・95%区間の当たり方を見る。1回分の SQL は DuckDB（1スレッド）と pandas で一致を確かめる。seed 653。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN
DATA.mkdir(exist_ok=True)
SRC = "出典：架空の店と抜き出し（作成者が乱数で作成、seed 653）"
rng = np.random.default_rng(653)
SIZES = {"小": (1500, 0.02, 300, 0.35), "中": (400, 0.10, 900, 0.50), "大": (100, 0.50, 3000, 0.70)}  # 店数・抽出率・売上の中心（万円）・キャッシュレスの中心
rows = []
sid = 1
for k, (n, p, mu, cr) in SIZES.items():
    sales = np.round(rng.lognormal(np.log(mu), 0.35, n), 1)
    cash = np.clip(rng.normal(cr, 0.08, n), 0.02, 0.98).round(3)
    for i in range(n):
        rows.append((f"S{sid:04d}", k, sales[i], cash[i], p)); sid += 1
POP = pd.DataFrame(rows, columns=["store_id", "size_class", "sales", "cashless_rate", "sample_rate"])
POP.to_csv(DATA / "stores_population.csv", index=False)
true = {"sales": POP.sales.mean(), "cashless_rate": POP.cashless_rate.mean()}


def draw(r):
    parts = []
    for k, (n, p, _, _) in SIZES.items():
        sub = POP[POP.size_class == k]
        parts.append(sub.iloc[np.sort(r.choice(n, int(round(n * p)), replace=False))])
    return pd.concat(parts)


def est(S):
    w = 1 / S.sample_rate
    o = {}
    for v in ["sales", "cashless_rate"]:
        o[v + "_W0"] = S[v].mean()
        o[v + "_W1"] = (S[v] * w).sum() / w.sum()
        sh = POP.size_class.value_counts(normalize=True)
        o[v + "_W2"] = sum(S[S.size_class == k][v].mean() * sh[k] for k in SIZES)
        # 区間：W0 は単純な標準誤差、W2 は層別の標準誤差（有限母集団の修正つき）
        o[v + "_W0_se"] = S[v].std(ddof=1) / np.sqrt(len(S))
        se2 = 0
        for k, (n, p, _, _) in SIZES.items():
            x = S[S.size_class == k][v]; m = len(x)
            se2 += sh[k] ** 2 * (1 - m / n) * x.var(ddof=1) / m
        o[v + "_W2_se"] = np.sqrt(se2)
    return o


S1 = draw(np.random.default_rng(6531))
S1.to_csv(DATA / "sample_stores.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("sample_stores", S1)
q = [x for x in (SQL / "02_weighted_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
r1 = con.execute(q[0]).df().iloc[0]
e1 = est(S1)
assert np.isclose(r1.sales_unweighted, e1["sales_W0"]) and np.isclose(r1.sales_weighted, e1["sales_W1"])
assert np.isclose(r1.cashless_weighted, e1["cashless_rate_W1"]) and np.isclose(e1["sales_W1"], e1["sales_W2"])

R = pd.DataFrame([est(draw(rng)) for _ in range(2000)])
R.round(5).to_csv(RES / "reps.csv", index=False)
summ = {}
for v in ["sales", "cashless_rate"]:
    t = true[v]
    for mth in ["W0", "W1", "W2"]:
        x = R[f"{v}_{mth}"]
        summ[f"{v}_{mth}"] = {"mean": round(float(x.mean()), 4), "bias_pct": round(float((x.mean() / t - 1) * 100), 2),
                              "sd": round(float(x.std()), 4), "rmse": round(float(np.sqrt(((x - t) ** 2).mean())), 4)}
    for mth in ["W0", "W2"]:
        lo = R[f"{v}_{mth}"] - 1.96 * R[f"{v}_{mth}_se"]; hi = R[f"{v}_{mth}"] + 1.96 * R[f"{v}_{mth}_se"]
        summ[f"{v}_{mth}"]["coverage_pct"] = round(float(((lo <= t) & (t <= hi)).mean() * 100), 1)
out = {"stores": len(POP), "sample_size": len(S1), "true_sales": round(true["sales"], 2), "true_cashless": round(true["cashless_rate"], 4),
       "sample_share_large_pct": round(float((S1.size_class == "大").mean() * 100), 1), "pop_share_large_pct": 5.0,
       "one_sample": {"sales_W0": round(float(e1["sales_W0"]), 1), "sales_W1": round(float(e1["sales_W1"]), 1),
                      "cash_W0": round(float(e1["cashless_rate_W0"]), 4), "cash_W1": round(float(e1["cashless_rate_W1"]), 4)},
       "reps": 2000, "summary": summ}
json.dump(out, open(RES / "a653_main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame(summ).T.to_csv(RES / "summary.csv")

# 図1：構成の違い
fig, ax = plt.subplots(figsize=(8, 3.4))
popsh = POP.size_class.value_counts(normalize=True).reindex(SIZES) * 100
smpsh = S1.size_class.value_counts(normalize=True).reindex(SIZES) * 100
y = np.arange(2); left = np.zeros(2)
for k, col in zip(SIZES, [LIGHT, BLUE, ORANGE]):
    vals = np.array([popsh[k], smpsh[k]])
    ax.barh(y, vals, left=left, color=col, label=f"{k}の店")
    for i, v in enumerate(vals):
        if v > 4:
            ax.text(left[i] + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=9, color="white" if col != LIGHT else "black")
    left += vals
ax.set_yticks(y); ax.set_yticklabels(["2,000店すべて", "抜き出した120店"]); ax.set_xlabel("割合（%）")
ax.legend(frameon=False, fontsize=9, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0)); ax.invert_yaxis()
save(fig, "a653_composition.png", SRC)
# 図2：推定の分布（売上）
fig, ax = plt.subplots(figsize=(8, 3.8))
bins = np.linspace(R.sales_W1.min() * 0.9, R.sales_W0.max() * 1.05, 70)
ax.hist(R.sales_W0, bins=bins, color=ORANGE, alpha=0.75, label="重みなしの平均")
ax.hist(R.sales_W1, bins=bins, color=BLUE, alpha=0.75, label="抽出率の逆数で重み")
ax.axvline(true["sales"], color="black", lw=1.5, ls="--", label=f"本当の値 {true['sales']:.0f}万円")
ax.set_xlabel("1店あたりの月の売上の推定（万円）"); ax.set_ylabel("回数（2,000回中）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("重みを付けないと、大きい店に引っぱられて約2.9倍に出る")
save(fig, "a653_sales_dist.png", SRC)
# 図3：偏りと区間の当たり方
fig, axs = plt.subplots(1, 2, figsize=(9, 3.6))
labs = ["売上", "キャッシュレスの割合"]
b0 = [summ["sales_W0"]["bias_pct"], summ["cashless_rate_W0"]["bias_pct"]]; b1 = [summ["sales_W1"]["bias_pct"], summ["cashless_rate_W1"]["bias_pct"]]
x = np.arange(2)
axs[0].bar(x - 0.2, b0, 0.4, color=ORANGE, label="重みなし"); axs[0].bar(x + 0.2, b1, 0.4, color=BLUE, label="重みあり")
for i in range(2):
    axs[0].text(i - 0.2, b0[i], f"{b0[i]:+.0f}%", ha="center", va="bottom", fontsize=9); axs[0].text(i + 0.2, b1[i], f"{b1[i]:+.1f}%", ha="center", va="bottom", fontsize=9)
axs[0].set_xticks(x); axs[0].set_xticklabels(labs); axs[0].set_ylabel("本当の値とのずれ（%）"); axs[0].legend(frameon=False, fontsize=9); axs[0].set_title("偏り")
c0 = [summ["sales_W0"]["coverage_pct"], summ["cashless_rate_W0"]["coverage_pct"]]; c2 = [summ["sales_W2"]["coverage_pct"], summ["cashless_rate_W2"]["coverage_pct"]]
axs[1].bar(x - 0.2, c0, 0.4, color=ORANGE, label="重みなし＋ふつうの区間"); axs[1].bar(x + 0.2, c2, 0.4, color=BLUE, label="層別の区間")
axs[1].axhline(95, color=GRAY, ls="--", lw=1)
for i in range(2):
    axs[1].text(i - 0.2, c0[i] + 1, f"{c0[i]:.0f}%", ha="center", fontsize=9); axs[1].text(i + 0.2, c2[i] + 1, f"{c2[i]:.0f}%", ha="center", fontsize=9)
axs[1].set_xticks(x); axs[1].set_xticklabels(labs); axs[1].set_ylabel("95%区間が本当の値を含んだ割合（%）"); axs[1].set_ylim(0, 105)
axs[1].legend(frameon=False, fontsize=8); axs[1].set_title("区間の当たり方")
fig.tight_layout(); save(fig, "a653_bias_coverage.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
