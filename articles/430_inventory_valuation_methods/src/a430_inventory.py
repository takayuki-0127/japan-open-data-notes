"""430 同じ仕入れと販売でも、在庫の評価の方法で、月の粗利はどれだけ違うのか
架空の商品200点、36か月（仕入れ値が上がる18か月と下がる18か月）。乱数の種は430。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SRC = "出所：架空のデータ（作成者が乱数で作成、seed 430）"
MONTHS = pd.period_range("2023-01", "2025-12", freq="M")


def price_index(up=0.30, down=0.20):
    """仕入れ値の指数。前半18か月で up 上がり、後半18か月で down 下がる"""
    a = np.linspace(1.0, 1.0 + up, 19)[1:]
    b = np.linspace(1.0 + up, (1.0 + up) * (1 - down), 19)[1:]
    return np.concatenate([a, b])


def make(seed=430, n_items=200, cover=2.0, up=0.30, down=0.20):
    """cover＝在庫を何か月分持つか（目安）。販売価格は、その月の仕入れ値の1.3倍"""
    rng = np.random.default_rng(seed)
    idx = price_index(up, down)
    P, S = [], []
    for it in range(1, n_items + 1):
        base = float(np.round(rng.lognormal(np.log(800), 0.7), 0)) + 50
        demand = max(5, int(rng.lognormal(np.log(60), 0.6)))
        stock = int(round(demand * cover))
        # 期首の在庫（2022年末の仕入れ値＝指数1.0）
        P.append((it, pd.Timestamp("2022-12-31"), 0, stock, round(base, 2)))
        for mi, m in enumerate(MONTHS):
            cost = round(base * idx[mi] * rng.normal(1, 0.01), 2)
            days = m.days_in_month
            sold_m = 0
            for k in range(4):                                  # 月に4回売れる
                q = max(1, int(round(demand / 4 * rng.lognormal(0, 0.25))))
                q = min(q, stock)
                if q > 0:
                    S.append((it, m.to_timestamp() + pd.Timedelta(days=int((k + 1) * days / 4) - 1), k + 1, q, round(cost * 1.3, 2)))
                    stock -= q; sold_m += q
                if k == 1:                                      # 月の半ばに1回仕入れる：在庫を cover か月分に戻す
                    buy = max(0, int(round(demand * cover)) - stock + int(round(demand / 2)))
                    if buy > 0:
                        P.append((it, m.to_timestamp() + pd.Timedelta(days=int(days / 2)), 0, buy, cost)); stock += buy
    P = pd.DataFrame(P, columns=["item_id", "d", "seq", "qty", "unit_cost"]); S = pd.DataFrame(S, columns=["item_id", "d", "seq", "qty", "unit_price"])
    return P, S, idx


def value(P, S):
    """3つの方法の、月ごとの売上原価と月末の在庫金額"""
    P = P.sort_values(["item_id", "d", "seq"]); S = S.sort_values(["item_id", "d", "seq"])
    ym_of = lambda d: d.to_period("M")
    cogs = {k: {} for k in ["先入先出", "移動平均", "総平均（月ごと）"]}
    inv = {k: {} for k in cogs}
    for it, p in P.groupby("item_id"):
        s = S[S.item_id == it]
        ev = pd.concat([p.assign(kind=0, price=p.unit_cost)[["d", "kind", "seq", "qty", "price"]], s.assign(kind=1, price=s.unit_price)[["d", "kind", "seq", "qty", "price"]]])
        ev = ev.sort_values(["d", "kind", "seq"]).values
        # 先入先出
        lots = []; q_ma = 0; v_ma = 0.0
        byM = {}
        for d_, kind, _, q, pr in ev:
            ym = ym_of(d_)
            b = byM.setdefault(ym, {"buy_q": 0, "buy_v": 0.0, "sell_q": 0, "fifo": 0.0, "ma": 0.0})
            if kind == 0:
                lots.append([q, pr]); q_ma += q; v_ma += q * pr
                b["buy_q"] += q; b["buy_v"] += q * pr
            else:
                need = q; c = 0.0
                while need > 0:
                    take = min(need, lots[0][0]); c += take * lots[0][1]; lots[0][0] -= take; need -= take
                    if lots[0][0] == 0:
                        lots.pop(0)
                b["fifo"] += c
                u = v_ma / q_ma; b["ma"] += q * u; q_ma -= q; v_ma -= q * u
                b["sell_q"] += q
            b["inv_fifo"] = sum(l[0] * l[1] for l in lots); b["inv_ma"] = v_ma; b["inv_q"] = q_ma
        # 総平均（月ごと）：月初の在庫＋その月の仕入れを、月の単価でならす
        q0 = 0; v0 = 0.0
        for ym in sorted(byM):
            b = byM[ym]
            qt = q0 + b["buy_q"]; vt = v0 + b["buy_v"]
            u = vt / qt if qt else 0.0
            c = b["sell_q"] * u
            q0 = qt - b["sell_q"]; v0 = vt - c
            for k, val, iv in [("先入先出", b["fifo"], b["inv_fifo"]), ("移動平均", b["ma"], b["inv_ma"]), ("総平均（月ごと）", c, v0)]:
                cogs[k][ym] = cogs[k].get(ym, 0.0) + val; inv[k][ym] = inv[k].get(ym, 0.0) + iv
    C = pd.DataFrame(cogs).sort_index(); I = pd.DataFrame(inv).sort_index()
    return C.loc[MONTHS], I


def summary(P, S):
    C, I = value(P, S)
    sales = S.assign(ym=S.d.dt.to_period("M"), amt=S.qty * S.unit_price).groupby("ym").amt.sum().loc[MONTHS]
    G = (-C).add(sales, axis=0)
    return sales, C, G, I


P, S, idx = make()
P.assign(d=P.d.dt.strftime("%Y-%m-%d")).to_csv(DATA / "purchases.csv", index=False); S.assign(d=S.d.dt.strftime("%Y-%m-%d")).to_csv(DATA / "sales.csv", index=False)
sales, C, G, I = summary(P, S)
M = pd.DataFrame({"売上": sales, "仕入れ値の指数": idx})
for k in C.columns:
    M[f"粗利：{k}"] = G[k]; M[f"粗利率：{k}"] = G[k] / sales * 100
M["差：先入先出−移動平均（%）"] = (G["先入先出"] / G["移動平均"] - 1) * 100
M["差：総平均−移動平均（%）"] = (G["総平均（月ごと）"] / G["移動平均"] - 1) * 100
M["差：先入先出−総平均（%）"] = (G["先入先出"] / G["総平均（月ごと）"] - 1) * 100
M.index = M.index.astype(str); M.round(3).to_csv(RES / "monthly_gross_profit.csv")
up, dn = slice(0, 18), slice(18, 36)
d_fm = M["差：先入先出−移動平均（%）"]; d_tm = M["差：総平均−移動平均（%）"]; d_ft = M["差：先入先出−総平均（%）"]


def stat(x):
    return {"差が1%以上の月": int((x.abs() >= 1).sum()), "差が0.5%未満の月": int((x.abs() < 0.5).sum()), "差が1%以上の月の一覧": [m for m in x.index if abs(x[m]) >= 1],"上がる時期の平均": round(float(x.iloc[up].mean()), 2), "下がる時期の平均": round(float(x.iloc[dn].mean()), 2), "大きさの中央値": round(float(x.abs().median()), 2),
            "最大": round(float(x.max()), 2), "最小": round(float(x.min()), 2), "最大の月": x.idxmax(), "最小の月": x.idxmin(),
            "先入先出のほうが多い月": int((x > 0).sum())}


yr = {}
for y in ["2023", "2024", "2025"]:
    mk = [m.startswith(y) for m in M.index]
    yr[y] = {k: round(float(G[k].values[mk].sum()), 0) for k in G.columns}
    yr[y]["差：先入先出−移動平均（%）"] = round((yr[y]["先入先出"] / yr[y]["移動平均"] - 1) * 100, 2)
    yr[y]["差：総平均−移動平均（%）"] = round((yr[y]["総平均（月ごと）"] / yr[y]["移動平均"] - 1) * 100, 2)
tot = {k: float(G[k].sum()) for k in G.columns}
tot_diff = {"先入先出−移動平均（%）": round((tot["先入先出"] / tot["移動平均"] - 1) * 100, 3), "総平均−移動平均（%）": round((tot["総平均（月ごと）"] / tot["移動平均"] - 1) * 100, 3)}
h1 = {k: float(G[k].iloc[up].sum()) for k in G.columns}; h2 = {k: float(G[k].iloc[dn].sum()) for k in G.columns}
half = {"上がる18か月：先入先出−移動平均（%）": round((h1["先入先出"] / h1["移動平均"] - 1) * 100, 2), "下がる18か月：先入先出−移動平均（%）": round((h2["先入先出"] / h2["移動平均"] - 1) * 100, 2)}
inv_end = {k: round(float(I[k].iloc[-1]), 0) for k in I.columns}
inv_peak = {k: round(float(I[k].loc[MONTHS[17]]), 0) for k in I.columns}
true_margin = round((1 - 1 / 1.3) * 100, 2)
gm = {k: {"上がる時期の平均": round(float(M[f"粗利率：{k}"].iloc[up].mean()), 2), "下がる時期の平均": round(float(M[f"粗利率：{k}"].iloc[dn].mean()), 2),
          "最高": round(float(M[f"粗利率：{k}"].max()), 2), "最低": round(float(M[f"粗利率：{k}"].min()), 2)} for k in C.columns}

# ---- 在庫を持つ月数を変える
cov = []
for c in [0.5, 1.0, 2.0, 4.0]:
    P2, S2, _ = make(cover=c)
    s2, C2, G2, I2 = summary(P2, S2)
    x = (G2["先入先出"] / G2["移動平均"] - 1) * 100; t = (G2["総平均（月ごと）"] / G2["移動平均"] - 1) * 100
    turn = float((I2["移動平均"].loc[MONTHS].values / (C2["移動平均"].values)).mean())
    cov.append({"在庫の目安（か月分）": c, "在庫÷月の売上原価（平均）": round(turn, 2), "先入先出−移動平均：上がる時期の平均（%）": round(float(x.iloc[up].mean()), 2),
                "先入先出−移動平均：下がる時期の平均（%）": round(float(x.iloc[dn].mean()), 2), "総平均−移動平均：大きさの中央値（%）": round(float(t.abs().median()), 2),
                "粗利率（先入先出）：上がる時期": round(float((G2["先入先出"] / s2 * 100).iloc[up].mean()), 2), "粗利率（先入先出）：下がる時期": round(float((G2["先入先出"] / s2 * 100).iloc[dn].mean()), 2),
                "3年の合計の差（%）": round(float((G2["先入先出"].sum() / G2["移動平均"].sum() - 1) * 100), 3)})
cov = pd.DataFrame(cov); cov.to_csv(RES / "by_inventory_cover.csv", index=False)
# ---- 値動きの大きさを変える
mv = []
for u_, d_ in [(0.0, 0.0), (0.1, 0.1 / 1.1), (0.3, 0.3 / 1.3), (0.6, 0.6 / 1.6)]:
    P2, S2, _ = make(up=u_, down=d_)
    s2, C2, G2, I2 = summary(P2, S2)
    x = (G2["先入先出"] / G2["移動平均"] - 1) * 100
    mv.append({"前半18か月の上がり幅（%）": round(u_ * 100), "先入先出−移動平均：上がる時期の平均（%）": round(float(x.iloc[up].mean()), 2), "下がる時期の平均（%）": round(float(x.iloc[dn].mean()), 2),
               "3年の合計の差（%）": round(float((G2["先入先出"].sum() / G2["移動平均"].sum() - 1) * 100), 3)})
mv = pd.DataFrame(mv); mv.to_csv(RES / "by_price_move.csv", index=False)

# ---- SQL（DuckDB）：先入先出を「累計の数量の区間の重なり」で出す
con = duckdb.connect(); con.register("purchases", P); con.register("sales", S)
q = """
WITH p AS (SELECT item_id, unit_cost, SUM(qty) OVER (PARTITION BY item_id ORDER BY d, seq ROWS UNBOUNDED PRECEDING) - qty AS q_from,
                  SUM(qty) OVER (PARTITION BY item_id ORDER BY d, seq ROWS UNBOUNDED PRECEDING) AS q_to FROM purchases),
     s AS (SELECT item_id, d, SUM(qty) OVER (PARTITION BY item_id ORDER BY d, seq ROWS UNBOUNDED PRECEDING) - qty AS q_from,
                  SUM(qty) OVER (PARTITION BY item_id ORDER BY d, seq ROWS UNBOUNDED PRECEDING) AS q_to FROM sales)
