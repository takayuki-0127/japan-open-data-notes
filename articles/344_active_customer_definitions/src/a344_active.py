"""344 「アクティブな顧客」は、定義でどれだけ人数が変わるのか（架空の購買・ログインの記録・seed 344）"""
import numpy as np, pandas as pd, duckdb, json
import matplotlib.pyplot as plt
from common import *
rng = np.random.default_rng(344)
START, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")
days = pd.date_range(START, END, freq="D"); ND = len(days)
# ---- 架空の顧客：入会日・やめる日・買う頻度・ログインの頻度
N = 30000
join = rng.integers(-400, ND, N)                               # 期間の前から少しずつ入会
life = rng.exponential(420, N).astype(int) + 14                # 入会からやめるまでの日数
rate_buy = rng.gamma(0.7, 1 / 0.7, N) * 0.022                  # 1日あたりの買う確率（人によって大きく違う）
rate_log = rate_buy * rng.uniform(2, 8, N) + 0.01              # ログインは買い物より多い
dow = np.array([1.0, 0.9, 0.9, 0.95, 1.1, 1.35, 1.3])          # 曜日
season = 1 + 0.25 * np.isin(days.month, [12]) + 0.12 * np.isin(days.month, [3, 7]) - 0.12 * np.isin(days.month, [2, 6])
camp = np.ones(ND); camp[(days >= "2025-05-10") & (days <= "2025-05-25")] = 1.8      # セール（買い物が増える）
push = np.ones(ND); push[(days >= "2024-10-01") & (days <= "2024-10-31")] = 1.5      # お知らせの強化（ログインだけ増える）
daymul_buy = dow[days.dayofweek] * season * camp
daymul_log = dow[days.dayofweek] * push
buys, logs = [], []
for t in range(ND):
    alive = (join <= t) & (t < join + life)
    idx = np.nonzero(alive)[0]
    b = idx[rng.random(len(idx)) < np.minimum(rate_buy[idx] * daymul_buy[t], 0.9)]
    l = idx[rng.random(len(idx)) < np.minimum(rate_log[idx] * daymul_log[t], 0.95)]
    buys.append(pd.DataFrame({"cust": b, "d": days[t]})); logs.append(pd.DataFrame({"cust": np.union1d(l, b), "d": days[t]}))
buy = pd.concat(buys, ignore_index=True); log = pd.concat(logs, ignore_index=True)
con = duckdb.connect(); con.register("buy", buy); con.register("login", log)
con.execute("CREATE TABLE me AS SELECT CAST(d AS DATE) AS me FROM (SELECT unnest(generate_series(DATE '2024-03-31', DATE '2025-12-31', INTERVAL 1 DAY)) AS d) WHERE month(d + INTERVAL 1 DAY) <> month(d)")
# ---- 5つの定義（月末の時点）。T-SQL でも同じ形（sql/ に置いた版は未検証）
SQL = """
SELECT me.me,
  (SELECT COUNT(DISTINCT cust) FROM buy   WHERE d >  me.me - INTERVAL 30 DAY AND d <= me.me) AS d1_buy30,
  (SELECT COUNT(DISTINCT cust) FROM buy   WHERE d >  me.me - INTERVAL 90 DAY AND d <= me.me) AS d2_buy90,
  (SELECT COUNT(DISTINCT cust) FROM buy   WHERE d >= date_trunc('month', me.me) AND d <= me.me) AS d3_buy_month,
  (SELECT COUNT(DISTINCT cust) FROM login WHERE d >  me.me - INTERVAL 30 DAY AND d <= me.me) AS d4_login30,
  (SELECT COUNT(*) FROM (SELECT cust FROM buy WHERE d > me.me - INTERVAL 90 DAY AND d <= me.me GROUP BY cust HAVING COUNT(*) >= 2)) AS d5_buy90_twice
FROM me ORDER BY me.me"""
A = con.execute(SQL).df(); A["me"] = pd.to_datetime(A.me)
# pandas で別に計算して照合（1つの月・2つの定義）
t0 = pd.Timestamp("2025-02-28")
assert buy[(buy.d > t0 - pd.Timedelta(days=30)) & (buy.d <= t0)].cust.nunique() == int(A.loc[A.me == t0, "d1_buy30"].iloc[0])
assert buy[(buy.d >= "2025-02-01") & (buy.d <= t0)].cust.nunique() == int(A.loc[A.me == t0, "d3_buy_month"].iloc[0])
DEF = {"d1_buy30": "過去30日に購入", "d2_buy90": "過去90日に購入", "d3_buy_month": "その月に購入", "d4_login30": "過去30日にログイン", "d5_buy90_twice": "過去90日に2回以上購入"}
cols = list(DEF)
A.to_csv(RES / "active_by_definition.csv", index=False)
M = A.set_index("me")[cols]; mom = M.pct_change().iloc[1:]
sign = np.sign(mom)
split = (sign.max(axis=1) != sign.min(axis=1))
pair = pd.DataFrame(index=cols, columns=cols, dtype=float)
for a in cols:
    for b in cols: pair.loc[a, b] = int((sign[a] != sign[b]).sum())
