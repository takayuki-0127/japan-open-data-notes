"""02 整形：予算づくりに使う「店×月」の表を作る。

- 元は F246 の合成のコード gen(seed)（data/f246/src/02_整形.py、コミット 3006b82）。**コードは書き換えずに読み込む。**
- gen(seed) は FY2022〜FY2025（2026年3月まで）しか作らない。この回では予算を立てたあとの「答え合わせ」のため、
  同じ設定のまま 2026年4〜8月（FY2026 の最初の5か月）を足した（gen_ext）。
  - gen(seed) が使った乱数の流れをそのまま受け取り、そのあとの乱数で5か月分を作る。
    なので FY2022〜FY2025 の数字は gen(seed) と1円もずれない（main() で確かめる）。
  - 2026年4〜8月の「市場の量」は、商業動態統計（スーパー）の実際の値から作る（F246 の作り方と同じ）。
  - 物価は F246 の仮定（2026年も年 +4%）のまま。**答え合わせのうち、物価の部分は仮定どうしの比べになる。**
- 出力：
  - data/store_month_seeds.csv.gz … 店×月（2022-04〜2026-08）、乱数の種 0〜19
  - data/industry_super_monthly.csv … 商業動態統計（スーパー、合計、百万円、2014-01〜2026-08）
  - results/02_check.json … mart（F247）・gen（F246）との照合
"""
import importlib.util, json, pathlib, types
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
F246 = ROOT / "data" / "f246" / "src" / "02_整形.py"
MART = ROOT / "data" / "mart"
EXT_START, EXT_END = "2026-04-01", "2026-08-31"
SEEDS = range(20)


def load_gen_module():
    s = importlib.util.spec_from_file_location("f246gen", F246)
    g = importlib.util.module_from_spec(s); s.loader.exec_module(g)
    return g


class _RecRng:
    """乱数の生成器を包んで、呼ばれた順に結果を記録する（中身の乱数は変えない）。"""
    def __init__(self, rng):
        self.rng, self.calls = rng, []

    def __getattr__(self, name):
        f = getattr(self.rng, name)
        def w(*a, **k):
            r = f(*a, **k); self.calls.append((name, a, k, r)); return r
        return w


def gen_ext(g, seed):
    """F246 の gen(seed) をそのまま動かし、同じ乱数の続きで 2026-04〜08 の店×日を足す。"""
    box = {}
    real_np = np

    class _Random:
        def __getattr__(self, n):
            return getattr(real_np.random, n)
        def default_rng(self, s=None):
            box["r"] = _RecRng(real_np.random.default_rng(s)); return box["r"]

    class _NP:
        random = _Random()
        def __getattr__(self, n):
            return getattr(real_np, n)

    g.np = _NP()
    try:
        cal, fsd, fsdc, fmm, ec = g.gen(seed)
    finally:
        g.np = real_np
    rec = box["r"]; rng = rec.rng
    calls = rec.calls
    store_re = calls[0][3]
    st_w_draw = [c for c in calls if c[0] == "normal" and c[1][:2] == (0, 0.30)][0][3]
    STORES = g.STORES
    st_w = pd.Series(np.exp(st_w_draw), index=STORES.store_id)

    # 5か月分の暦と、市場の量・物価（F246 の _indices をそのまま使う）
    calx = pd.read_csv(g.RAW / "calendar_daily.csv.gz", parse_dates=["date"])
    calx = calx[(calx.date >= g.START) & (calx.date <= EXT_END)].reset_index(drop=True)
    calx["ym"] = calx.date.dt.strftime("%Y-%m")
    calx["fy"] = np.where(calx.date.dt.month >= 4, calx.date.dt.year, calx.date.dt.year - 1)
    calx["flyer"] = calx.dow.isin([2, 5])
    pm, vol = g._indices(calx)
    ce = calx[calx.date >= EXT_START].reset_index(drop=True)
    nd, ns = len(ce), len(STORES)
    t_year = ((ce.date - pd.Timestamp(g.START)).dt.days / 365.25).values
    dow = g.DOW[ce.dow.values]
    hol = np.where(ce.hol.values & (ce.dow.values < 5), 1.07, 1.0)
    year_end = np.ones(nd)
    flyer = np.where(ce.flyer.values, 1.07, 1.0)
    volm = vol.reindex(ce.ym).values
    pmd = pm.reindex(ce.ym).values
    store_month = rng.normal(0, 0.02, (ns, ce.ym.nunique()))
    ym_codes = pd.factorize(ce.ym)[0]
    rows = []
    for j, st in STORES.iterrows():
        if pd.notna(st.close_date) and st.close_date < pd.Timestamp(EXT_START):
            continue
        days_open = (ce.date - st.open_date).dt.days.values
        ramp = np.where(days_open < 0, 0, np.clip(0.75 + 0.25 * days_open / 180, 0.75, 1.0))
        ramp = np.where(days_open < 14, ramp * 1.30, ramp)
        if st.open_date < pd.Timestamp(g.START):
            ramp = np.ones(nd)
        trend = np.exp(g.AREA_TREND[st.area] * t_year)
        lam = g.BASE_REC[st["size"]] * np.exp(store_re[j]) * trend * dow * hol * year_end * flyer * volm ** 0.85 * ramp
        lam = lam * np.exp(store_month[j, ym_codes]) * np.exp(rng.normal(0, 0.05, nd))
        receipts = rng.poisson(np.maximum(lam, 1))
        items_per = g.AREA_ITEMS[st.area] * (volm ** 0.15) * (pmd ** -0.25) * np.exp(rng.normal(0, 0.03, nd))
        items = np.round(receipts * items_per)
        unit_price = 228 * g.AREA_PRICE[st.area] * pmd * np.where(ce.flyer.values, 0.985, 1.0) * np.exp(rng.normal(0, 0.02, nd))
        sales = items * unit_price
        wage = 1150 * np.exp(0.04 * t_year) * (1.08 if st.area == "都市" else 1.0)
        labor_hours = (g.LABOR_BASE[st["size"]] + 0.030 * receipts) * np.exp(rng.normal(0, 0.03, nd))
        other = (260000 if st["size"] == "S" else 340000 if st["size"] == "M" else 460000) * np.exp(0.02 * t_year)
        rows.append(pd.DataFrame({"date": ce.date, "store_id": st.store_id, "receipts": receipts, "items": items,
                                  "sales": sales, "labor_hours": labor_hours, "labor_cost": labor_hours * wage,
                                  "other_cost": other, "flyer": ce.flyer.values}))
    fx = pd.concat(rows, ignore_index=True)
    C = g.CATS; n = len(fx)
    share = C.share.values * np.exp(rng.normal(0, 0.05, (n, len(C))))
    share = share / share.sum(1, keepdims=True)
    csales = fx.sales.values[:, None] * share
    marg = C.margin.values[None, :] - 0.01 * (fx.flyer.values[:, None] * C.promo.values[None, :])
    rural = fx.store_id.map(STORES.set_index("store_id").area).eq("地方").values
    wmult = st_w.reindex(fx.store_id).values * np.where(rural, 1.25, 1.0)   # FY2025 からの地方の廃棄の悪化は続く（F246 の設定のまま）
    waste_r = C.waste.values[None, :] * wmult[:, None] * np.exp(rng.normal(0, 0.25, (n, len(C))))
    fx["gross_profit_before_waste"] = (csales * marg).sum(1)
    fx["waste"] = (csales * waste_r).sum(1)
    fx["gross_profit"] = fx.gross_profit_before_waste - fx.waste
    keep = ["date", "store_id", "receipts", "items", "sales", "labor_hours", "labor_cost", "other_cost",
            "gross_profit_before_waste", "waste", "gross_profit"]
    return pd.concat([fsd[keep], fx[keep]], ignore_index=True)


