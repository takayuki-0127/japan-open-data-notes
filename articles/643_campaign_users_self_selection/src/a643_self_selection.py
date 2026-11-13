"""643 キャンペーンを使った人と使わなかった人を比べると、効果が0でもどれだけ差が出るのか

架空の顧客2万人。前の6か月の購入額（prev_spend）が多い人ほどキャンペーンを使いやすく、翌月の購入額（next_spend）も
前の購入額で決まる。キャンペーンの本当の効果は 0円 と 500円 の2通り。比べ方は
  A 使った人と使わなかった人の単純な差
  B 前の購入額の十分位の中で比べて、使った人の数で重みをつけて平均（DuckDB の SQL でも計算して一致を確かめる）
  C 前の購入額を入れた回帰（使ったかどうかの係数）
  D 案内をくじで半分にだけ送った場合（送った群と送らない群の差を、使った割合で割る）
各200回。使いやすさが前の購入額にどれだけ左右されるか（選ばれ方の強さ）も変える。数字は置いた前提で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の顧客の購入額とキャンペーンの利用（作成者が乱数で作成、seed 643）"
DATA.mkdir(exist_ok=True)
rng = np.random.default_rng(643)
N, REPS = 20000, 200
SQLQ = (SQL / "02_compare_duckdb.sql").read_text(encoding="utf-8")


def draw(effect, sel=1.0, offer_half=False):
    prev = np.round(rng.lognormal(np.log(12000), 0.8, N), -1)
    z = (np.log(prev) - np.log(12000)) / 0.8
    offered = (rng.random(N) < 0.5) if offer_half else np.ones(N, bool)
    p_use = 1 / (1 + np.exp(-(-1.2 + sel * 1.2 * z)))
    used = offered & (rng.random(N) < p_use)
    base = 0.17 * prev * np.exp(rng.normal(0, 0.5, N))
    nxt = np.round(base + effect * used, 0)
    return pd.DataFrame({"customer_id": np.arange(1, N + 1), "prev_spend": prev, "offered": offered.astype(int),
                         "used": used.astype(int), "next_spend": nxt})


def estimates(df):
    u = df.used == 1
    a = df.next_spend[u].mean() - df.next_spend[~u].mean()
    dec = pd.qcut(df.prev_spend.rank(method="first"), 10, labels=False)
    g = df.assign(dec=dec).groupby("dec")
    diff = g.apply(lambda x: x.next_spend[x.used == 1].mean() - x.next_spend[x.used == 0].mean())
    b = float((diff * g.used.sum()).sum() / g.used.sum().sum())
    X = np.column_stack([np.ones(len(df)), df.used, np.log(df.prev_spend)])
    c = float(np.linalg.lstsq(X, df.next_spend, rcond=None)[0][1])
    return float(a), b, c


def rct(df):
    o = df.offered == 1
    itt = df.next_spend[o].mean() - df.next_spend[~o].mean()
    rate = df.used[o].mean()
    return float(itt / rate), float(itt), float(rate)


# 例の1回（効果0）を保存し、SQL と突き合わせる
ex = draw(0)
ex.to_csv(DATA / "customers.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("customers", ex)
sq = con.execute(SQLQ).fetchone()
ea, eb, ec = estimates(ex)
assert abs(sq[0] - ea) < 1e-6 and abs(sq[1] - eb) < 1e-6, (sq, ea, eb)
use_rate_ex = float(ex.used.mean())
prev_med = {"used": float(ex.prev_spend[ex.used == 1].median()), "not_used": float(ex.prev_spend[ex.used == 0].median())}

rows = []
for effect in [0, 500]:
    for r in range(REPS):
        a, b, c = estimates(draw(effect))
        d, itt, rate = rct(draw(effect, offer_half=True))
        rows.append({"effect": effect, "rep": r, "naive": a, "decile": b, "regression": c, "rct_wald": d, "rct_itt": itt, "rct_use_rate": rate})
D = pd.DataFrame(rows); D["rct_use_rate"] *= 100; D.to_csv(RES / "reps.csv", index=False, float_format="%.4f")
S = D.groupby("effect").agg(["mean", "std"]).round(1)
S.to_csv(RES / "summary.csv")
sel_rows = []
for sel in [0, 0.5, 1.0, 1.5]:
    for r in range(60):
        a, b, c = estimates(draw(0, sel=sel))
        sel_rows.append({"sel": sel, "naive": a, "decile": b, "regression": c})
SS = pd.DataFrame(sel_rows).groupby("sel").mean().round(1); SS.to_csv(RES / "by_selection.csv")
out = {"customers": N, "reps": REPS, "example": {"use_rate_pct": round(use_rate_ex * 100, 1), "naive": round(ea, 1), "decile": round(eb, 1),
       "regression": round(ec, 1), "sql_naive": round(float(sq[0]), 1), "sql_decile": round(float(sq[1]), 1),
       "prev_spend_median": prev_med, "next_spend_mean": round(float(ex.next_spend.mean()), 1)},
       "summary": {str(e): {k: {"mean": float(S.loc[e, (k, "mean")]), "sd": float(S.loc[e, (k, "std")])}
                            for k in ["naive", "decile", "regression", "rct_wald", "rct_itt", "rct_use_rate"]} for e in [0, 500]},
       "by_selection": SS.to_dict(orient="index")}
json.dump(out, open(RES / "a643_main.json", "w"), ensure_ascii=False, indent=1)

lab = {"naive": "使った人と使わなかった人の単純な差", "decile": "前の購入額の十分位の中で比べる", "regression": "前の購入額を入れた回帰", "rct_wald": "くじで半分に案内（差÷利用率）"}
ks = ["naive", "decile", "regression", "rct_wald"]
# 図1：本当の効果 0円・500円での推定（平均±標準偏差）
fig, ax = plt.subplots(1, 2, figsize=(11, 3.9), sharey=True, gridspec_kw={"wspace": 0.08})
for a_, e in zip(ax, [0, 500]):
    m = [S.loc[e, (k, "mean")] for k in ks]; s = [S.loc[e, (k, "std")] for k in ks]
    a_.barh([lab[k] for k in ks][::-1], m[::-1], xerr=s[::-1], color=[ORANGE, BLUE, BLUE, GREEN][::-1], capsize=3)
    for i, v in enumerate(m[::-1]):
        a_.text(max(v, 0) + 60, i + 0.25, f"{v:+,.0f}円", fontsize=8)
    a_.axvline(e, color=INK, ls="--", lw=1); a_.set_title(f"本当の効果 {e}円", fontsize=11); a_.set_xlabel("推定した効果（円、200回の平均±標準偏差）")
save(fig, "a643_estimates.png", SRC, y=-0.06)

# 図2：例の1回の、前の購入額の分布
fig, ax = plt.subplots(figsize=(8, 3.8))
bins = np.logspace(np.log10(1000), np.log10(200000), 40)
ax.hist(ex.prev_spend[ex.used == 0], bins=bins, color=GRAY, alpha=0.6, label=f"使わなかった人（中央値 {prev_med['not_used']:,.0f}円）")
ax.hist(ex.prev_spend[ex.used == 1], bins=bins, color=ORANGE, alpha=0.7, label=f"使った人（中央値 {prev_med['used']:,.0f}円）")
ax.set_xscale("log"); ax.set_xlabel("前の6か月の購入額（円、対数目盛）"); ax.set_ylabel("人数"); ax.legend(frameon=False, fontsize=9)
ax.set_title("使った人は、もともとよく買う人に偏っている（例の1回、効果0）")
save(fig, "a643_prev_spend.png", SRC)

# 図3：選ばれ方の強さと見かけの効果
fig, ax = plt.subplots(figsize=(8, 3.8))
for k, c in [("naive", ORANGE), ("decile", BLUE), ("regression", GREEN)]:
    ax.plot(SS.index, SS[k], marker="o", color=c, label=lab[k])
ax.axhline(0, color=INK, ls="--", lw=1); ax.set_xticks(SS.index)
ax.set_xticklabels(["0（無関係）", "0.5", "1（基準）", "1.5"]); ax.set_xlabel("前の購入額が使いやすさに効く強さ")
ax.set_ylabel("見かけの効果（円、本当は0）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("よく買う人ほど使うほど、単純な差は大きくなる（各60回の平均）")
save(fig, "a643_by_selection.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
