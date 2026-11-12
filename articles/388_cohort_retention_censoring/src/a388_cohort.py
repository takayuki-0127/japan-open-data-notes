"""388 登録月ごとの継続率の表で、まだ観測できていない月を0と数えると、どれだけ低く出るのか
架空の会員（2024年1月〜2025年12月に登録、2025年12月31日まで観測）。乱数の種は388。1か月＝30日として数える。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

START, CUT = np.datetime64("2024-01-01"), np.datetime64("2025-12-31")
MONTHS = pd.period_range("2024-01", "2025-12", freq="M"); K = 23; SHAPE = 0.6


def make(seed, growth=0.03, worse_2025=1.0, base=2000):
    """登録日と、本当の退会日（観測の終わりより後も含む）。退会までの日数はワイブル分布（最初ほど辞めやすい）"""
    r = np.random.default_rng(seed); rows = []
    lam = 365 / (-np.log(0.45)) ** (1 / SHAPE)             # 12か月（365日）後に45%が残る
    for i, m in enumerate(MONTHS):
        n = int(round(base * (1 + growth) ** i))
        day = r.integers(0, m.days_in_month, n)
        signup = np.datetime64(m.start_time.date()) + day.astype("timedelta64[D]")
        l = lam / (worse_2025 if m.year == 2025 else 1.0) ** (1 / SHAPE)   # worse_2025 倍、辞めやすい
        life = np.ceil(l * r.weibull(SHAPE, n)).astype(int)
        rows.append(pd.DataFrame({"登録月": str(m), "登録日": signup, "本当の退会日": signup + life.astype("timedelta64[D]")}))
    d = pd.concat(rows, ignore_index=True); d.insert(0, "会員ID", np.arange(1, len(d) + 1))
    d["退会日"] = d["本当の退会日"].where(d["本当の退会日"] <= CUT)       # 観測の終わりより後の退会は、まだ分からない（空欄）
    return d


def curves(d):
    """k か月後の継続率を、5つの数え方で出す"""
    sg = d["登録日"].to_numpy().astype("datetime64[D]"); out = []
    tr_days = (d["本当の退会日"].to_numpy().astype("datetime64[D]") - sg).astype(int)      # 本当の在籍日数
    event = d["退会日"].notna().to_numpy()                   # 観測の終わりまでに退会した
    obs_days = (CUT - sg).astype(int)                       # 観測できた日数
    life_obs = np.where(event, tr_days, obs_days)           # 観測できた在籍日数
    S = 1.0
    for k in range(1, K + 1):
        t = 30 * k; seen = obs_days >= t                    # k か月後まで観測できた会員
        alive_true = tr_days > t
        alive_obs = seen & (~event | (tr_days > t))
        # 積み上げ（カプラン・マイヤー）：k か月目の初めにいた人のうち、その月に辞めた割合
        at_risk = life_obs >= t - 30 if k > 1 else np.ones(len(d), bool)
        full = at_risk & (obs_days >= t)                    # その月を最後まで観測できた人だけ
        died = full & event & (life_obs <= t) & (life_obs > t - 30)
        S *= 1 - died.sum() / max(full.sum(), 1)
        out.append({"k": k, "本当の値": 100 * alive_true.mean(),
                    "①観測できていない分を0と数える": 100 * alive_obs.sum() / len(d),
                    "②退会日が空欄なら続いていると数える": 100 * (~event | (tr_days > t)).mean(),
                    "③kか月後まで観測できた会員だけで割る": 100 * alive_obs.sum() / max(seen.sum(), 1),
                    "④月ごとの継続率を掛け合わせる": 100 * S, "観測できた会員の割合%": 100 * seen.mean()})
    return pd.DataFrame(out)


d = make(388)
d.drop(columns="本当の退会日").to_csv(DATA / "members.csv", index=False)
cv = curves(d); cv.round(2).to_csv(RES / "retention_by_method.csv", index=False)

# ---- SQL（DuckDB）で登録月×経過月の表を作る ----
con = duckdb.connect(); con.execute("SET threads=1")
con.execute("CREATE TABLE members AS SELECT 会員ID, 登録月, CAST(登録日 AS DATE) AS 登録日, CAST(退会日 AS DATE) AS 退会日 FROM read_csv_auto(?)", [str(DATA / "members.csv")])
tab = con.execute((ROOT / "src" / "01_cohort_duckdb.sql").read_text(encoding="utf-8")).df()
tab.to_csv(RES / "cohort_table_sql.csv", index=False)
tot = tab.groupby("k")[["人数", "観測できた人数", "続いていた人数"]].sum()
assert np.allclose(100 * tot["続いていた人数"] / tot["人数"], cv["①観測できていない分を0と数える"])
assert np.allclose(100 * tot["続いていた人数"] / tot["観測できた人数"].clip(lower=1), cv["③kか月後まで観測できた会員だけで割る"])

# 登録月ごと：6か月後・12か月後の継続率（0で数える表と、本当の値）
tr_life = (d["本当の退会日"] - d["登録日"]).dt.days.to_numpy(); coh = []
for m, gidx in d.groupby("登録月").groups.items():
    row = {"登録月": m, "人数": len(gidx)}
    for k in (3, 6, 12):
        s = tab[(tab["登録月"] == m) & (tab["k"] == k)].iloc[0]
        row[f"{k}か月_0で数える%"] = round(100 * s["続いていた人数"] / s["人数"], 1)
        row[f"{k}か月_観測できた人だけ%"] = round(100 * s["続いていた人数"] / s["観測できた人数"], 1) if s["観測できた人数"] > 0 else np.nan
        row[f"{k}か月_本当の値%"] = round(100 * (tr_life[gidx] > 30 * k).mean(), 1)
    coh.append(row)
coh = pd.DataFrame(coh); coh.to_csv(RES / "by_signup_month.csv", index=False)

# ---- 会員の増え方を変える・新しい会員ほど辞めやすい場合 ----
sw = []
for g in (0.0, 0.03, 0.08):
    c = curves(make(3880 + int(g * 100), growth=g))
    for k in (3, 6, 12, 18):
        r = c[c.k == k].iloc[0]
        sw.append({"場面": f"登録が毎月{int(g*100)}%ずつ増える", "k": k, "本当の値%": round(r["本当の値"], 1),
                   "①との差": round(r["①観測できていない分を0と数える"] - r["本当の値"], 1),
                   "②との差": round(r["②退会日が空欄なら続いていると数える"] - r["本当の値"], 1),
                   "③との差": round(r["③kか月後まで観測できた会員だけで割る"] - r["本当の値"], 1),
                   "④との差": round(r["④月ごとの継続率を掛け合わせる"] - r["本当の値"], 1)})
c2 = curves(make(38899, worse_2025=1.5))
for k in (3, 6, 12, 18):
    r = c2[c2.k == k].iloc[0]
    sw.append({"場面": "2025年の登録者は1.5倍辞めやすい", "k": k, "本当の値%": round(r["本当の値"], 1),
               "①との差": round(r["①観測できていない分を0と数える"] - r["本当の値"], 1),
               "②との差": round(r["②退会日が空欄なら続いていると数える"] - r["本当の値"], 1),
               "③との差": round(r["③kか月後まで観測できた会員だけで割る"] - r["本当の値"], 1),
               "④との差": round(r["④月ごとの継続率を掛け合わせる"] - r["本当の値"], 1)})
sw = pd.DataFrame(sw); sw.to_csv(RES / "scenarios.csv", index=False)

# ---- 図 ----
SRC = "架空の会員データ（作成者が乱数で作成、seed 388）。2025年12月31日まで観測、1か月＝30日"
fig, ax = plt.subplots(figsize=(8.4, 4.8))
sty = {"本当の値": (INK, "-", 2.4), "①観測できていない分を0と数える": (ORANGE, "-", 2), "②退会日が空欄なら続いていると数える": (ORANGE, "--", 1.6),
       "③kか月後まで観測できた会員だけで割る": (BLUE, "-", 1.8), "④月ごとの継続率を掛け合わせる": (GREEN, ":", 2)}
for c, (col, ls, lw) in sty.items(): ax.plot(cv.k, cv[c], color=col, ls=ls, lw=lw, label=c)
ax.set_xlabel("登録からの月数"); ax.set_ylabel("継続率（%）"); ax.set_ylim(0, 100); ax.legend(fontsize=8.5, frameon=False)
ax.set_title("全体の継続率：数え方ごとの値と、本当の値")
save(fig, "a388_curves.png", SRC)

fig, axs = plt.subplots(1, 2, figsize=(11.5, 5.2), sharey=True)
P0 = tab[tab.k <= 12].assign(v=lambda t: 100 * t["続いていた人数"] / t["人数"]).pivot(index="登録月", columns="k", values="v")
P1 = tab[tab.k <= 12].assign(v=lambda t: np.where(t["観測できた人数"] == t["人数"], 100 * t["続いていた人数"] / t["人数"], np.nan)).pivot(index="登録月", columns="k", values="v")
for a, P, ttl in zip(axs, (P0, P1), ("観測できていない分を0と数えた表", "最後まで観測できた所だけを出した表")):
    a.imshow(P.to_numpy(), cmap="Blues", vmin=0, vmax=100, aspect="auto")
    for i in range(P.shape[0]):
        for j in range(P.shape[1]):
            v = P.iloc[i, j]
            if not np.isnan(v): a.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.5, color="white" if v > 55 else INK)
    a.set_xticks(range(12)); a.set_xticklabels(range(1, 13)); a.set_yticks(range(len(P))); a.set_yticklabels(P.index, fontsize=7)
    a.set_xlabel("登録からの月数"); a.set_title(ttl, fontsize=11)
fig.suptitle("登録月ごとの継続率（%）", y=1.0)
save(fig, "a388_cohort_tables.png", SRC)

fig, ax = plt.subplots(figsize=(8.4, 4.6))
for g, col in ((0.0, LIGHT), (0.03, BLUE), (0.08, ORANGE)):
    c = curves(make(3880 + int(g * 100), growth=g))
    ax.plot(c.k, c["①観測できていない分を0と数える"] - c["本当の値"], "o-", ms=3, color=col, label=f"登録が毎月{int(g*100)}%ずつ増える")
ax.axhline(0, color=INK, lw=0.8); ax.set_xlabel("登録からの月数"); ax.set_ylabel("本当の値との差（ポイント）")
ax.set_title("0と数えたときの低く出る幅：新しい会員が多いほど大きい"); ax.legend(fontsize=9, frameon=False)
save(fig, "a388_bias_by_growth.png", SRC)

r6, r12 = cv[cv.k == 6].iloc[0], cv[cv.k == 12].iloc[0]
main = {"会員数": len(d), "退会日が空欄の会員": int(d["退会日"].isna().sum()),
        "6か月": {c: round(float(r6[c]), 1) for c in cv.columns[1:]}, "12か月": {c: round(float(r12[c]), 1) for c in cv.columns[1:]},
        "duckdb": duckdb.__version__}
json.dump(main, open(RES / "a388_main.json", "w"), ensure_ascii=False, indent=1)
print(cv.round(1).to_string()); print(coh.to_string()); print(sw.to_string()); print(main)
