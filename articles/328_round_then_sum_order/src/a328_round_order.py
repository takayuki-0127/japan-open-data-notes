"""328 行ごとに丸めてから足すのと、足してから丸めるのでは、どれだけ違うか
架空の伝票（税率8%と10%、数量×単価）で、消費税の端数を丸める場所を4通りに変えて比べる。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SEED = 328; rng = np.random.default_rng(SEED)
NINV, NCUST = 20_000, 400
# ---------- 架空の明細：1か月分、得意先400、伝票2万枚 ----------
nline = np.clip(rng.poisson(5.0, NINV), 1, 30)
inv = np.repeat(np.arange(1, NINV + 1), nline); L = len(inv)
cust_of_inv = rng.integers(1, NCUST + 1, NINV)
unit = rng.choice([58, 88, 98, 108, 128, 148, 178, 198, 228, 258, 298, 348, 398, 480, 598, 780, 980, 1280, 1980, 2980], L)
qty = rng.integers(1, 13, L)
rate = rng.choice([8, 10], L, p=[0.6, 0.4])                      # 8%＝軽減税率の品目、10%＝そのほか
lines = pd.DataFrame({"invoice_id": inv, "line_no": np.concatenate([np.arange(1, n + 1) for n in nline]),
                      "customer_id": cust_of_inv[inv - 1], "unit_price": unit, "qty": qty, "tax_rate": rate})
lines["net"] = lines.unit_price * lines.qty                       # 税抜の金額（整数の円）
lines.to_csv(DATA / "invoice_lines.csv", index=False)

con = duckdb.connect(); con.register("lines", lines)
# 丸め方3つ：切り捨て・四捨五入・切り上げ。税額は「税抜×税率÷100」を整数で計算する（小数の誤差を避ける）
RND = {"切り捨て": "(x) // 100", "四捨五入": "((x) + 50) // 100", "切り上げ": "((x) + 99) // 100"}
def taxes(expr):
    f = lambda x: expr.replace("(x)", f"({x})")
    return con.sql(f"""
    WITH l AS (SELECT *, net * tax_rate AS t100 FROM lines),
    by_line AS (SELECT invoice_id, sum({f('t100')}) AS tax FROM l GROUP BY 1),                       -- ① 明細ごとに丸める
    by_rate AS (SELECT invoice_id, sum(tax) AS tax FROM (SELECT invoice_id, tax_rate, {f('sum(t100)')} AS tax FROM l GROUP BY 1,2) GROUP BY 1),  -- ② 伝票の中で税率ごとに1回
    by_inv  AS (SELECT invoice_id, {f('sum(t100)')} AS tax FROM l GROUP BY 1),                       -- ③ 伝票全体で1回
    n AS (SELECT invoice_id, any_value(customer_id) AS customer_id, count(*) AS n_lines, count(DISTINCT tax_rate) AS n_rates, sum(net) AS net, sum(t100)/100.0 AS exact FROM l GROUP BY 1)
    SELECT n.*, a.tax AS t_line, b.tax AS t_rate, c.tax AS t_inv FROM n JOIN by_line a USING (invoice_id) JOIN by_rate b USING (invoice_id) JOIN by_inv c USING (invoice_id)
    ORDER BY invoice_id""").df()
def monthly(expr):                                                 # ④ 得意先ごとに月の合計で、税率ごとに1回
    f = lambda x: expr.replace("(x)", f"({x})")
    return con.sql(f"SELECT sum(tax) FROM (SELECT customer_id, tax_rate, {f('sum(net*tax_rate)')} AS tax FROM lines GROUP BY 1,2)").fetchone()[0]
out, summ = {}, []
for k, e in RND.items():
    d = taxes(e); out[k] = d
    ex = float(d.exact.sum())
    summ.append({"丸め方": k, "正確な税額の合計": ex, "①明細ごと": int(d.t_line.sum()), "②伝票の税率ごと": int(d.t_rate.sum()), "③伝票全体": int(d.t_inv.sum()), "④得意先の月合計・税率ごと": int(monthly(e)),
                 "①−②が1円以上の伝票の割合": float((d.t_line != d.t_rate).mean()), "②−③が1円以上の伝票の割合": float((d.t_rate != d.t_inv).mean()),
                 "①−②の平均（円）": float((d.t_line - d.t_rate).mean()), "①−②の最大の差（円）": int((d.t_line - d.t_rate).abs().max())})
summ = pd.DataFrame(summ); summ.to_csv(RES / "summary.csv", index=False)
d = out["切り捨て"]; d.to_csv(RES / "invoice_tax_truncate.csv", index=False)
d["diff"] = d.t_line - d.t_rate
dist = d["diff"].value_counts().sort_index().rename_axis("①−②（円）").reset_index(name="伝票数"); dist.to_csv(RES / "diff_distribution_truncate.csv", index=False)
bins = [0, 1, 2, 3, 5, 8, 12, 30]; d["行数の区分"] = pd.cut(d.n_lines, bins, labels=["1", "2", "3", "4〜5", "6〜8", "9〜12", "13〜"])
byn = pd.concat({k: out[k].assign(g=pd.cut(out[k].n_lines, bins, labels=["1", "2", "3", "4〜5", "6〜8", "9〜12", "13〜"])).groupby("g", observed=True)
                 .apply(lambda g: pd.Series({"伝票数": len(g), "差が出た割合": (g.t_line != g.t_rate).mean(), "平均の差（円）": (g.t_line - g.t_rate).mean()})) for k in RND}).reset_index()
byn.columns = ["丸め方", "明細の行数", "伝票数", "差が出た割合", "平均の差（円）"]; byn.to_csv(RES / "by_lines.csv", index=False)
# pandas での検算（SQL と別の計算）
chk = lines.assign(t100=lines.net * lines.tax_rate)
p_line = (chk.t100 // 100).groupby(chk.invoice_id).sum().values
p_rate = (chk.groupby(["invoice_id", "tax_rate"]).t100.sum() // 100).groupby("invoice_id").sum().values
assert (p_line == d.t_line.values).all() and (p_rate == d.t_rate.values).all()
tot = summ.set_index("丸め方")
main = {"invoices": NINV, "lines": int(L), "customers": NCUST, "mean_lines": float(nline.mean()), "net_total": int(lines.net.sum()),
        "summary": summ.to_dict(orient="records"),
        "truncate": {"share_diff": float((d["diff"] != 0).mean()), "mean_diff": float(d["diff"].mean()), "min_diff": int(d["diff"].min()),
                     "total_line_minus_rate": int(d["diff"].sum()), "total_rate_minus_inv": int((d.t_rate - d.t_inv).sum()),
                     "total_line_minus_month": int(tot.loc["切り捨て", "①明細ごと"] - tot.loc["切り捨て", "④得意先の月合計・税率ごと"]),
                     "share_of_tax": float(d["diff"].sum() / d.t_rate.sum()), "two_rate_invoices": float((d.n_rates == 2).mean()),
                     "share_rate_vs_inv": float((d.t_rate != d.t_inv).mean())},
        "pandas_check": "SQL と pandas の①②が全伝票で一致"}
json.dump(main, open(RES / "a328_main.json", "w"), ensure_ascii=False, indent=1)
print(summ.T.to_string()); print(dist.to_string()); print(byn.to_string()); print(json.dumps(main["truncate"], ensure_ascii=False))

SRC = "架空の伝票（作成者が乱数で作成、seed 328）"
fig, ax = plt.subplots(figsize=(8.2, 4.0))
ax.bar(dist["①−②（円）"], dist["伝票数"] / NINV * 100, color=BLUE)
for x, y in zip(dist["①−②（円）"], dist["伝票数"] / NINV * 100):
    if y >= 0.5: ax.text(x, y + 0.5, f"{y:.0f}%", ha="center", fontsize=9)
ax.set_xlabel("明細ごとに切り捨てた税額 − 伝票の税率ごとに1回切り捨てた税額（円）"); ax.set_ylabel("伝票の割合（%）")
ax.set_title("切り捨てを明細ごとにすると、伝票の税額は税率ごと1回のときより平均で" + f"{-d['diff'].mean():.1f}円少ない", loc="left", fontsize=11.5)
save(fig, "a328_diff_hist.png", SRC)
fig, ax = plt.subplots(figsize=(8.2, 4.0)); w = 0.26
for i, (k, c) in enumerate(zip(RND, [BLUE, GREEN, ORANGE])):
    g = byn[byn["丸め方"] == k]; ax.bar(np.arange(len(g)) + (i - 1) * w, g["差が出た割合"] * 100, w, color=c, label=k)
ax.set_xticks(range(7)); ax.set_xticklabels(["1", "2", "3", "4〜5", "6〜8", "9〜12", "13〜"]); ax.set_xlabel("伝票の明細の行数"); ax.set_ylabel("①と②で税額が違う伝票の割合（%）"); ax.legend(frameon=False)
ax.set_title("明細が増えるほど、丸める場所で税額が変わる伝票が増える", loc="left", fontsize=11.5)
save(fig, "a328_by_lines.png", SRC)
fig, ax = plt.subplots(figsize=(8.6, 4.0)); cols = ["①明細ごと", "②伝票の税率ごと", "③伝票全体", "④得意先の月合計・税率ごと"]
for i, (k, c) in enumerate(zip(RND, [BLUE, GREEN, ORANGE])):
    r = tot.loc[k]; v = [r[c_] - r["正確な税額の合計"] for c_ in cols]; ax.bar(np.arange(4) + (i - 1) * w, v, w, color=c, label=k)
    for x, y in zip(np.arange(4) + (i - 1) * w, v): ax.text(x, y + (900 if y >= 0 else -900), f"{y:+,.0f}", ha="center", va="bottom" if y >= 0 else "top", fontsize=8)
ax.set_ylim(-48000, 50000); ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(range(4)); ax.set_xticklabels(["①明細ごと", "②伝票の中で\n税率ごとに1回", "③伝票全体で1回", "④得意先の月合計で\n税率ごとに1回"], fontsize=9.5)
ax.set_ylabel("丸めない税額の合計との差（円）"); ax.legend(frameon=False, ncol=3, loc="upper right")
ax.set_title("丸める場所を粗くするほど、1か月の税額の合計は丸めない値に近づく", loc="left", fontsize=11.5)
save(fig, "a328_month_total.png", SRC)
