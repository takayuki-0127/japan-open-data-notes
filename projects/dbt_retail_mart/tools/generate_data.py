"""架空の小売「みどりマート（架空）」の合成データを作る（F275 の 01 と同じ中身。出力先だけ data/ に変えた）。
本番用（2024-04〜2026-03、13店）と、答え合わせ用の小さなデータ（境目のケース入り）。
使い方: python3 tools/generate_data.py [seed]   （既定 seed=2751）
出力: data/main_<seed>/*.csv.gz, data/fixture_<seed>/*.csv.gz, data/fixture_plain_<seed>/（境目のケースなし）
"""
import sys, os, datetime as dt
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 2751
D0, D1 = dt.date(2024, 4, 1), dt.date(2026, 3, 31)


def dk(d):
    return d.year * 10000 + d.month * 100 + d.day


def calendar():
    rows = []
    d = dt.date(2010, 1, 1)
    while d <= dt.date(2026, 12, 31):
        fy, fm = d.year, d.month
        if d.day >= 21:  # 21日締め：21日以降は翌月の会計月
            fm += 1
            if fm == 13:
                fy, fm = fy + 1, 1
        rows.append((dk(d), d.year * 100 + d.month, d.year * 12 + d.month - 1, fy * 100 + fm, fy * 12 + fm - 1))
        d += dt.timedelta(days=1)
    return pd.DataFrame(rows, columns=["date_key", "cal_ym", "cal_mi", "fis_ym", "fis_mi"])


def masters():
    store = pd.DataFrame({
        "store_id": list(range(1, 13)) + [99],
        "open_date_key": [20180401, 20180415, 20190301, 20190920, 20200110, 20200701, 20210201, 20210821, 20220315,
                          20240610, 20241121, 20250401, 20230101],
        "is_test": [0] * 12 + [1],
        "size": [1.0, 1.2, 0.8, 1.1, 0.9, 1.3, 0.7, 1.0, 1.1, 0.9, 1.0, 0.8, 0.1],
    })
    rng = np.random.default_rng(275)
    item = pd.DataFrame({"item_id": np.arange(1, 201), "dept_id": rng.integers(1, 9, 200),
                         "price": rng.integers(10, 101, 200) * 10})
    dept = pd.DataFrame({"dept_id": np.arange(1, 9),
                         "dept_name": ["青果", "鮮魚精肉", "加工食品", "菓子", "日配", "日用品", "医薬・化粧", "その他"]})
    return store, item, dept


def gen_sales(store, item, days, rate, rng, member_pool=500, p_member=0.6):
    """店×日ごとにレシートを作り、明細・返品をつける"""
    rec, lines, rets = [], [], []
    rid = 0
    items = item.to_numpy()
    for _, s in store.iterrows():
        sid = int(s.store_id)
        for d in days:
            if dk(d) < s.open_date_key:
                continue
            lam = rate * s["size"] * (1.25 if d.weekday() >= 5 else 1.0)
            n = rng.poisson(lam)
            for _ in range(n):
                rid += 1
                mem = int(sid * 10000 + rng.integers(1, member_pool + 1)) if rng.random() < p_member else None
                rec.append((rid, dk(d), sid, mem))
                for ln in range(1, 2 + rng.poisson(1.0)):
                    it = items[rng.integers(0, len(items))]
                    qty = 1 + rng.poisson(0.3)
                    amt = int(it[2]) * qty
                    tax = 8 if it[1] <= 5 else 10
                    u = rng.random()
                    st = "ok" if u < 0.97 else ("cancel" if u < 0.99 else "void")
                    lines.append((rid, ln, dk(d), sid, int(it[0]), amt, tax, st))
                    if st == "ok" and rng.random() < 0.02:
                        rd = d + dt.timedelta(days=int(rng.integers(0, 11)))
                        if rd <= D1:
                            rets.append((rid, ln, dk(rd), amt))
    receipt = pd.DataFrame(rec, columns=["receipt_id", "date_key", "store_id", "member_id"])
    receipt["member_id"] = receipt["member_id"].astype("Int64")
    sl = pd.DataFrame(lines, columns=["receipt_id", "line_no", "date_key", "store_id", "item_id", "amount_incl", "tax_pct", "status"])
    rl = pd.DataFrame(rets, columns=["receipt_id", "line_no", "return_date_key", "amount_incl"])
    return receipt, sl, rl


