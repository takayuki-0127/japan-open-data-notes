"""596 小さい契約群の実績を全体の平均とどう混ぜるか：Bühlmann–Straub のクレジビリティ（seed 596）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(596)
SRC = "架空のデータ（作成者が乱数で作成、seed 596）"
G, YEARS, MU, REPS = 300, 3, 0.05, 400          # 300群・過去3年・平均の事故率5%・各400回
BANDS = [(0, 100, "100件未満"), (100, 500, "100〜500件"), (500, 2000, "500〜2,000件"), (2000, 1e9, "2,000件以上")]
METH = {"own": "自分の実績だけ", "all": "全体の平均だけ", "cred": "クレジビリティ（推定した k）"}


def make(cv):
    """群ごとの契約件数（毎年少しずつ変わる）と、本当の事故率、過去3年と翌年の事故件数"""
    n0 = np.round(np.exp(rng.uniform(np.log(20), np.log(5000), G)))
    w = np.maximum(1, np.round(n0[:, None] * rng.uniform(0.9, 1.1, (G, YEARS + 1)))).astype(int)
    theta = np.full(G, MU) if cv == 0 else rng.gamma(1 / cv ** 2, MU * cv ** 2, G)
    y = rng.poisson(w * theta[:, None])
    return w, theta, y


def buhlmann_straub(w, y):
    """Bühlmann–Straub の推定。s2：群の中の年ごとの揺れ、a：群どうしの本当の差、k = s2 / a"""
    x = y / w
    wi = w.sum(1); xi = y.sum(1) / wi; W = wi.sum(); xbar = (wi * xi).sum() / W
    s2 = (w * (x - xi[:, None]) ** 2).sum() / (len(wi) * (w.shape[1] - 1))
    a = ((wi * (xi - xbar) ** 2).sum() - (len(wi) - 1) * s2) / (W - (wi ** 2).sum() / W)
    a = max(a, 1e-12)
    k = s2 / a; z = wi / (wi + k)
    mu_hat = (z * xi).sum() / z.sum()
    return dict(xi=xi, z=z, k=k, s2=s2, a=a, mu=mu_hat, pred=z * xi + (1 - z) * mu_hat, wi=wi, xbar=xbar)


def one(cv):
    w, theta, y = make(cv)
    past_w, past_y = w[:, :YEARS], y[:, :YEARS]
    b = buhlmann_straub(past_w, past_y)
    k_true = MU / (MU * cv) ** 2 if cv > 0 else np.inf          # ポアソンなら s2 = 平均、a = 分散
    z_true = b["wi"] / (b["wi"] + k_true); oracle = z_true * b["xi"] + (1 - z_true) * MU
    pred = {"own": b["xi"], "all": np.full(G, b["xbar"]), "cred": b["pred"], "oracle": oracle}
    nxt = y[:, YEARS] / w[:, YEARS]
    out = {"k_hat": b["k"], "k_true": k_true}
    for m, p in pred.items():
        e_true = (p - theta) ** 2; e_next = (p - nxt) ** 2
        out[m + "_rmse_true"] = np.sqrt(e_true.mean()); out[m + "_rmse_next"] = np.sqrt(e_next.mean())
        for lo, hi, lab in BANDS:
            s = (b["wi"] / YEARS >= lo) & (b["wi"] / YEARS < hi)
            out[f"{m}_rmse_true_{lab}"] = np.sqrt(e_true[s].mean())
    for lo, hi, lab in BANDS:
        s = (b["wi"] / YEARS >= lo) & (b["wi"] / YEARS < hi)
        out[f"z_{lab}"] = b["z"][s].mean()
    return out


rows = []
for cv in [0.0, 0.15, 0.3, 0.6]:
    for r in range(REPS):
        rows.append({"cv": cv, "rep": r, **one(cv)})
sim = pd.DataFrame(rows).replace([np.inf], np.nan)
sim.to_csv(RES / "simulation.csv", index=False)
summ = sim.groupby("cv").mean(numeric_only=True).drop(columns="rep").reset_index()
summ["k_hat_median"] = sim.groupby("cv").k_hat.median().values
summ.round(6).to_csv(RES / "summary.csv", index=False)

# 例の1回（cv=0.3）：データを書き出し、SQL（DuckDB）でも同じ推定をして突き合わせる
w, theta, y = make(0.3)
ex = pd.DataFrame([{"group_id": f"G{i:03d}", "year": 2023 + j, "policies": int(w[i, j]), "claims": int(y[i, j])}
                   for i in range(G) for j in range(YEARS)])
ex.to_csv(DATA / "example_groups.csv", index=False)
b = buhlmann_straub(w[:, :YEARS], y[:, :YEARS])
con = duckdb.connect(); con.execute("SET threads TO 1"); con.register("claims_by_year", ex)
sq = con.execute(open(SQL / "02_credibility_duckdb.sql").read()).df().sort_values("group_id").reset_index(drop=True)
diff = float(np.abs(sq.credibility_rate.values - b["pred"]).max())
pd.DataFrame([{"k_python": b["k"], "k_duckdb": float(sq.k.iloc[0]), "s2": b["s2"], "a": b["a"],
               "max_abs_diff_rate": diff, "match": diff < 1e-9,
               "z_at_100": 100 * YEARS / (100 * YEARS + b["k"]), "z_at_1000": 1000 * YEARS / (1000 * YEARS + b["k"])}]
             ).to_csv(RES / "sql_example.csv", index=False)

# 図1 群の大きさとクレジビリティの重み Z（例の1回）
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.scatter(b["wi"] / YEARS, b["z"], s=12, color=BLUE, alpha=0.7, label="各群の Z（推定した k）")
xs = np.exp(np.linspace(np.log(15), np.log(5500), 200))
ax.plot(xs, xs * YEARS / (xs * YEARS + b["k"]), color=INK, lw=1, label=f"Z = 3年の件数 ÷ (3年の件数 + k)、k = {b['k']:,.0f}件")
ax.set_xscale("log"); ax.set_ylim(0, 1); ax.set_xlabel("群の1年あたりの契約件数（対数目盛、過去3年の重みは3倍）")
ax.set_ylabel("自分の実績にかける重み Z"); ax.grid(alpha=0.3); ax.legend(fontsize=9, loc="upper left")
ax.set_title("小さい群ほど、全体の平均に寄せる（本当の事故率のばらつき CV 0.3）")
save(fig, "a596_weight.png", "出典：" + SRC)

# 図2 大きさの帯ごとの誤差（cv=0.3）
g = summ[summ.cv == 0.3].iloc[0]
fig, ax = plt.subplots(figsize=(9.5, 4.6)); xx = np.arange(len(BANDS))
for j, (m, c) in enumerate(zip(METH, [GRAY, ORANGE, GREEN])):
    v = [g[f"{m}_rmse_true_{lab}"] * 100 for *_, lab in BANDS]
    bars = ax.bar(xx + (j - 1) * 0.26, v, 0.26, color=c, label=METH[m])
    for b_, vv in zip(bars, v): ax.text(b_.get_x() + b_.get_width() / 2, vv + 0.03, f"{vv:.2f}", ha="center", fontsize=8)
ax.set_xticks(xx); ax.set_xticklabels([lab for *_, lab in BANDS]); ax.set_xlabel("群の1年あたりの契約件数")
ax.set_ylabel("本当の事故率との誤差（RMSE、ポイント）"); ax.grid(axis="y", alpha=0.3); ax.legend(fontsize=9)
ax.set_title("群の大きさごとの予測の誤差（本当の事故率のばらつき CV 0.3、400回の平均）")
save(fig, "a596_error_by_size.png", "出典：" + SRC + "。本当の事故率は平均5%")

# 図3 群どうしの差の大きさを変えると
fig, ax = plt.subplots(figsize=(9.5, 4.6)); xx = np.arange(4)
for j, (m, c) in enumerate(zip(METH, [GRAY, ORANGE, GREEN])):
    v = [summ[summ.cv == cv].iloc[0][m + "_rmse_true"] * 100 for cv in [0.0, 0.15, 0.3, 0.6]]
    bars = ax.bar(xx + (j - 1) * 0.26, v, 0.26, color=c, label=METH[m])
    for b_, vv in zip(bars, v): ax.text(b_.get_x() + b_.get_width() / 2, vv + 0.03, f"{vv:.2f}", ha="center", fontsize=8)
ax.set_xticks(xx); ax.set_xticklabels(["差なし（CV 0）", "小さい（CV 0.15）", "中くらい（CV 0.3）", "大きい（CV 0.6）"])
ax.set_xlabel("群どうしの本当の事故率の差"); ax.set_ylabel("全300群の誤差（RMSE、ポイント）")
ax.grid(axis="y", alpha=0.3); ax.legend(fontsize=9); ax.set_title("差が大きいほど自分の実績に寄り、差がないほど全体の平均に寄る")
save(fig, "a596_error_by_cv.png", "出典：" + SRC)

json.dump({"summary": summ.round(6).to_dict("records"), "sql": pd.read_csv(RES / "sql_example.csv").to_dict("records")},
          open(RES / "a596_main.json", "w"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 250); print(summ.T.to_string()); print(pd.read_csv(RES / "sql_example.csv").T.to_string())
