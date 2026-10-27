"""F38 分析：訪日客の消費1兆円が生む生産・付加価値・雇用（産業連関分析）。
python src/03_分析.py  → results/*.csv, results/summary.json
"""
import json
import numpy as np, pandas as pd
from common import ROOT, RES, load_table, matrices, employment_coef, purchaser_shares

TOTAL = 1000.0          # 1兆円＝1,000十億円
C_RATE = 0.60           # 消費転換係数（雇用者所得のうち消費に回る割合、基本の仮定）

inb = pd.read_csv(ROOT / "data/raw/inbound_2025_ref2.csv")
inb["小費目"] = inb["小費目"].fillna(inb["費目"])
mp = pd.read_csv(ROOT / "data/mapping_item_to_sector.csv", dtype={"部門コード": str, "部門コード_別案": str})
inb = inb.merge(mp, on="小費目", how="left")
assert inb["部門コード"].notna().all()
inb["金額"] = inb["消費単価_円"] / inb["消費単価_円"].sum() * TOTAL   # 十億円


def demand_vector(t, code_col="部門コード", margin=True, ps=None):
    """1兆円（購入者価格）を、部門別の最終需要（生産者価格）に直す。"""
    idx = {s: i for i, s in enumerate(t["sec"])}
    f = np.zeros(len(t["sec"]))
    for _, r in inb.iterrows():
        s = r[code_col]; y = r["金額"]
        if r["種別"] == "商品" and margin:
            p = ps[s]
            share = p["prod"] / p["purch"] if p["purch"] > 0 else 1.0
            share = min(max(share, 0), 1)
            mg = y * (1 - share)
            tot = p["cm"] + p["fr"]
            cm_share = p["cm"] / tot if tot > 0 else 1.0
            f[idx[s]] += y * share
            f[idx["511"]] += mg * cm_share
            f[idx["572"]] += mg * (1 - cm_share)
        elif r["種別"] == "商品":
            f[idx[s]] += y
        else:
            f[idx[s]] += y
    return f


def ripple(t, mt, f, c_rate=C_RATE, imports=True, second=True, ecoef=None):
    I = mt["I"]; M = mt["M"]
    if imports:
        fd = (I - M) @ f
        X1 = mt["B"] @ fd
    else:
        fd = f.copy()
        X1 = mt["B0"] @ fd
    direct = fd
    first = X1 - direct
    W1 = mt["w"] @ X1
    if second:
        Cv = c_rate * W1 * mt["h"]
        X2 = (mt["B"] @ ((I - M) @ Cv)) if imports else (mt["B0"] @ Cv)
    else:
        X2 = np.zeros_like(X1)
    out = dict(direct=direct, first=first, second=X2, total=X1 + X2,
               leak=f.sum() - fd.sum(), W1=W1)
    out["VA"] = mt["v"] @ out["total"]
    if ecoef is not None:
        out["L"] = ecoef @ out["total"]
        out["L_by"] = ecoef * out["total"]
    return out


t20 = load_table("2020"); m20 = matrices(t20)
e20 = employment_coef(t20)
ps = purchaser_shares(t20)
f = demand_vector(t20, ps=ps)
base = ripple(t20, m20, f, ecoef=e20)

summary = {
    "最終需要_購入者価格": TOTAL,
    "最終需要_生産者価格": float(f.sum()),
    "うち商業マージン": float(f[t20["sec"].index("511")]),
    "輸入に漏れた分": float(base["leak"]),
    "直接効果": float(base["direct"].sum()),
    "1次波及": float(base["first"].sum()),
    "2次波及": float(base["second"].sum()),
    "生産誘発_合計": float(base["total"].sum()),
    "波及倍率": float(base["total"].sum() / TOTAL),
    "粗付加価値誘発": float(base["VA"]),
    "雇用者所得_1次まで": float(base["W1"]),
    "雇用誘発_人": float(base["L"]),
}

