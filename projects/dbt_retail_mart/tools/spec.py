"""8本のレポートの「正しい答え」を、dbt の SQL とは別に pandas で計算する（F275 の spec と同じ中身）。"""
import numpy as np, pandas as pd


def load(path):
    import os
    t = {}
    for k in ["calendar", "store", "item", "dept", "receipt", "sales_line", "returns_line"]:
        t[k] = pd.read_csv(os.path.join(path, f"{k}.csv.gz"))
    t["receipt"]["member_id"] = t["receipt"]["member_id"].astype("Int64")
    return t


def reports(t, P):
    cal = t["calendar"]
    ycol, mcol = ("cal_ym", "cal_mi") if P["mon"] == "cal" else ("fis_ym", "fis_mi")
    mon = cal[["date_key", ycol, mcol]].rename(columns={ycol: "ym", mcol: "mi"})
    bad = {"cancel"} if P["st"] == "cancel" else {"cancel", "void"}
    sl = t["sales_line"]
    ok = sl[~sl.status.isin(bad)].copy()
    if P["test"]:
        ok = ok[ok.store_id.isin(t["store"].loc[t["store"].is_test == 0, "store_id"])]
    ok["fac"] = 100.0 / (100 + ok.tax_pct) if P["tax"] else 1.0
    s_part = pd.DataFrame({"d": ok.date_key, "store_id": ok.store_id, "item_id": ok.item_id, "amt": ok.amount_incl * ok.fac})
    r = t["returns_line"].merge(ok, on=["receipt_id", "line_no"], suffixes=("_r", ""))
    rd = r.return_date_key if P["ret"] == "return" else r.date_key
    r_part = pd.DataFrame({"d": rd, "store_id": r.store_id, "item_id": r.item_id, "amt": -r.amount_incl_r * r.fac})
    net = pd.concat([s_part, r_part], ignore_index=True).merge(mon, left_on="d", right_on="date_key")
    grp_map = ({1: "生鮮", 2: "生鮮", 3: "加工食品", 4: "加工食品", 5: "日配", 6: "日用品", 7: "日用品"} if P["grp"] == "old"
               else {1: "生鮮・日配", 2: "生鮮・日配", 5: "生鮮・日配", 3: "加工食品", 4: "加工食品", 6: "日用品", 7: "日用品", 8: "日用品"})
    dg = t["dept"].assign(grp=lambda x: x.dept_id.map(grp_map).fillna("その他"))[["dept_id", "grp"]]
    netg = net.merge(t["item"], on="item_id").merge(dg, on="dept_id")
    out = {}
    R1 = net.groupby("ym", as_index=False).amt.sum().rename(columns={"amt": "sales"})
    out["R1"] = R1
    out["R2"] = net.groupby(["ym", "store_id"], as_index=False).amt.sum().rename(columns={"amt": "sales"})
    out["R3"] = netg.groupby(["ym", "grp"], as_index=False).amt.sum().rename(columns={"amt": "sales"})
    out["R6"] = netg.groupby(["ym", "store_id", "grp"], as_index=False).amt.sum().rename(columns={"amt": "sales"})
    sm = net.groupby(["ym", "mi", "store_id"], as_index=False).amt.sum().rename(columns={"amt": "sales"})
    op = t["store"].merge(mon, left_on="open_date_key", right_on="date_key")[["store_id", "mi"]].rename(columns={"mi": "open_mi"})
    a = sm.merge(op, on="store_id")
    a = a[a.open_mi <= a.mi - P["gap"]]
    b = sm.rename(columns={"sales": "sales_ly", "ym": "ym_ly"}).assign(mi=lambda x: x.mi + 12)
    ab = a.merge(b[["store_id", "mi", "sales_ly"]], on=["store_id", "mi"])
    R4 = ab.groupby("ym", as_index=False).agg(comp_sales=("sales", "sum"), comp_sales_ly=("sales_ly", "sum"))
    R4["yoy"] = R4.comp_sales / R4.comp_sales_ly - 1
    out["R4"] = R4
    rc = t["receipt"][t["receipt"].receipt_id.isin(ok.receipt_id)].copy()
    if P["cust"] == "receipt":
        rc["key"] = rc.receipt_id.astype("int64")
    else:
        m = rc.member_id
        rc["key"] = np.where(m.isna(), -rc.receipt_id.astype("int64"), m.fillna(0).astype("int64") * 100000000 + rc.date_key)
    cu = rc.merge(mon, on="date_key").groupby("ym", as_index=False).key.nunique().rename(columns={"key": "customers"})
    R5 = R1.merge(cu, on="ym")
    R5["ticket"] = R5.sales / R5.customers
    out["R5"] = R5
    R7 = R5.merge(R4[["ym", "yoy"]].rename(columns={"yoy": "comp_yoy"}), on="ym", how="left")
    out["R7"] = R7
    last = net.ym.max()
    out["R8"] = net[net.ym == last].groupby("d", as_index=False).amt.sum().rename(columns={"d": "date_key", "amt": "sales"})
    return out