SUM = ["sales", "receipts", "items", "gross_profit_before_waste", "waste", "gross_profit",
       "labor_hours", "labor_cost", "other_cost"]


def to_month(d):
    d = d.copy(); d["ym"] = d.date.dt.strftime("%Y-%m")
    m = d.groupby(["ym", "store_id"], as_index=False)[SUM].sum()
    m["days"] = d.groupby(["ym", "store_id"]).size().values
    m["operating_profit"] = m.gross_profit - m.labor_cost - m.other_cost
    return m


def main():
    g = load_gen_module()
    out, chk = [], {}
    for s in SEEDS:
        d = gen_ext(g, s)
        m = to_month(d); m.insert(0, "seed", s); out.append(m)
        if s in (0, 1):
            base = g.gen(s)[1]
            a = d[d.date <= "2026-03-31"].reset_index(drop=True)
            diff = max(float(np.abs(a[c].values - base[c].values).max()) for c in ["sales", "receipts", "gross_profit", "labor_cost"])
            chk[f"seed{s}_max_abs_diff_vs_gen"] = diff
    allm = pd.concat(out, ignore_index=True)
    allm.to_csv(ROOT / "data" / "store_month_seeds.csv.gz", index=False, float_format="%.1f")
    mart = pd.read_csv(MART / "store_month.csv", encoding="utf-8-sig")
    z = allm[allm.seed == 0].merge(mart, on=["ym", "store_id"], suffixes=("", "_mart"))
    chk["mart_rows_matched"] = int(len(z)); chk["mart_rows"] = int(len(mart))
    chk["mart_max_rel_diff_sales"] = float((z.sales / z.sales_mart - 1).abs().max())
    chk["mart_max_rel_diff_op"] = float(((z.operating_profit - z.operating_profit_mart).abs() / z.sales_mart).max())
    ext = allm[(allm.seed == 0) & (allm.ym >= "2026-04")]
    chk["ext_months"] = sorted(ext.ym.unique().tolist()); chk["ext_stores"] = int(ext.store_id.nunique())
    s = pd.read_csv(g.RAW / "sales_monthly_6types.csv")
    s = s[(s["業態"] == "スーパー") & (s["品目"] == "合計")][["ym", "販売額_百万円"]].rename(columns={"販売額_百万円": "sales_mil"})
    s.to_csv(ROOT / "data" / "industry_super_monthly.csv", index=False)
    chk["industry_range"] = [s.ym.min(), s.ym.max(), int(len(s))]
    (ROOT / "results").mkdir(exist_ok=True)
    json.dump(chk, open(ROOT / "results" / "02_check.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(chk, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