SELECT strftime(date_trunc('month', s.d), '%Y-%m') AS ym, SUM((LEAST(s.q_to, p.q_to) - GREATEST(s.q_from, p.q_from)) * p.unit_cost) AS cogs_fifo
FROM s JOIN p ON p.item_id = s.item_id AND p.q_from < s.q_to AND p.q_to > s.q_from GROUP BY 1 ORDER BY 1"""
r = con.execute(q).fetchall()
a = np.array([float(x[1]) for x in r]); b = C["先入先出"].values
ok = bool(np.allclose(a, b, rtol=1e-9)); assert ok and len(a) == 36
pd.DataFrame([{"確かめたこと": "DuckDB の SQL で出した先入先出の売上原価が、Python の計算と36か月すべてで一致", "結果": ok}]).to_csv(RES / "sql_check_duckdb.csv", index=False)

main = {"items": 200, "months": 36, "purchases": int(len(P)), "sales_rows": int(len(S)), "sales_total": round(float(sales.sum()), 0), "true_margin_at_current_cost": true_margin,
        "gross_margin": gm, "diff_fifo_vs_ma": stat(d_fm), "diff_total_vs_ma": stat(d_tm), "diff_fifo_vs_total": stat(d_ft), "by_year": yr, "total_gross": {k: round(v, 0) for k, v in tot.items()},
        "total_diff": tot_diff, "half": half, "inventory_end": inv_end, "inventory_at_peak": inv_peak,
        "end_inventory_diff_fifo_minus_ma": round(inv_end["先入先出"] - inv_end["移動平均"], 0), "total_gross_diff_fifo_minus_ma": round(tot["先入先出"] - tot["移動平均"], 0),
        "by_cover": json.loads(cov.to_json(orient="records", force_ascii=False)), "by_move": json.loads(mv.to_json(orient="records", force_ascii=False))}
json.dump(main, open(RES / "a430_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図1：仕入れ値の指数と、方法ごとの粗利率
x = np.arange(36); lab = [m if m.endswith("-01") or m.endswith("-07") else "" for m in M.index]
fig, axs = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True, gridspec_kw={"height_ratios": [1, 2]})
axs[0].plot(x, idx * 100, color=INK); axs[0].set_ylabel("仕入れ値の指数\n（2022年末＝100）"); axs[0].axvline(17.5, color=GRAY, ls=":")
axs[0].set_title("仕入れ値が上がる時期は粗利率が高く、下がる時期は低く出る（3つの方法とも）")
for k, c in [("先入先出", ORANGE), ("移動平均", BLUE), ("総平均（月ごと）", GREEN)]:
    axs[1].plot(x, M[f"粗利率：{k}"], color=c, label=k, lw=1.6)
axs[1].axhline(true_margin, color=GRAY, ls="--", lw=1); axs[1].text(35.5, true_margin + 0.12, f"その月の仕入れ値で計算した粗利率 {true_margin:.1f}%", fontsize=8.5, va="bottom", ha="right", color=INK)
axs[1].axvline(17.5, color=GRAY, ls=":"); axs[1].set_ylabel("粗利率（%）"); axs[1].legend(frameon=False, ncol=3, loc="lower left")
axs[1].set_xticks(x); axs[1].set_xticklabels(lab, fontsize=8); axs[1].set_xlim(-0.5, 35.8)
save(fig, "a430_margin_by_method.png", SRC)

# ---- 図2：月の粗利の差
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.bar(x - 0.2, d_fm.values, 0.4, color=ORANGE, label="先入先出 − 移動平均")
ax.bar(x + 0.2, d_tm.values, 0.4, color=GREEN, label="総平均（月ごと）− 移動平均")
ax.axhline(0, color=INK, lw=0.8); ax.axvline(17.5, color=GRAY, ls=":")
ax.text(8, ax.get_ylim()[1] * 0.92, "仕入れ値が上がる時期", ha="center", fontsize=9, color=GRAY); ax.text(27, ax.get_ylim()[1] * 0.92, "下がる時期", ha="center", fontsize=9, color=GRAY)
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=8); ax.set_ylabel("月の粗利の差（%）"); ax.set_title("月の粗利は、評価の方法でどれだけ違うか（移動平均を基準）")
ax.legend(frameon=False, loc="lower left")
save(fig, "a430_monthly_diff.png", SRC)

# ---- 図3：左＝粗利の差の累計、右＝在庫を持つ月数
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.1))
ax = axs[0]
cum = (G["先入先出"] - G["移動平均"]).cumsum().values / 1e6
cum2 = (G["総平均（月ごと）"] - G["移動平均"]).cumsum().values / 1e6
ax.plot(x, cum, color=ORANGE, label="先入先出 − 移動平均"); ax.plot(x, cum2, color=GREEN, label="総平均（月ごと）− 移動平均")
ax.axhline(0, color=INK, lw=0.8); ax.axvline(17.5, color=GRAY, ls=":")
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=7); ax.set_ylabel("粗利の差の累計（百万円）"); ax.set_title("差の累計は、仕入れ値の向きが変わると逆に動く"); ax.legend(frameon=False, fontsize=8)
ax = axs[1]
w = 0.35; xx = np.arange(len(cov))
ax.bar(xx - w / 2, cov["先入先出−移動平均：上がる時期の平均（%）"], w, color=ORANGE, label="上がる時期")
ax.bar(xx + w / 2, cov["先入先出−移動平均：下がる時期の平均（%）"], w, color=BLUE, label="下がる時期")
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(xx); ax.set_xticklabels([f"{c:g}か月分" for c in cov["在庫の目安（か月分）"]])
ax.set_xlabel("持つ在庫の目安"); ax.set_ylabel("先入先出 − 移動平均の月の粗利の差（平均、%）"); ax.set_title("在庫を長く持つほど、方法による差が大きい"); ax.legend(frameon=False)
fig.tight_layout()
save(fig, "a430_cumulative_and_cover.png", SRC)
print(json.dumps(main, ensure_ascii=False)[:5000])
