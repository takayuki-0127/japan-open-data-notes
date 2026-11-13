"""531 納期の遵守率は、納期を「当初の約束日」と「変更後の日」のどちらで数えるかで何ポイント違うのか（実務の型）

架空の受注（2025年の1年分）を作る。受注ごとに当初の約束日があり、0〜3回の納期変更が入る。
変更には「早めの変更」（出荷の4日以上前）と「出荷直前の変更」（出荷の3日前以内）がある。
同じ記録を、(A) 当初の約束日、(B) 最後に変えた日、(C) 出荷直前の変更を除いた最後の日、の3通りで数え、
遵守率（約束日までに出荷した割合）を比べる。遵守の判定は Python と SQL（DuckDB）の両方で行い、一致を確かめる。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 531
SRC = "架空の受注記録（作成者が乱数で作成、seed 531）"
LATE_WINDOW = 3            # 出荷の3日前以内の変更を「出荷直前の変更」とする


def make(n=20000, seed=SEED, p_late=0.12):
    """受注と納期変更の記録を作る。p_late：出荷直前に納期を後ろへずらす受注の割合"""
    rng = np.random.default_rng(seed)
    days = pd.date_range("2025-01-06", "2025-12-19", freq="D")
    order_d = days[rng.integers(0, len(days), n)]
    lead = rng.integers(7, 29, n)                                  # 当初の約束までの日数
    promise0 = order_d + pd.to_timedelta(lead, unit="D")
    # 実際の出荷日：当初の約束日の前後にばらつく（遅れ側に少し長い裾）
    dev = np.round(rng.normal(-0.5, 2.2, n) + rng.exponential(1.2, n) * (rng.random(n) < 0.35)).astype(int)
    ship = promise0 + pd.to_timedelta(dev, unit="D")
    ship = pd.DatetimeIndex(np.maximum(ship.values, (order_d + pd.Timedelta(days=2)).values))
    rows = []
    # 早めの変更：受注の30%で1〜2回。客先の都合や部材の見通しで、出荷の4日以上前に約束日を動かす
    early = rng.random(n) < 0.30
    for i in np.where(early)[0]:
        k = rng.integers(1, 3)
        span = (ship[i] - order_d[i]).days - LATE_WINDOW - 1
        if span < 1:
            continue
        for j in range(k):
            ch = order_d[i] + pd.Timedelta(days=int(rng.integers(1, span + 1)))
            # 変更後の日は、その時点の見込みの出荷日に近づける（ずれ ±2日）
            newd = ship[i] + pd.Timedelta(days=int(rng.integers(-1, 3)))
            rows.append((i + 1, ch, newd, "早め"))
    # 出荷直前の変更：遅れそうな受注ほど起きやすい。出荷の0〜3日前に、出荷日以降へ約束日を動かす
    late_gap = (ship - promise0).days.to_numpy()
    w = np.where(late_gap > 0, 3.0, 0.4)
    pl = np.clip(w / w.mean() * p_late, 0, 0.95)
    late = rng.random(n) < pl
    for i in np.where(late)[0]:
        ch = ship[i] - pd.Timedelta(days=int(rng.integers(0, LATE_WINDOW + 1)))
        ch = max(ch, order_d[i] + pd.Timedelta(days=1))
        newd = ship[i] + pd.Timedelta(days=int(rng.integers(0, 3)))
        rows.append((i + 1, ch, newd, "直前"))
    orders = pd.DataFrame({"order_id": np.arange(1, n + 1), "ordered": order_d, "promise_initial": promise0, "shipped": ship})
    ch = pd.DataFrame(rows, columns=["order_id", "changed_on", "new_promise", "kind"]).sort_values(["order_id", "changed_on"], kind="stable", ignore_index=True)
    ch["seq"] = ch.groupby("order_id").cumcount() + 1
    return orders, ch[["order_id", "seq", "changed_on", "new_promise", "kind"]]


def bases(orders, ch):
    """3通りの約束日を受注ごとに出す"""
    o = orders.copy()
    last = ch.sort_values(["order_id", "changed_on", "seq"]).groupby("order_id").tail(1).set_index("order_id").new_promise
    o["promise_last"] = o.order_id.map(last).fillna(o.promise_initial)
    c2 = ch.merge(o[["order_id", "shipped"]], on="order_id")
    c2 = c2[(c2.shipped - c2.changed_on).dt.days > LATE_WINDOW]
    last_ex = c2.sort_values(["order_id", "changed_on", "seq"]).groupby("order_id").tail(1).set_index("order_id").new_promise
    o["promise_ex_late"] = o.order_id.map(last_ex).fillna(o.promise_initial)
    c3 = ch.merge(o[["order_id", "shipped"]], on="order_id")
    late_ids = set(c3.loc[(c3.shipped - c3.changed_on).dt.days <= LATE_WINDOW, "order_id"])
    o["has_late_change"] = o.order_id.isin(late_ids)
    o["has_any_change"] = o.order_id.isin(set(ch.order_id))
    for k, c in [("A", "promise_initial"), ("B", "promise_last"), ("C", "promise_ex_late")]:
        o[f"ok_{k}"] = o.shipped <= o[c]
    return o


def rates(o):
    return {k: round(o[f"ok_{k}"].mean() * 100, 2) for k in "ABC"}


def main():
    orders, ch = make()
    orders.to_csv(DATA / "fictional_orders.csv", index=False, date_format="%Y-%m-%d")
    ch.to_csv(DATA / "fictional_promise_changes.csv", index=False, date_format="%Y-%m-%d")
    o = bases(orders, ch)
    # SQL（DuckDB）で同じ判定をし、Python と一致するか
    con = duckdb.connect(); con.execute("SET threads=1")
    con.register("orders", orders); con.register("changes", ch)
    q = open(SQL / "02_promise_basis_duckdb.sql", encoding="utf-8").read()
    s = con.execute(q).df().sort_values("order_id", ignore_index=True)
    sql_ok = bool((s[["ok_a", "ok_b", "ok_c"]].astype(bool).to_numpy() == o.sort_values("order_id")[["ok_A", "ok_B", "ok_C"]].to_numpy()).all())

    r = rates(o)
    res = {"n_orders": len(o), "n_changes": len(ch), "sql_matches_python": sql_ok,
           "share_any_change_pct": round(o.has_any_change.mean() * 100, 1),
           "share_late_change_pct": round(o.has_late_change.mean() * 100, 1),
           "rate_pct": {"A_当初の約束日": r["A"], "B_最後に変えた日": r["B"], "C_直前の変更を除く": r["C"]},
           "gap_B_minus_A_pt": round(r["B"] - r["A"], 2), "gap_C_minus_A_pt": round(r["C"] - r["A"], 2), "gap_B_minus_C_pt": round(r["B"] - r["C"], 2)}
    # 区分別：変更なし・早めの変更だけ・直前の変更あり
    o["grp"] = np.where(o.has_late_change, "直前の変更あり", np.where(o.has_any_change, "早めの変更だけ", "変更なし"))
    gr = []
    for g in ["変更なし", "早めの変更だけ", "直前の変更あり"]:
        x = o[o.grp == g]
        gr.append({"区分": g, "件数": len(x), **{f"{k}(%)": round(x[f"ok_{k}"].mean() * 100, 1) for k in "ABC"}})
    pd.DataFrame(gr).to_csv(RES / "rate_by_change_group.csv", index=False); res["by_group"] = gr
    # 月別
    o["m"] = o.ordered.dt.month
    mon = o.groupby("m")[["ok_A", "ok_B", "ok_C"]].mean().mul(100).round(1).reset_index()
    mon.columns = ["受注月", "A(%)", "B(%)", "C(%)"]; mon.to_csv(RES / "rate_by_month.csv", index=False)
    res["month_range_pct"] = {k: [float(mon[f"{k}(%)"].min()), float(mon[f"{k}(%)"].max())] for k in "ABC"}
    # 直前の変更の起きやすさを変えたシミュレーション（同じ seed で p_late だけ変える）
    sim = []
    for pl in [0.0, 0.03, 0.06, 0.09, 0.12, 0.15, 0.18, 0.21, 0.24]:
        oo = bases(*make(seed=SEED, p_late=pl))
        rr = rates(oo)
        sim.append({"p_late": pl, "直前の変更の割合(%)": round(oo.has_late_change.mean() * 100, 1), **{f"{k}(%)": rr[k] for k in "ABC"},
                    "B-A(pt)": round(rr["B"] - rr["A"], 2), "B-C(pt)": round(rr["B"] - rr["C"], 2)})
    sm = pd.DataFrame(sim); sm.to_csv(RES / "gap_vs_late_change_share.csv", index=False); res["simulation"] = sim
    slope = np.polyfit(sm["直前の変更の割合(%)"], sm["B-C(pt)"], 1)[0]
    res["slope_BminusC_per_1pt_late"] = round(float(slope), 3)
    pd.DataFrame([{"基準": k, "遵守率(%)": v} for k, v in res["rate_pct"].items()]).to_csv(RES / "rate_by_basis.csv", index=False)
    json.dump(res, open(RES / "a531_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：3通りの遵守率
    fig, ax = plt.subplots(figsize=(7, 3.6))
    lab = ["A 当初の約束日", "B 最後に変えた日", "C 直前の変更を除く"]
    v = [r["A"], r["B"], r["C"]]
    ax.barh(lab[::-1], v[::-1], color=[GREEN, ORANGE, BLUE][::-1])
    for i, x in enumerate(v[::-1]):
        ax.text(x + 0.5, i, f"{x:.1f}%", va="center", color=INK)
    ax.set_xlim(0, 105); ax.set_xlabel("遵守率（約束日までに出荷した割合、%）")
    ax.set_title("同じ受注20,000件でも、数える約束日で遵守率が変わる")
    save(fig, "a531_rate_by_basis.png", SRC)
    # 図2：区分別
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    xs = np.arange(3); wd = 0.26
    for j, (k, c) in enumerate(zip("ABC", [GREEN, ORANGE, BLUE])):
        ax.bar(xs + (j - 1) * wd, [g[f"{k}(%)"] for g in gr], wd, color=c, label=lab[j])
    ax.set_xticks(xs, [f"{g['区分']}\n（{g['件数']:,}件）" for g in gr]); ax.set_ylim(0, 120); ax.set_yticks(range(0, 101, 20)); ax.set_ylabel("遵守率（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper center", ncol=3); ax.set_title("差が出るのは、納期を変えた受注だけ")
    save(fig, "a531_rate_by_group.png", SRC)
    # 図3：直前の変更の割合と差
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.plot(sm["直前の変更の割合(%)"], sm["B-A(pt)"], "o-", color=ORANGE, label="B − A（変更後の日 − 当初の日）")
    ax.plot(sm["直前の変更の割合(%)"], sm["B-C(pt)"], "s-", color=BLUE, label="B − C（直前の変更を入れるか）")
    ax.set_xlabel("出荷の3日前以内に納期を変えた受注の割合（%）"); ax.set_ylabel("遵守率の差（ポイント）")
    ax.legend(frameon=False, fontsize=9); ax.set_title("直前の変更が多いほど、「変更後の日」の遵守率は高く出る")
    save(fig, "a531_gap_vs_late_share.png", SRC)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
