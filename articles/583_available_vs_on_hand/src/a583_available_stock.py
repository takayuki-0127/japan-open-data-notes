"""583 在庫を帳簿上の数（有り高）で見るか、引当を除いた使える数（引当可能数）で見るかで、
欠品の判定は何品目・何日変わるのか。架空の在庫と受注（seed 583）"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SRC = "出典：架空の在庫と受注（作成者が乱数で作成、seed 583）"
rng = np.random.default_rng(583)
DAYS = 182                      # 2025-01-01〜2025-07-01
d0 = pd.Timestamp("2025-01-01")

# ---- 1. 品目：A 小口中心（出荷まで1〜3日）・B 先の日付の大口受注が混じる・C 動きの少ない品目 ----
sku = []
for i in range(200):
    kind = "A" if i < 100 else ("B" if i < 160 else "C")
    rate = {"A": rng.uniform(1.5, 4.0), "B": rng.uniform(1.0, 3.0), "C": rng.uniform(0.1, 0.5)}[kind]
    sku.append({"sku": f"P{i + 1:03d}", "kind": kind, "rate": rate})
sku = pd.DataFrame(sku)

orders, snaps = [], []
oid = 0
for s in sku.itertuples():
    lead_po = 5                                    # 発注から入荷まで5日
    S = int(np.ceil(s.rate * 2.0 * (7 + lead_po))) + 3   # 週1回、引当可能数＋発注残を S まで戻す
    on_hand = S // 2
    open_orders = []                               # [order_id, qty, ship_due]
    po = {}                                        # 入荷日 -> 数量
    review = int(s.sku[1:]) % 7
    for t in range(DAYS):
        on_hand += po.pop(t, 0)
        # 出荷：予定日を過ぎた注文から、在庫があれば出す（足りなければ残す）
        still = []
        for o in sorted(open_orders, key=lambda x: x[2]):
            if o[2] <= t and on_hand >= o[1]:
                on_hand -= o[1]
                orders[o[0]]["shipped_day"] = t
            else:
                still.append(o)
        open_orders = still
        # 受注
        n_small = rng.poisson(s.rate)
        new = [(int(rng.integers(1, 4)), t + int(rng.integers(1, 4))) for _ in range(n_small)]
        if s.kind == "B" and rng.random() < 0.06:      # 先の日付の大口（10〜30日後に出荷）
            new.append((int(rng.integers(15, 60)), t + int(rng.integers(10, 31))))
        for q, due in new:
            reserved = sum(o[1] for o in open_orders)
            orders.append({"order_id": oid, "sku": s.sku, "ordered_day": t, "qty": q, "due_day": due,
                           "shipped_day": None, "available_at_order": on_hand - reserved, "on_hand_at_order": on_hand})
            open_orders.append([oid, q, due]); oid += 1
        reserved = sum(o[1] for o in open_orders)
        # 発注（週1回）：引当可能数＋発注残で見て S まで
        if t % 7 == review:
            pipe = sum(po.values())
            q = S - (on_hand - reserved + pipe)
            if q > 0:
                po[t + lead_po] = po.get(t + lead_po, 0) + int(q)
        snaps.append((t, s.sku, s.kind, on_hand, reserved, sum(po.values())))

od = pd.DataFrame(orders)
sn = pd.DataFrame(snaps, columns=["day", "sku", "kind", "on_hand", "reserved", "on_order"])
sn["available"] = sn["on_hand"] - sn["reserved"]
sn["projected"] = sn["available"] + sn["on_order"]
to_date = lambda x: (d0 + pd.to_timedelta(x, unit="D")).dt.strftime("%Y-%m-%d")
od_out = od.assign(ordered_on=to_date(od["ordered_day"]), due_on=to_date(od["due_day"]),
                   shipped_on=to_date(od["shipped_day"].astype("float")).where(od["shipped_day"].notna()))
od_out[["order_id", "sku", "ordered_on", "qty", "due_on", "shipped_on"]].to_csv(DATA / "orders.csv", index=False)
sn.assign(snap_date=to_date(sn["day"]))[["snap_date", "sku", "on_hand"]].to_csv(DATA / "stock_snapshot.csv", index=False)
sku[["sku", "kind"]].to_csv(DATA / "items.csv", index=False)

# ---- 2. 欠品の判定 ----
WARM = 28                                          # 最初の4週は立ち上がりなので除く
v = sn[sn.day >= WARM].copy()
v["out_book"] = v["on_hand"] <= 0
v["out_avail"] = v["available"] <= 0
v["out_proj"] = v["projected"] <= 0
v["hidden"] = v["out_avail"] & ~v["out_book"]      # 帳簿では在庫ありだが、使える数は0以下
nd = DAYS - WARM
by_kind = v.groupby("kind").agg(sku_days=("sku", "size"), out_book=("out_book", "sum"), out_avail=("out_avail", "sum"), out_proj=("out_proj", "sum"), hidden=("hidden", "sum"))
per_sku = v.groupby(["sku", "kind"]).agg(out_book=("out_book", "sum"), out_avail=("out_avail", "sum")).reset_index()
daily = v.groupby("day").agg(out_book=("out_book", "sum"), out_avail=("out_avail", "sum"), out_proj=("out_proj", "sum"))

# 帳簿で「在庫あり」と見える日に入った注文のうち、すぐ引き当てられなかったもの
oo = od[od.ordered_day >= WARM]
looks_ok = oo["on_hand_at_order"] >= oo["qty"]
cant = oo["available_at_order"] < oo["qty"]
late = od[(od.ordered_day >= WARM) & od.shipped_day.notna()]
late_rate = float((late.shipped_day > late.due_day).mean() * 100)

# ---- 3. SQL（DuckDB、1スレッド）：受注から引当（未出荷の受注残）を作り直し、引当可能数を出す ----
con = duckdb.connect(); con.execute("SET threads=1")
for t in ["orders", "stock_snapshot"]:
    con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('{DATA / (t + '.csv')}')")
sq = con.execute((SQL / "02_available_duckdb.sql").read_text()).df()
sq["snap_date"] = pd.to_datetime(sq["snap_date"]).dt.strftime("%Y-%m-%d")
chk = sn.assign(snap_date=to_date(sn["day"])).merge(sq, on=["snap_date", "sku"], suffixes=("", "_sql"))
sql_match = bool((chk["reserved"] == chk["reserved_sql"]).all() and (chk["available"] == chk["available_sql"]).all() and len(chk) == len(sn))
sq.groupby("snap_date").agg(out_book=("on_hand", lambda x: int((x <= 0).sum())), out_avail=("available_sql", lambda x: int((x <= 0).sum()))).to_csv(RES / "sql_daily_counts.csv")

res = {"n_sku": 200, "days_used": nd, "period": "2025-01-29〜2025-07-01（最初の4週を除く）",
       "sku_days": int(len(v)),
       "out_book_sku_days": int(v.out_book.sum()), "out_avail_sku_days": int(v.out_avail.sum()),
       "ratio_avail_to_book": round(float(v.out_avail.sum() / v.out_book.sum()), 2),
       "hidden_sku_days": int(v.hidden.sum()),
       "out_proj_sku_days": int(v.out_proj.sum()), "sku_ever_out_proj": int((v.groupby("sku").out_proj.sum() > 0).sum()),
       "late_orders": int((late.shipped_day > late.due_day).sum()), "late_orders_sku": int(late[late.shipped_day > late.due_day].sku.nunique()),
       "sku_ever_out_book": int((per_sku.out_book > 0).sum()), "sku_ever_out_avail": int((per_sku.out_avail > 0).sum()),
       "by_kind": {k: {kk: int(vv) for kk, vv in r.items()} for k, r in by_kind.iterrows()},
       "daily_out_book_mean": round(float(daily.out_book.mean()), 1), "daily_out_avail_mean": round(float(daily.out_avail.mean()), 1),
       "daily_max_gap": int((daily.out_avail - daily.out_book).max()),
       "orders_after_warm": int(len(oo)),
       "orders_looks_ok_but_cannot_allocate": int((looks_ok & cant).sum()),
       "share_of_cannot_allocate_that_looked_ok_pct": round(float((looks_ok & cant).sum() / cant.sum() * 100), 1),
       "orders_cannot_allocate": int(cant.sum()),
       "late_shipment_pct": round(late_rate, 2),
       "sql_match_python": sql_match}
by_kind.to_csv(RES / "by_kind.csv"); per_sku.to_csv(RES / "per_sku.csv", index=False); daily.to_csv(RES / "daily_counts.csv")
json.dump(res, open(RES / "a583_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))

# ---- 4. 図 ----
fig, ax = plt.subplots(figsize=(9, 4))
x = d0 + pd.to_timedelta(daily.index, unit="D")
ax.plot(x, daily.out_avail, color=ORANGE, label="引当可能数が0以下の品目数")
ax.plot(x, daily.out_book, color=BLUE, label="帳簿の在庫（有り高）が0以下の品目数")
ax.plot(x, daily.out_proj, color=GREEN, label="引当可能数＋入荷予定が0以下の品目数")
ax.fill_between(x, daily.out_book, daily.out_avail, color=ORANGE, alpha=0.15, lw=0)
ax.set_ylabel("欠品と判定される品目数（200品目中）"); ax.set_ylim(0, 62)
ax.legend(frameon=False, loc="upper left", ncol=2, fontsize=8.5)
ax.set_title("同じ日の在庫でも、引当を引くと欠品の品目数は何倍になるか")
fig.autofmt_xdate()
save(fig, "a583_daily.png", SRC)

fig, ax = plt.subplots(figsize=(8, 4))
kinds = ["A", "B", "C"]; lab = {"A": "A 小口中心\n（100品目）", "B": "B 先の日付の大口あり\n（60品目）", "C": "C 動きが少ない\n（40品目）"}
xx = np.arange(3); w = 0.27
b1 = [by_kind.loc[k, "out_book"] / by_kind.loc[k, "sku_days"] * 100 for k in kinds]
b2 = [by_kind.loc[k, "out_avail"] / by_kind.loc[k, "sku_days"] * 100 for k in kinds]
b3 = [by_kind.loc[k, "out_proj"] / by_kind.loc[k, "sku_days"] * 100 for k in kinds]
for off, b, c, lb in [(-w, b1, BLUE, "帳簿の在庫で判定"), (0, b2, ORANGE, "引当可能数で判定"), (w, b3, GREEN, "引当可能数＋入荷予定で判定")]:
    ax.bar(xx + off, b, w, color=c, label=lb)
    for i in range(3):
        ax.text(xx[i] + off, b[i] + 0.4, f"{b[i]:.1f}%", ha="center", fontsize=8.5)
ax.set_xticks(xx); ax.set_xticklabels([lab[k] for k in kinds])
ax.set_ylabel("欠品と判定される品目・日の割合（%）"); ax.legend(frameon=False)
ax.set_title("先の日付の大口受注がある品目ほど、判定の差は大きい")
save(fig, "a583_by_kind.png", SRC)

# 例：B の品目で差の大きいもの1つの推移
ex = per_sku[per_sku.kind == "B"].assign(g=lambda d: d.out_avail - d.out_book).sort_values("g").iloc[-1]["sku"]
e = sn[(sn.sku == ex) & (sn.day >= WARM)]
fig, ax = plt.subplots(figsize=(9, 4))
xe = d0 + pd.to_timedelta(e.day, unit="D")
ax.plot(xe, e.on_hand, color=BLUE, label="帳簿の在庫（有り高）")
ax.plot(xe, e.available, color=ORANGE, label="引当可能数（有り高 − 未出荷の受注残）")
ax.plot(xe, e.projected, color=GREEN, lw=1, ls="--", label="引当可能数＋入荷予定（発注残）")
ax.axhline(0, color=INK, lw=0.8)
ax.fill_between(xe, e.available, 0, where=(e.available <= 0) & (e.on_hand > 0), color=ORANGE, alpha=0.25, lw=0, label="帳簿では在庫ありだが、使える数は0以下")
ax.set_ylabel("数量"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title(f"例：品目 {ex}（先の日付の大口受注が入る品目）")
fig.autofmt_xdate()
save(fig, "a583_example.png", SRC)
res["example_sku"] = ex
json.dump(res, open(RES / "a583_main.json", "w"), ensure_ascii=False, indent=1)
