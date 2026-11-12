"""358 売上が0の日が表にないと、1日あたりの平均はどれだけ高く出るのか（架空の店別・日次売上）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import SQL, RES, save, BLUE, ORANGE, GRAY, GREEN, INK, LIGHT

SEED = 358
SRC = "架空の店別・日次売上（作成者が乱数で作成、seed 358）"
rng = np.random.default_rng(SEED)
days = pd.date_range("2024-01-01", "2025-12-31")
dow = days.dayofweek.values
WK = np.array([0.9, 0.9, 0.95, 1.0, 1.1, 1.3, 1.2])     # 曜日ごとの客の入り

# ---------- 店：大20・中40・小60。小さい店には定休日がある ----------
stores = []
for i in range(120):
    size = "大" if i < 20 else "中" if i < 60 else "小"
    lam = {"大": rng.uniform(250, 500), "中": rng.uniform(30, 90), "小": rng.uniform(0.4, 4.0)}[size]   # 1日の会計の件数の平均
    closed = int(rng.integers(0, 7)) if (size == "小" or (size == "中" and rng.random() < 0.5)) else -1   # 定休日の曜日（-1＝なし）
    stores.append({"store_id": i + 1, "size": size, "lam": lam, "closed_dow": closed, "ticket": rng.uniform(1500, 4000)})
stores = pd.DataFrame(stores)

rec, opn = [], []
for s in stores.itertuples():
    is_open = dow != s.closed_dow
    n = rng.poisson(s.lam * WK[dow]) * is_open
    # 1日の売上＝会計の件数ぶんの金額の合計（1件の金額は対数正規）
    amt = np.array([rng.lognormal(np.log(s.ticket) - 0.125, 0.5, k).sum() if k > 0 else 0.0 for k in n]).round()
    opn.append(pd.DataFrame({"store_id": s.store_id, "d": days[is_open]}))
    has = n > 0
    rec.append(pd.DataFrame({"store_id": s.store_id, "d": days[has], "amount": amt[has]}))
sales = pd.concat(rec, ignore_index=True)                  # 売上のあった日だけ行がある
store_days = pd.concat(opn, ignore_index=True)             # 開いていた日

# ---------- ① 1日あたりの売上：3通り ----------
con = duckdb.connect(); con.execute("SET threads=1")
con.register("s_df", sales); con.register("o_df", store_days)
con.execute("CREATE TABLE sales AS SELECT store_id, CAST(d AS DATE) d, amount FROM s_df")
con.execute("CREATE TABLE store_days AS SELECT store_id, CAST(d AS DATE) d FROM o_df")
res = con.execute((SQL / "01_avg_daily_duckdb.sql").read_text(encoding="utf-8")).df()

# pandas で別に計算して確かめる
tot = sales.groupby("store_id")["amount"].sum()
n_rows = sales.groupby("store_id").size()
n_open = store_days.groupby("store_id").size()
ref = pd.DataFrame({"avg_a": tot / n_rows, "avg_b": tot / len(days), "avg_c": tot / n_open}).reset_index()
assert np.allclose(res[["avg_a", "avg_b", "avg_c"]].values, ref[["avg_a", "avg_b", "avg_c"]].values)

st = stores.merge(res, on="store_id")
st["zero_share"] = (1 - n_rows.values / n_open.values) * 100          # 開いていたのに売上0だった日の割合
st["closed_share"] = (1 - n_open.values / len(days)) * 100
st["err_a"] = (st["avg_a"] / st["avg_c"] - 1) * 100
st["err_b"] = (st["avg_b"] / st["avg_c"] - 1) * 100
st.round(3).to_csv(RES / "store_level.csv", index=False)
by = st.groupby("size", sort=False).agg(店数=("store_id", "size"), 売上0の日の割合=("zero_share", "mean"), 定休日の割合=("closed_share", "mean"),
                                         A_平均=("err_a", "mean"), A_中央値=("err_a", "median"), A_最大=("err_a", "max"), B_平均=("err_b", "mean"), B_最小=("err_b", "min")).reset_index()
by.round(2).to_csv(RES / "error_by_size.csv", index=False)

# 「店の平均日販の平均」（1店あたり）で見たとき
chain = {k: float(st[c].mean()) for k, c in [("A", "avg_a"), ("B", "avg_b"), ("C", "avg_c")]}
small = st[st["size"] == "小"]
chain_small = {k: float(small[c].mean()) for k, c in [("A", "avg_a"), ("B", "avg_b"), ("C", "avg_c")]}
over10 = int((st["err_a"] >= 10).sum())

# ---------- ② 会計の件数の平均ごとの高く出る幅（理屈：1/(1−e^−λ) − 1） ----------
sw = []
for lam in [0.25, 0.5, 1, 1.5, 2, 3, 4, 6, 8]:
    r = np.random.default_rng([SEED, int(lam * 100)])
    k = r.poisson(lam, 200_000)
    amt = np.array([r.lognormal(np.log(2500) - 0.125, 0.5, x).sum() if x else 0.0 for x in k])
    sw.append({"lam": lam, "zero_share": (k == 0).mean() * 100, "sim": (amt[k > 0].mean() / amt.mean() - 1) * 100,
               "theory": (1 / (1 - np.exp(-lam)) - 1) * 100})
sw = pd.DataFrame(sw); sw.round(3).to_csv(RES / "overestimate_by_traffic.csv", index=False)

# ---------- ③ 7日の移動平均と前の日との差 ----------
full = store_days.merge(sales, on=["store_id", "d"], how="left").fillna({"amount": 0.0}).sort_values(["store_id", "d"])
full["ma7_cal"] = full.groupby("store_id")["amount"].transform(lambda s: s.rolling(7).mean())          # 開いていた7日
od = store_days.sort_values(["store_id", "d"]).copy()
od["ord"] = od.groupby("store_id").cumcount()                                                         # 開いていた日の通し番号
srt = sales.sort_values(["store_id", "d"]).merge(od, on=["store_id", "d"])
srt["ma7_rows"] = srt.groupby("store_id")["amount"].transform(lambda s: s.rolling(7).mean())           # 行で7つ
srt["span"] = srt.groupby("store_id")["ord"].transform(lambda s: s - s.shift(6) + 1)                   # その7行がまたぐ「開いていた日」の数
srt["gap"] = srt.groupby("store_id")["ord"].diff()                                                     # 前の行は、何日前の営業日か
m = srt.merge(full[["store_id", "d", "ma7_cal"]], on=["store_id", "d"]).merge(stores[["store_id", "size"]], on="store_id").dropna(subset=["ma7_rows", "ma7_cal"])
m["err"] = (m["ma7_rows"] / m["ma7_cal"] - 1) * 100
ma = m.groupby("size", sort=False).agg(差の平均=("err", "mean"), 差が出た日の割合=("err", lambda s: (s > 1e-9).mean() * 100),
                                        七行が8営業日以上にまたがる割合=("span", lambda s: (s > 7).mean() * 100),
                                        またぐ営業日の最大=("span", "max")).reset_index()
lag = srt.merge(stores[["store_id", "size"]], on="store_id").dropna(subset=["gap"]).groupby("size", sort=False)["gap"] \
    .agg(前の行が前の営業日でない割合=lambda s: (s > 1).mean() * 100, 最大の間隔="max").reset_index()
ma = ma.merge(lag, on="size")
ma.round(2).to_csv(RES / "moving_average_and_lag.csv", index=False)
low = m.merge(stores[["store_id", "lam"]], on="store_id")
low = low[low["lam"] < 2]
ma_low = {"stores": int(low["store_id"].nunique()), "mean_err": float(low["err"].mean()), "share_differs": float((low["err"] > 1e-9).mean() * 100)}

# ---------- 図 ----------
fig, ax = plt.subplots(figsize=(9, 4.2))
x = np.linspace(0.2, 8.5, 200)
ax.plot(x, (1 / (1 - np.exp(-x)) - 1) * 100, color=GRAY, lw=1.5, label="理屈の値：1÷(1−e^−λ)−1")
ax.scatter(sw["lam"], sw["sim"], color=BLUE, zorder=3, label="架空のデータで数えた値")
for r in sw.itertuples():
    if r.lam in (0.5, 1, 2, 4): ax.annotate(f"+{r.sim:.0f}%", (r.lam, r.sim), textcoords="offset points", xytext=(8, 6), fontsize=9.5)
ax.set_xlabel("1日の会計の件数の平均（λ）"); ax.set_ylabel("1日あたりの売上が高く出る幅（%）"); ax.set_ylim(0, 370)
ax.set_title("客の少ない店ほど、売上0の日が抜けて平均が高く出る"); ax.legend(frameon=False)
save(fig, "a358_overestimate_by_traffic.png", "売上のあった日だけで平均した値 ÷ 売上0の日も入れた平均。" + SRC)

fig, ax = plt.subplots(figsize=(9, 4.2))
xs = np.arange(3); bw = 0.36
va = [by.loc[by["size"] == s, "A_平均"].iloc[0] for s in ["大", "中", "小"]]
vb = [by.loc[by["size"] == s, "B_平均"].iloc[0] for s in ["大", "中", "小"]]
ax.bar(xs - bw / 2, va, bw, color=ORANGE, label="A：売上の表だけで平均（0の日が抜ける）")
ax.bar(xs + bw / 2, vb, bw, color=GRAY, label="B：全部の日を0で埋める（定休日まで入る）")
for xi, v in zip(xs - bw / 2, va): ax.text(xi, v + 0.8, f"{v:+.1f}%", ha="center", fontsize=10)
for xi, v in zip(xs + bw / 2, vb): ax.text(xi, v - 2.2 if v < -0.05 else v + 0.8, f"{v:+.1f}%", ha="center", fontsize=10)
ax.set_ylim(-20, 30)
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(xs); ax.set_xticklabels(["大きい店（20店）", "中くらいの店（40店）", "小さい店（60店）"])
ax.set_ylabel("正しい値とのずれ（%、店の平均）")
ax.set_title("0の日を入れないと高く出て、休みの日まで入れると低く出る"); ax.legend(frameon=False, loc="upper left")
save(fig, "a358_error_by_size.png", "正しい値＝売上の合計÷開いていた日数。" + SRC)

ex_id = int(small.sort_values("lam").iloc[len(small) // 4]["store_id"])           # 小さい店のうち客の少なめの1店
a = srt[(srt["store_id"] == ex_id) & (srt["d"].between("2025-03-01", "2025-06-30"))]
bfull = full[(full["store_id"] == ex_id) & (full["d"].between("2025-03-01", "2025-06-30"))]
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.plot(a["d"], a["ma7_rows"], color=ORANGE, lw=1.6, label="行で7つ（売上のあった日だけの表）")
ax.plot(bfull["d"], bfull["ma7_cal"], color=BLUE, lw=1.6, label="開いていた7日（0の日を埋めた表）")
import matplotlib.dates as mdates
ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y年%-m月"))
ax.set_ylabel("7日の移動平均（円）"); ax.set_title(f"同じ店の「7日の移動平均」でも、0の日が抜けていると高い所を通る（店{ex_id}）")
ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.08))
save(fig, "a358_moving_average_example.png", SRC, y=-0.08)

exs = st[st["store_id"] == ex_id].iloc[0]
main = {"by_size": by.round(3).to_dict("records"), "chain_mean_per_store": chain, "chain_small": chain_small,
        "chain_err_a_pct": (chain["A"] / chain["C"] - 1) * 100, "chain_err_b_pct": (chain["B"] / chain["C"] - 1) * 100,
        "small_err_a_pct": (chain_small["A"] / chain_small["C"] - 1) * 100, "small_err_b_pct": (chain_small["B"] / chain_small["C"] - 1) * 100,
        "stores_over10pct": over10, "sweep": sw.round(3).to_dict("records"), "moving": ma.round(3).to_dict("records"),
        "rows_sales": int(len(sales)), "rows_open": int(len(store_days)), "rows_all": int(len(days) * len(stores)),
        "moving_lam_under2": ma_low, "example_store": {"id": ex_id, "lam": float(exs["lam"]), "zero_share": float(exs["zero_share"]), "err_a": float(exs["err_a"])}}
json.dump(main, open(RES / "a358_main.json", "w"), ensure_ascii=False, indent=1)
print(by.round(2).to_string()); print(sw.round(1).to_string()); print(ma.round(2).to_string())
print({k: round(v, 2) if isinstance(v, float) else v for k, v in main.items() if k not in ("by_size", "sweep", "moving")})
