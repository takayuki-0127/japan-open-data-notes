"""413 途中で解約した契約に返す保険料は、日割りと短期率でどれだけ違うのか
架空の1年契約3万件と解約日。短期率の表は、説明のために作った架空のもの（実在の約款の表ではない）。乱数の種は413。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

rng = np.random.default_rng(413)
N = 30_000
# 説明用に作った架空の短期率（経過した期間 → すでに使ったとみなす割合 %）。実在の表ではない
SHORT = pd.DataFrame({"経過日数まで": [7, 15, 30, 61, 91, 122, 152, 183, 213, 244, 274, 305, 335, 365],
                      "短期率%": [10, 15, 25, 35, 45, 55, 65, 70, 75, 80, 85, 90, 95, 100]})
SHORT.to_csv(DATA / "short_rate_table_fictional.csv", index=False)


def make(kind):
    start = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, N), unit="D")
    prem = (np.round(np.exp(rng.normal(np.log(60_000), 0.5, N)) / 100) * 100).astype(int)        # 1年分の保険料（円）
    if kind == "一様":
        el = rng.integers(1, 365, N)                                   # 経過日数（1〜364日）
    elif kind == "契約の初めに集まる":
        el = np.clip(np.ceil(rng.exponential(60, N)), 1, 364).astype(int)
    else:                                                              # 満期の近くに集まる
        el = 365 - np.clip(np.ceil(rng.exponential(60, N)), 1, 364).astype(int)
    return pd.DataFrame({"契約ID": np.arange(1, N + 1), "始期": start, "年間保険料": prem, "経過日数": el,
                         "解約日": start + pd.to_timedelta(el, unit="D")})


def elapsed_months(start, cancel):
    """経過月数（1か月に満たない端数は切り上げ）。始期の応当日で数える"""
    m = (cancel.dt.year - start.dt.year) * 12 + (cancel.dt.month - start.dt.month)
    anniv = pd.DatetimeIndex([s + pd.DateOffset(months=int(k)) for s, k in zip(start, m)])
    m = m + (cancel.values > anniv.values)                             # 応当日を過ぎていれば、端数を切り上げ
    return np.clip(m, 1, 12).astype(int)


def refunds(d):
    p = d["年間保険料"].to_numpy(float); el = d["経過日数"].to_numpy()
    daily = np.floor(p * (365 - el) / 365)                             # 日割り（1円未満切り捨て）
    mon = elapsed_months(d["始期"], d["解約日"])
    monthly = np.floor(p * (12 - mon) / 12)                            # 月割り（経過月数は切り上げ）
    rate = SHORT["短期率%"].to_numpy()[np.searchsorted(SHORT["経過日数まで"].to_numpy(), el)]
    short = np.floor(p * (100 - rate) / 100)                           # 短期率
    return daily, monthly, short, mon


res, D = [], {}
for kind in ("一様", "契約の初めに集まる", "満期の近くに集まる"):
    d = make(kind); D[kind] = d
    daily, monthly, short, mon = refunds(d)
    d["返す額_日割り"], d["返す額_月割り"], d["返す額_短期率"], d["経過月数"] = daily.astype(int), monthly.astype(int), short.astype(int), mon
    tot = d["年間保険料"].sum()
    res.append({"解約の時期": kind, "年間保険料の合計": int(tot),
                "日割り_返す額": int(daily.sum()), "月割り_返す額": int(monthly.sum()), "短期率_返す額": int(short.sum()),
                "月割り_日割りとの差%": round(100 * (monthly.sum() / daily.sum() - 1), 2),
                "短期率_日割りとの差%": round(100 * (short.sum() / daily.sum() - 1), 2),
                "日割り_保険料に対する割合%": round(100 * daily.sum() / tot, 2),
                "月割り_保険料に対する割合%": round(100 * monthly.sum() / tot, 2),
                "短期率_保険料に対する割合%": round(100 * short.sum() / tot, 2),
                "短期率が日割りより多く返す契約の割合%": round(100 * float((short > daily).mean()), 2),
                "1件あたりの差の平均（短期率−日割り、円）": round(float((short - daily).mean()), 0)})
R = pd.DataFrame(res); R.to_csv(RES / "totals_by_scenario.csv", index=False)
D["一様"].assign(始期=D["一様"]["始期"].dt.date, 解約日=D["一様"]["解約日"].dt.date).to_csv(DATA / "cancellations_uniform.csv", index=False)

# 解約した月（経過月数）ごとの差
u = D["一様"]
bm = u.groupby("経過月数").agg(件数=("契約ID", "size"), 日割り=("返す額_日割り", "sum"), 月割り=("返す額_月割り", "sum"), 短期率=("返す額_短期率", "sum"))
bm["月割り_日割りとの差%"] = (100 * (bm["月割り"] / bm["日割り"] - 1)).round(1)
bm["短期率_日割りとの差%"] = (100 * (bm["短期率"] / bm["日割り"] - 1)).round(1)
bm.to_csv(RES / "by_elapsed_month.csv")

# 返す割合の曲線（保険料を1としたとき）。経過日数 1〜364、始期は 2025-01-01 として月割りを出す
el = np.arange(1, 365)
c = pd.DataFrame({"契約ID": el, "始期": pd.Timestamp("2025-01-01"), "年間保険料": 1_000_000, "経過日数": el})
c["解約日"] = c["始期"] + pd.to_timedelta(el, unit="D")
cd, cm, cs, _ = refunds(c)
curve = pd.DataFrame({"経過日数": el, "日割り": cd / 1e6, "月割り": cm / 1e6, "短期率": cs / 1e6}); curve.to_csv(RES / "refund_curve.csv", index=False)
gap_max = {"月割り": float((curve["日割り"] - curve["月割り"]).max()), "短期率": float((curve["日割り"] - curve["短期率"]).max()),
           "短期率が最も離れる経過日数": int(curve["経過日数"][(curve["日割り"] - curve["短期率"]).idxmax()])}

# 解約の時期の平均（経過日数の平均）を動かす
sw = []
for mean in (20, 40, 60, 90, 120, 180):
    r = np.random.default_rng(4130 + mean)
    d = pd.DataFrame({"契約ID": np.arange(N), "始期": pd.Timestamp("2025-01-01") + pd.to_timedelta(r.integers(0, 365, N), unit="D"),
                      "年間保険料": (np.round(np.exp(r.normal(np.log(60_000), 0.5, N)) / 100) * 100).astype(int),
                      "経過日数": np.clip(np.ceil(r.exponential(mean, N)), 1, 364).astype(int)})
    d["解約日"] = d["始期"] + pd.to_timedelta(d["経過日数"], unit="D")
    a, b, s, _ = refunds(d)
    sw.append({"経過日数の平均（置いた値）": mean, "経過日数の平均（実際）": round(float(d["経過日数"].mean()), 1),
               "月割り_日割りとの差%": round(100 * (b.sum() / a.sum() - 1), 2), "短期率_日割りとの差%": round(100 * (s.sum() / a.sum() - 1), 2)})
SW = pd.DataFrame(sw); SW.to_csv(RES / "sweep_cancel_timing.csv", index=False)

# 短期率の表の形を動かす：使ったとみなす割合 ＝（経過日数÷365）の a 乗。a=1 は日割りと同じ、a が小さいほど早い解約に厳しい
sh = []
pu, eu = u["年間保険料"].to_numpy(float), u["経過日数"].to_numpy()
for a in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5):
    s_ = np.floor(pu * (1 - (eu / 365) ** a))
    sh.append({"a": a, "30日で使ったとみなす割合%": round(100 * (30 / 365) ** a, 1), "183日で使ったとみなす割合%": round(100 * (183 / 365) ** a, 1),
               "日割りとの差%（解約が一様）": round(100 * (s_.sum() / u["返す額_日割り"].sum() - 1), 2)})
SH = pd.DataFrame(sh); SH.to_csv(RES / "sweep_table_shape.csv", index=False)

# ---------------- SQL（DuckDB）で同じ額を出して、Python と比べる ----------------
db = duckdb.connect(); db.execute("SET threads=1")
db.register("c", u[["契約ID", "始期", "解約日", "年間保険料"]]); db.register("t", SHORT.rename(columns={"経過日数まで": "upto", "短期率%": "rate"}))
q = db.execute("""
WITH a AS (
  SELECT 契約ID, 年間保険料 AS p, date_diff('day', 始期, 解約日) AS el,
         date_diff('month', 始期, 解約日)
         + CASE WHEN 解約日 > 始期 + to_months(CAST(date_diff('month', 始期, 解約日) AS INTEGER)) THEN 1 ELSE 0 END AS mon0
  FROM c),