def boundary_rows(receipt, sl, rl, item):
    """答え合わせ用：定義の境目に当たる行を足す（どの変更依頼でも結果が動くように）"""
    rid = int(receipt.receipt_id.max()) + 1000
    it5 = int(item[item.dept_id == 5].item_id.iloc[0]); it8 = int(item[item.dept_id == 8].item_id.iloc[0])
    it1 = int(item[item.dept_id == 1].item_id.iloc[0]); it6 = int(item[item.dept_id == 6].item_id.iloc[0])
    R, L, T = [], [], []
    def add(d, sid, mem, its, st="ok"):
        nonlocal rid
        rid += 1
        R.append((rid, d, sid, mem))
        for i, (it, amt, tax) in enumerate(its, 1):
            L.append((rid, i, d, sid, it, amt, tax, st))
        return rid
    # 月末に売って翌月に返品（返品の計上月で動く）、20日に売って21日に返品（会計月で動く）
    r = add(20250331, 1, None, [(it1, 1000, 8)]); T.append((r, 1, 20250402, 1000))
    r = add(20250620, 2, None, [(it6, 2200, 10)]); T.append((r, 1, 20250621, 2200))
    # 20日と21日の売上（会計月で動く）
    add(20251020, 1, 10001, [(it6, 3300, 10)]); add(20251021, 1, 10002, [(it1, 1080, 8)])
    # void だけのレシート（CR6 で客数・売上が動く）、cancel だけのレシート
    add(20250910, 1, 10003, [(it6, 5500, 10)], st="void"); add(20250910, 2, 20001, [(it6, 4400, 10)], st="cancel")
    # 同じ会員が同じ日に2回（CR8 で客数が動く）、会員なしのレシート
    add(20251105, 3, 30005, [(it5, 500, 8)]); add(20251105, 3, 30005, [(it8, 1100, 10)]); add(20251105, 3, None, [(it8, 220, 10)])
    # 部門5・8（CR7 で部門のまとめ方が動く）
    add(20250715, 2, None, [(it5, 864, 8), (it8, 1650, 10)])
    # テスト店の売上（CR5 で動く）
    add(20250801, 99, None, [(it1, 7777, 8)]); add(20240801, 99, None, [(it1, 3333, 8)])
    receipt = pd.concat([receipt, pd.DataFrame(R, columns=receipt.columns)], ignore_index=True)
    receipt["member_id"] = receipt["member_id"].astype("Int64")
    sl = pd.concat([sl, pd.DataFrame(L, columns=sl.columns)], ignore_index=True)
    rl = pd.concat([rl, pd.DataFrame(T, columns=rl.columns)], ignore_index=True)
    return receipt, sl, rl


def save(name, tabs):
    p = os.path.join(ROOT, "data", name)
    os.makedirs(p, exist_ok=True)
    for k, v in tabs.items():
        v.to_csv(os.path.join(p, f"{k}.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
    print(name, {k: len(v) for k, v in tabs.items()})


def main():
    cal = calendar()
    store, item, dept = masters()
    days = [D0 + dt.timedelta(days=i) for i in range((D1 - D0).days + 1)]
    rng = np.random.default_rng(SEED)
    rc, sl, rl = gen_sales(store, item, days, 15.0, rng)
    common = {"calendar": cal, "store": store.drop(columns="size"), "item": item.drop(columns="price"), "dept": dept}
    save(f"main_{SEED}", {**common, "receipt": rc, "sales_line": sl, "returns_line": rl})
    # 答え合わせ用：店1・2・3（開店が既存店の境目に当たる店も）とテスト店、ほぼ週1件
    fstore = pd.DataFrame({"store_id": [1, 2, 3, 99], "open_date_key": [20180401, 20240410, 20240525, 20230101],
                           "is_test": [0, 0, 0, 1], "size": [1.0, 1.0, 1.0, 1.0]})
    rng2 = np.random.default_rng(SEED + 1)
    frc, fsl, frl = gen_sales(fstore[fstore.store_id != 99], item, days, 0.15, rng2, member_pool=20)
    fcommon = {**common, "store": fstore.drop(columns="size")}
    save(f"fixture_plain_{SEED}", {**fcommon, "receipt": frc, "sales_line": fsl, "returns_line": frl})
    brc, bsl, brl = boundary_rows(frc, fsl, frl, item)
    save(f"fixture_{SEED}", {**fcommon, "receipt": brc, "sales_line": bsl, "returns_line": brl})


if __name__ == "__main__":
    main()
