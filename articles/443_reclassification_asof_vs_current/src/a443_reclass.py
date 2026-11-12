"""443 分類を付け替えたあと、過去の集計は「当時の区分」と「今の区分」でどれだけ違うか（架空の売上3年分）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SEED = 443
SRC = "架空の売上と分類マスタ（作成者が乱数で作成、seed 443）"
MONTHS = [f"{y}-{m:02d}" for y in (2023, 2024, 2025) for m in range(1, 13)]
CHANGES = ["2024-04", "2024-10", "2025-04"]          # 付け替えの月（この月から新しい分類）
NCAT, NPROD = 12, 400


def make(seed, move_share=0.06, drop_share=0.05, block=True):
    r = np.random.default_rng(seed)
    cat0 = r.integers(0, NCAT, NPROD)
    size = r.lognormal(13.0, 1.0, NPROD)                              # 月の売上の大きさ
    gr = r.normal(0.02, 0.08, NPROD)                                   # 商品ごとの年の伸び
    seas = 1 + 0.15 * np.sin(2 * np.pi * (np.arange(12)[None, :] + r.integers(0, 12, NPROD)[:, None]) / 12)
    t = np.arange(36)
    amt = size[:, None] * (1 + gr[:, None]) ** (t[None, :] / 12) * np.tile(seas, 3) * r.lognormal(0, 0.10, (NPROD, 36))
    end = np.full(NPROD, 36); gone = r.choice(NPROD, int(NPROD * drop_share), replace=False); end[gone] = r.integers(14, 34, len(gone))   # 扱いをやめた月
    amt[t[None, :] >= end[:, None]] = 0
    hist = []; cur = cat0.copy(); start = np.zeros(NPROD, int)
    for ch in CHANGES:
        k = MONTHS.index(ch); mv = r.choice(NPROD, int(NPROD * move_share), replace=False)
        if ch == CHANGES[1] and block:                                           # 2回目は、ある区分の一部をまとめて別の区分へ（組織の付け替え）
            src = r.integers(0, NCAT); mv = np.union1d(mv, np.flatnonzero(cur == src)[: int((cur == src).sum() * 0.5)])
        for p in mv:
            if end[p] <= k: continue
            new = (cur[p] + r.integers(1, NCAT)) % NCAT
            hist.append((p, cur[p], start[p], k - 1)); cur[p] = new; start[p] = k
    for p in range(NPROD): hist.append((p, cur[p], start[p], 9999))
    H = pd.DataFrame(hist, columns=["product_id", "cat", "from_i", "to_i"])
    S = pd.DataFrame({"product_id": np.repeat(np.arange(NPROD), 36), "mi": np.tile(t, NPROD), "amount": np.round(amt.ravel()).astype("int64")}); S = S[S.amount > 0]
    now = pd.DataFrame({"product_id": np.arange(NPROD), "cat": cur})[end == 36]          # いまのマスタ：扱いをやめた商品は載っていない
    return S, H, now


def three(S, H, now):
    S = S.assign(y=2023 + S.mi // 12)
    a = S.merge(now, on="product_id").groupby(["cat", "y"]).amount.sum().unstack(fill_value=0)                         # ① いまのマスタだけ
    m = S.merge(H, on="product_id"); m = m[(m.mi >= m.from_i) & (m.mi <= m.to_i)]
    b = m.groupby(["cat", "y"]).amount.sum().unstack(fill_value=0)                                                     # ② 当時の区分
    last = H.sort_values("from_i").groupby("product_id").tail(1)[["product_id", "cat"]]
    c = S.merge(last, on="product_id").groupby(["cat", "y"]).amount.sum().unstack(fill_value=0)                        # ③ いまの区分に引き直す
    return [x.reindex(range(NCAT), fill_value=0) for x in (a, b, c)]


def yoy(x, y): return (x[y] / x[y - 1] - 1) * 100


def measure(S, H, now):
    a, b, c = three(S, H, now); out = {}
    for y in (2024, 2025):
        d = (yoy(b, y) - yoy(c, y)).abs()
        out[f"differ5_{y}"] = int((d >= 5).sum()); out[f"differ10_{y}"] = int((d >= 10).sum()); out[f"max_{y}"] = float(d.max())
        big_b = yoy(b, y).abs() >= 20; out[f"jump_asof_{y}"] = int(big_b.sum()); out[f"jump_false_{y}"] = int((big_b & (yoy(c, y).abs() < 10)).sum())
        out[f"sign_{y}"] = int(((yoy(b, y) * yoy(c, y) < 0) & (d >= 5)).sum())
        out[f"lost_{y}"] = float((1 - a[y].sum() / c[y].sum()) * 100)
    out["lost_2023"] = float((1 - a[2023].sum() / c[2023].sum()) * 100)
    out["total_yoy_now_2025"] = float((a[2025].sum() / a[2024].sum() - 1) * 100); out["total_yoy_true_2025"] = float((c[2025].sum() / c[2024].sum() - 1) * 100)
    out["total_yoy_now_2024"] = float((a[2024].sum() / a[2023].sum() - 1) * 100); out["total_yoy_true_2024"] = float((c[2024].sum() / c[2023].sum() - 1) * 100)
    return out, (a, b, c)


S, H, now = make(SEED); res, (a, b, c) = measure(S, H, now)
names = [f"区分{chr(65 + i)}" for i in range(NCAT)]
S.assign(ym=[MONTHS[i] for i in S.mi]).drop(columns="mi").to_csv(DATA / "sales.csv", index=False)
Hc = H.assign(category=[names[i] for i in H.cat], valid_from=[MONTHS[i] for i in H.from_i], valid_to=[MONTHS[i] if i < 36 else "9999-12" for i in H.to_i])[["product_id", "category", "valid_from", "valid_to"]]
Hc.to_csv(DATA / "class_hist.csv", index=False); nowc = now.assign(category=[names[i] for i in now.cat])[["product_id", "category"]]; nowc.to_csv(DATA / "class_now.csv", index=False)
tab = pd.DataFrame({"区分": names, "①いまのマスタだけ 2024": a[2024].values, "①いまのマスタだけ 2025": a[2025].values, "②当時の区分 2024": b[2024].values, "②当時の区分 2025": b[2025].values,
                    "③いまの区分に引き直す 2024": c[2024].values, "③いまの区分に引き直す 2025": c[2025].values,
                    "前年比② 2025": yoy(b, 2025).round(1).values, "前年比③ 2025": yoy(c, 2025).round(1).values, "前年比② 2024": yoy(b, 2024).round(1).values, "前年比③ 2024": yoy(c, 2024).round(1).values,
                    "前年比① 2025": yoy(a, 2025).round(1).values})
tab.to_csv(RES / "category_table_main.csv", index=False)
moved = H.groupby("product_id").size(); n_moved = int((moved > 1).sum())

# SQL（DuckDB）で同じ3つを出して一致を確かめる
con = duckdb.connect(); con.execute("SET threads=1")
con.register("sales", pd.read_csv(DATA / "sales.csv")); con.register("class_hist", Hc); con.register("class_now", nowc)
q1 = "SELECT c.category, SUBSTR(s.ym,1,4) AS y, SUM(s.amount) AS amount FROM sales s JOIN class_now c ON c.product_id=s.product_id GROUP BY ALL"
q2 = "SELECT h.category, SUBSTR(s.ym,1,4) AS y, SUM(s.amount) AS amount FROM sales s JOIN class_hist h ON h.product_id=s.product_id AND s.ym BETWEEN h.valid_from AND h.valid_to GROUP BY ALL"
q3 = "WITH latest AS (SELECT product_id, category, ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY valid_from DESC) AS rn FROM class_hist) SELECT l.category, SUBSTR(s.ym,1,4) AS y, SUM(s.amount) AS amount FROM sales s JOIN latest l ON l.product_id=s.product_id AND l.rn=1 GROUP BY ALL"
chk = []
for q, x, lab in ((q1, a, "①"), (q2, b, "②"), (q3, c, "③")):
    d = con.execute(q).df(); p = d.pivot(index="category", columns="y", values="amount").fillna(0)
    for i, nm in enumerate(names):
        for y in (2023, 2024, 2025):
            v = int(p.loc[nm, str(y)]) if nm in p.index else 0
            assert v == int(x.loc[i, y]), (lab, nm, y)
    chk.append(dict(method=lab, rows=len(d), total=int(d.amount.sum())))
pd.DataFrame(chk).to_csv(RES / "sql_check_duckdb.csv", index=False)

# 2,000社分（乱数を変える）と、付け替える商品の割合を変えた場合
rows = []
for k in range(2000):
    r_, _ = measure(*make(10_000 + k)); rows.append(r_)
sim = pd.DataFrame(rows); sim.round(3).to_csv(RES / "sim_2000_companies.csv", index=False)
rows = []
for ms in (0.0, 0.02, 0.04, 0.06, 0.10, 0.15):
    rr = pd.DataFrame([measure(*make(50_000 + k, move_share=ms))[0] for k in range(300)])
    rows.append(dict(move_share=ms, differ5_2025=float(rr.differ5_2025.mean()), differ5_2024=float(rr.differ5_2024.mean()), jump_false_2025=float(rr.jump_false_2025.mean()), max_2025=float(rr.max_2025.median()), sign_2025=float(rr.sign_2025.mean())))
sw = pd.DataFrame(rows); sw.round(3).to_csv(RES / "by_move_share.csv", index=False)
rows = []
for ms in (0.0, 0.02, 0.06, 0.10):
    rr = pd.DataFrame([measure(*make(60_000 + k, move_share=ms, block=False))[0] for k in range(300)])
    rows.append(dict(move_share=ms, differ5_2025=float(rr.differ5_2025.mean()), differ5_2024=float(rr.differ5_2024.mean()), jump_false_2025=float(rr.jump_false_2025.mean()), max_2025=float(rr.max_2025.median())))
swn = pd.DataFrame(rows); swn.round(3).to_csv(RES / "by_move_share_no_block.csv", index=False)
rows = []
for ds in (0.0, 0.02, 0.05, 0.10):
    rr = pd.DataFrame([measure(*make(70_000 + k, drop_share=ds))[0] for k in range(300)])
    rows.append(dict(drop_share=ds, lost_2023=float(rr.lost_2023.mean()), lost_2024=float(rr.lost_2024.mean()), lost_2025=float(rr.lost_2025.mean()), total_yoy_now_2025=float(rr.total_yoy_now_2025.mean()), total_yoy_true_2025=float(rr.total_yoy_true_2025.mean()),
                     total_yoy_now_2024=float(rr.total_yoy_now_2024.mean()), total_yoy_true_2024=float(rr.total_yoy_true_2024.mean())))
dw = pd.DataFrame(rows); dw.round(3).to_csv(RES / "by_drop_share.csv", index=False)

main = dict(n_products=NPROD, n_categories=NCAT, changes=CHANGES, moved_products=n_moved, rows_sales=len(S), main=res,
            sim=dict(n=2000, **{k: round(float(sim[k].mean()), 2) for k in sim.columns}, differ5_2025_ge3=round(float((sim.differ5_2025 >= 3).mean() * 100), 1), jump_false_2025_ge1=round(float((sim.jump_false_2025 >= 1).mean() * 100), 1),
                     jump_false_2024_ge1=round(float((sim.jump_false_2024 >= 1).mean() * 100), 1), sign_any=round(float(((sim.sign_2025 + sim.sign_2024) >= 1).mean() * 100), 1), max_2025_median=round(float(sim.max_2025.median()), 1), max_2024_median=round(float(sim.max_2024.median()), 1)),
            by_move_share=sw.round(3).to_dict("records"), by_move_share_no_block=swn.round(3).to_dict("records"), by_drop_share=dw.round(3).to_dict("records"))
json.dump(main, open(RES / "a443_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：区分ごとの前年比（2025年、②と③）
fig, ax = plt.subplots(figsize=(10, 4.4)); x = np.arange(NCAT); w = 0.38
ax.bar(x - w / 2, yoy(b, 2025), w, color=ORANGE, label="②当時の区分で集計"); ax.bar(x + w / 2, yoy(c, 2025), w, color=BLUE, label="③いまの区分に引き直して集計")
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(names); ax.set_ylabel("2025年の売上の前年比（%）"); ax.set_title("同じ売上でも、区分ごとの前年比は集計のしかたで変わる（架空の1社）"); ax.legend(frameon=False, fontsize=9)
save(fig, "a443_yoy_by_category.png", SRC)
# 図2：2,000社の分布
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4))
for ax, col, ttl in ((axs[0], "differ5", "前年比が5ポイント以上違う区分の数（12区分のうち）"), (axs[1], "jump_false", "「2割以上の増減」に見えるが、引き直すと1割未満の区分の数")):
    for y, cc, off in ((2024, LIGHT, -0.2), (2025, BLUE, 0.2)):
        v = sim[f"{col}_{y}"].value_counts(normalize=True).sort_index() * 100; ax.bar(v.index + off, v.values, 0.4, color=cc, label=f"{y}年の前年比")
    ax.set_xlabel(ttl); ax.set_ylabel("2,000社のうちの割合（%）"); ax.legend(frameon=False, fontsize=9)
fig.suptitle("乱数を変えた2,000社での数え上げ", fontsize=13)
save(fig, "a443_sim_distribution.png", SRC)
# 図3：付け替える商品の割合と、いまのマスタだけで落ちる売上
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4))
axs[0].plot(sw.move_share * 100, sw.differ5_2025, "-o", color=BLUE, label="2025年の前年比"); axs[0].plot(sw.move_share * 100, sw.differ5_2024, "-o", color=LIGHT, label="2024年の前年比")
axs[0].plot(swn.move_share * 100, swn.differ5_2025, "--s", color=GRAY, label="2025年（まとめての付け替えなし）"); axs[0].set_xlabel("1回の付け替えで動く商品の割合（%）"); axs[0].set_ylabel("前年比が5ポイント以上違う区分の数（平均）"); axs[0].set_title("付け替えが多いほど、違う区分が増える", fontsize=12); axs[0].legend(frameon=False, fontsize=9)
xx = np.arange(len(dw)); axs[1].bar(xx - 0.27, dw.lost_2023, 0.27, color=INK, label="2023年"); axs[1].bar(xx, dw.lost_2024, 0.27, color=BLUE, label="2024年"); axs[1].bar(xx + 0.27, dw.lost_2025, 0.27, color=LIGHT, label="2025年")
axs[1].set_xticks(xx); axs[1].set_xticklabels([f"{int(v * 100)}%" for v in dw.drop_share]); axs[1].set_xlabel("3年のあいだに扱いをやめた商品の割合"); axs[1].set_ylabel("①いまのマスタだけの集計で落ちる売上（%）"); axs[1].set_title("古い年ほど、売上が多く落ちる", fontsize=12); axs[1].legend(frameon=False, fontsize=9)
save(fig, "a443_move_and_drop.png", SRC)
print(json.dumps(main, ensure_ascii=False)[:3000]); print(tab[["区分", "前年比② 2025", "前年比③ 2025", "前年比② 2024", "前年比③ 2024", "前年比① 2025"]].to_string())