b AS (SELECT *, LEAST(GREATEST(mon0, 1), 12) AS mon,
             (SELECT MIN(rate) FROM t WHERE t.upto >= a.el) AS rate FROM a)
SELECT 契約ID,
       CAST(floor(p * (365 - el) / 365.0) AS BIGINT)   AS daily,
       CAST(floor(p * (12 - mon) / 12.0) AS BIGINT)    AS monthly,
       CAST(floor(p * (100 - rate) / 100.0) AS BIGINT) AS short
FROM b ORDER BY 契約ID""").df()
sql_ok = {"日割り": bool((q.daily.values == u["返す額_日割り"].values).all()), "月割り": bool((q.monthly.values == u["返す額_月割り"].values).all()),
          "短期率": bool((q.short.values == u["返す額_短期率"].values).all())}
assert all(sql_ok.values()), sql_ok
pd.DataFrame([sql_ok]).to_csv(RES / "sql_check_duckdb.csv", index=False)

main = {"契約の数": N, "短期率の表": "説明用に作った架空の表（実在の約款の表ではない）", "解約の時期ごとの合計": R.to_dict("records"),
        "経過月数ごと（一様）": bm.reset_index().to_dict("records"), "返す割合の差の最大（保険料に対して）": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in gap_max.items()},
        "解約の時期を動かす": SW.to_dict("records"), "短期率の表の形を動かす": SH.to_dict("records"), "SQLとPythonの一致": sql_ok}
json.dump(main, open(RES / "a413_main.json", "w"), ensure_ascii=False, indent=1, default=int)

# ---------------- 図 ----------------
SRC = "架空の1年契約3万件（作成者が乱数で作成、seed 413）。短期率は説明用に作った架空の表"
fig, ax = plt.subplots(figsize=(9.5, 4.2))
ax.plot(curve["経過日数"], 100 * curve["日割り"], color=GRAY, label="日割り")
ax.step(curve["経過日数"], 100 * curve["月割り"], where="post", color=BLUE, label="月割り（経過月数は切り上げ）")
ax.step(curve["経過日数"], 100 * curve["短期率"], where="post", color=ORANGE, label="短期率（架空の表）")
ax.set_xlabel("始期から解約までの日数"); ax.set_ylabel("返す額（年間保険料に対する%）"); ax.set_xlim(0, 365); ax.set_ylim(0, 100)
ax.set_title("解約までの日数と、返す額の割合"); ax.legend(frameon=False)
save(fig, "a413_refund_curve.png", SRC)

fig, ax = plt.subplots(figsize=(9.5, 4.2))
kinds = list(R["解約の時期"]); x = np.arange(len(kinds)); w = 0.26
for i, (k, col) in enumerate((("日割り", GRAY), ("月割り", BLUE), ("短期率", ORANGE))):
    v = R[f"{k}_保険料に対する割合%"].to_numpy()
    b = ax.bar(x + (i - 1) * w, v, w, color=col, label=k)
    for r, y in zip(b, v): ax.text(r.get_x() + r.get_width() / 2, y, f"{y:.1f}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"解約が{k}" if k != "一様" else "解約が一様" for k in kinds]); ax.set_ylabel("返す額の合計（年間保険料の合計に対する%）")
ax.set_title("3万件の合計：返す額は、解約の時期と決め方で変わる"); ax.legend(frameon=False)
save(fig, "a413_totals.png", SRC)

fig, ax = plt.subplots(figsize=(9.5, 4.2))
x = bm.index.to_numpy(); w = 0.4
ax.bar(x - w / 2, bm["月割り_日割りとの差%"], w, color=BLUE, label="月割り")
ax.bar(x + w / 2, bm["短期率_日割りとの差%"], w, color=ORANGE, label="短期率（架空の表）")
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xlabel("解約までの経過月数（端数は切り上げ）"); ax.set_ylabel("日割りとの差（%）")
ax.set_title("解約した月ごとの、返す額の日割りとの差（解約が一様な場合）"); ax.legend(frameon=False)
save(fig, "a413_by_month.png", SRC)
print(SH.to_string()); print(R.to_string()); print(bm.to_string()); print(SW.to_string()); print(gap_max)