pair.to_csv(RES / "pairwise_sign_disagreement.csv")
mom.round(5).to_csv(RES / "mom_change.csv")
ratio = M.max(axis=1) / M.min(axis=1)
yoy = (M.iloc[12:].values / M.iloc[:-12].values - 1)
yoy = pd.DataFrame(yoy, index=M.index[12:], columns=cols); ysign = np.sign(yoy); ysplit = (ysign.max(axis=1) != ysign.min(axis=1))
feb = mom.loc[mom.index.month == 2, ["d1_buy30", "d3_buy_month"]]
main = {"n_customers": N, "n_purchases": int(len(buy)), "n_logins": int(len(log)), "months": int(len(M)),
        "count_dec2025": {DEF[c]: int(M[c].iloc[-1]) for c in cols},
        "ratio_max_over_min": {"mean": round(float(ratio.mean()), 2), "min": round(float(ratio.min()), 2), "max": round(float(ratio.max()), 2)},
        "ratio_vs_buy30_mean": {DEF[c]: round(float((M[c] / M.d1_buy30).mean()), 3) for c in cols},
        "mom_months": int(len(mom)), "mom_months_direction_split": int(split.sum()),
        "mom_split_months": [d.strftime("%Y-%m") for d in mom.index[split]],
        "pair_disagree_buy30_vs": {DEF[c]: int(pair.loc["d1_buy30", c]) for c in cols[1:]},
        "yoy_months": int(len(yoy)), "yoy_months_direction_split": int(ysplit.sum()),
        "feb_mom": {d.strftime("%Y-%m"): {DEF[c]: round(float(v), 4) for c, v in r.items()} for d, r in feb.iterrows()},
        "oct2024_mom": {DEF[c]: round(float(mom.loc["2024-10-31", c]), 4) for c in cols},
        "may2025_mom": {DEF[c]: round(float(mom.loc["2025-05-31", c]), 4) for c in cols},
        "jun2025_mom": {DEF[c]: round(float(mom.loc["2025-06-30", c]), 4) for c in cols},
        "mom_sd_pct": {DEF[c]: round(float(mom[c].std() * 100), 2) for c in cols}}
json.dump(main, open(RES / "a344_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1))
SRC = "架空の購買・ログインの記録（乱数で作成、seed 344）。月末の時点で数えた"
COL = [BLUE, GREEN, ORANGE, GRAY, INK]
fig, ax = plt.subplots(figsize=(8.4, 4.6))
for c, col in zip(cols, COL): ax.plot(M.index, M[c] / 1000, "-o", ms=3, color=col, lw=1.8, label=DEF[c])
ax.set_ylabel("アクティブな顧客（千人）"); ax.set_ylim(0); ax.set_title("同じ記録から数えた「アクティブな顧客」：定義で人数は何倍も違う"); ax.legend(frameon=False, fontsize=9, ncol=2)
save(fig, "a344_series.png", SRC)
fig, ax = plt.subplots(figsize=(9, 3.6))
img = sign[cols].T.values; ax.imshow(img, cmap="RdBu", vmin=-1.6, vmax=1.6, aspect="auto")
ax.set_yticks(range(5)); ax.set_yticklabels([DEF[c] for c in cols], fontsize=9)
ax.set_xticks(range(len(mom))); ax.set_xticklabels([d.strftime("%y/%m") for d in mom.index], rotation=90, fontsize=8)
for j, s_ in enumerate(split.values):
    if s_: ax.text(j, -0.62, "▼", ha="center", fontsize=8, color=ORANGE)
for i in range(5):
    for j in range(len(mom)): ax.text(j, i, "＋" if img[i, j] > 0 else ("−" if img[i, j] < 0 else "0"), ha="center", va="center", fontsize=8, color="white" if img[i, j] != 0 else INK)
ax.set_title(f"前月より増えたか減ったか（青＝増、赤＝減）。▼は定義で向きが割れた月：{int(split.sum())}／{len(mom)}か月", fontsize=11, pad=16)
for s_ in ax.spines.values(): s_.set_visible(False)
save(fig, "a344_direction.png", SRC, y=-0.08)
fig, ax = plt.subplots(figsize=(7.6, 4)); x = np.arange(5); w = 0.26
for j, (k, lab, col) in enumerate([("oct2024_mom", "2024年10月（お知らせを強化）", GRAY), ("may2025_mom", "2025年5月（セール）", BLUE), ("jun2025_mom", "2025年6月（セールの翌月）", ORANGE)]):
    v = [main[k][DEF[c]] * 100 for c in cols]; ax.bar(x + (j - 1) * w, v, w, color=col, label=lab)
ax.axhline(0, color=INK, lw=0.6); ax.set_xticks(x); ax.set_xticklabels([DEF[c].replace("に", "に\n", 1) for c in cols], fontsize=8.5)
ax.set_ylabel("前月比（%）"); ax.set_title("同じ出来事が、定義によって違う大きさ・違う月に出る"); ax.legend(frameon=False, fontsize=9)
save(fig, "a344_events.png", SRC)