# 部門別
df = pd.DataFrame({"部門コード": t20["sec"], "部門": t20["name"], "最終需要_生産者価格": f,
                   "直接効果": base["direct"], "1次波及": base["first"], "2次波及": base["second"],
                   "生産誘発_合計": base["total"], "雇用誘発_人": base["L_by"], "輸入係数": m20["m"]})
df.sort_values("生産誘発_合計", ascending=False).to_csv(RES / "by_sector_2020.csv", index=False, encoding="utf-8-sig")

# 費目ごとに1兆円ずつ使った場合
rows = []
for cat, g in inb.groupby("費目", sort=False):
    sub = inb.copy(); sub["金額"] = np.where(sub["費目"] == cat, sub["消費単価_円"], 0.0)
    if sub["金額"].sum() == 0:
        continue
    sub["金額"] = sub["金額"] / sub["金額"].sum() * TOTAL
    keep = inb["金額"].copy(); inb["金額"] = sub["金額"]
    fc = demand_vector(t20, ps=ps); r = ripple(t20, m20, fc, ecoef=e20)
    inb["金額"] = keep
    rows.append(dict(費目=cat, 構成比=g["構成比_pct"].sum(), 国内に残る直接需要=r["direct"].sum(),
                     生産誘発_合計=r["total"].sum(), 波及倍率=r["total"].sum() / TOTAL,
                     粗付加価値=r["VA"], 雇用誘発_人=r["L"]))
cats = pd.DataFrame(rows); cats.to_csv(RES / "by_category_2020.csv", index=False, encoding="utf-8-sig")

# 頑健性・前提の違い
rob = []
def add(label, r):
    rob.append(dict(設定=label, 直接効果=r["direct"].sum(), 一次波及=r["first"].sum(), 二次波及=r["second"].sum(),
                    生産誘発_合計=r["total"].sum(), 波及倍率=r["total"].sum() / TOTAL,
                    粗付加価値=r["VA"], 雇用誘発_人=r.get("L", np.nan)))
add("基本（2020年表・競争輸入型・2次まで・消費転換0.6）", base)
add("2次波及を含めない", ripple(t20, m20, f, second=False, ecoef=e20))
add("消費転換係数0.5", ripple(t20, m20, f, c_rate=0.5, ecoef=e20))
add("消費転換係数0.7", ripple(t20, m20, f, c_rate=0.7, ecoef=e20))
add("輸入を考えない（閉鎖型）", ripple(t20, m20, f, imports=False, ecoef=e20))
f_nm = demand_vector(t20, margin=False, ps=ps)
add("買物代を生産者価格に直さない", ripple(t20, m20, f_nm, ecoef=e20))
f_alt = demand_vector(t20, code_col="部門コード_別案", ps=ps)
add("費目の対応のさせ方を変える（別案）", ripple(t20, m20, f_alt, ecoef=e20))
add("輸入を考えない＋生産者価格に直さない＋2次まで（最大）", ripple(t20, m20, f_nm, imports=False, ecoef=e20))
# 2015年表（雇用表は統合中分類がないので、雇用は2020年の係数を当てはめず空欄）
t15 = load_table("2015"); m15 = matrices(t15)
f15 = demand_vector(t15, ps=ps)
r15 = ripple(t15, m15, f15)
add("2015年表", r15)
rb = pd.DataFrame(rob); rb.to_csv(RES / "robustness.csv", index=False, encoding="utf-8-sig")

summary["2015年表_波及倍率"] = float(r15["total"].sum() / TOTAL)
summary["2020_国内生産額_十億円"] = float(t20["X"].sum())
summary["2015_国内生産額_十億円"] = float(t15["X"].sum())
summary["従業者総数_2020"] = float((e20 * t20["X"]).sum())
summary["2020年表_宿泊業_国内生産額"] = float(t20["X"][t20["sec"].index("671")])
summary["2015年表_宿泊業_国内生産額"] = float(t15["X"][t15["sec"].index("671")])
json.dump(summary, open(RES / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))
print(cats.round(3).to_string())
print(rb.round(3).to_string())
print(df.sort_values("生産誘発_合計", ascending=False).head(15).round(2).to_string())
