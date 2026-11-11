"""233：架空の通販会社の注文データを作る（乱数、seed 固定）。実在の会社・業務とは関係ない"""
import numpy as np, pandas as pd
from common import DATA
rng = np.random.default_rng(233)
N_CUST, N_ORD = 6000, 24000
cust = pd.DataFrame({"customer_id": np.arange(1, N_CUST + 1),
                     "prefecture": rng.choice(["東京都", "神奈川県", "大阪府", "愛知県", "福岡県", "北海道", "その他"], N_CUST,
                                              p=[.2, .12, .12, .1, .08, .08, .3])})
# 住所：引っ越した顧客（約7%）は住所が2件。is_primary=1 が今の住所
moved = rng.random(N_CUST) < 0.07
addr = [{"customer_id": c, "address_id": 1, "is_primary": 0 if m else 1} for c, m in zip(cust.customer_id, moved)]
addr += [{"customer_id": c, "address_id": 2, "is_primary": 1} for c, m in zip(cust.customer_id, moved) if m]
addr = pd.DataFrame(addr)
stores = pd.DataFrame({"store_id": [1, 2, 3, 4], "store_name": ["東店", "西店", "南店", "北店"]})
# 注文：2026-02-15〜2026-04-15。ネット注文（約12%）は store_id が NULL。取消は約4%
start = pd.Timestamp("2026-02-15")
sec = rng.integers(0, 60 * 86400, N_ORD)
ordered_at = (start + pd.to_timedelta(sec, unit="s")).floor("s")
store = rng.choice([1, 2, 3, 4], N_ORD).astype("float")
store[rng.random(N_ORD) < 0.12] = np.nan
orders = pd.DataFrame({"order_id": np.arange(100001, 100001 + N_ORD), "customer_id": rng.integers(1, N_CUST + 1, N_ORD),
                       "store_id": pd.array(store, dtype="Int64"), "ordered_at": ordered_at,
                       "status": np.where(rng.random(N_ORD) < 0.04, "取消", "完了")}).sort_values("ordered_at")
lines = []
for oid in orders.order_id:
    for ln in range(1, rng.integers(1, 6) + 1):
        food = rng.random() < 0.35
        lines.append((oid, ln, int(rng.integers(1, 400)), int(rng.integers(1, 4)), int(rng.choice([98, 148, 298, 480, 980, 1480, 2980, 4980])),
                      0.08 if food else 0.10))
lines = pd.DataFrame(lines, columns=["order_id", "line_no", "item_id", "qty", "unit_price", "tax_rate"])
for name, d in {"customers": cust, "customer_addresses": addr, "stores": stores, "orders": orders, "order_lines": lines}.items():
    d.to_csv(DATA / f"{name}.csv", index=False)
print({k: len(v) for k, v in {"customers": cust, "addr": addr, "orders": orders, "lines": lines}.items()})
