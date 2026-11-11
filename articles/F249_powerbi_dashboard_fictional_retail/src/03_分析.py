"""03 分析：DAX の各メジャーの期待値（pandas と SQL の2通り）、偶然の幅で色をつける効果（乱数の種20通り）、速さ。

- 会社・数字は架空（サンプルマート（架空）、合成データ）。
- 期待値は powerbi/data/ のスタースキーマだけから計算する（Power BI に読ませるのと同じファイル）。
- DAX そのものは Power BI で動かしていない。Power BI で組み立てた人が、results/expected_values.csv と同じ値が出るかで確かめる。
"""
import json, pathlib, time, importlib.util, sys
import numpy as np
import pandas as pd
import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "powerbi" / "data"; RES = ROOT / "results"; RES.mkdir(exist_ok=True)
SUMS = ["sales", "receipts", "items", "gross_profit_before_waste", "waste", "gross_profit", "labor_hours", "labor_cost"]
SCOPES = ["全社", "都市", "郊外", "地方"]


def rd(n):
    return pd.read_csv(P / n, encoding="utf-8-sig")


def load():
    d = {k: rd(f"{k}.csv" if "fact_store_day" not in k else f"{k}.csv.gz") for k in
         ["dim_date", "dim_store", "dim_category", "fact_store_day", "fact_store_day_category", "fact_store_month", "fact_member_month", "ref_noise_band"]}
    return d


def ym_shift(ym, k):
    return (pd.Period(ym, "M") + k).strftime("%Y-%m")


class Engine:
    """店×月に集めてから、既存店の当月と前年同月（同じ店）を足し上げる。DAX の SUMX(VALUES(month_start)) と同じ順。"""

    def __init__(self, d):
        self.d = d
        f = d["fact_store_day"].copy(); f["ym"] = f.biz_date.str[:7]
        sm = f.groupby(["store_id", "ym"])[SUMS].sum()
        fm = d["fact_store_month"].assign(ym=lambda x: x.month_start.str[:7]).set_index(["store_id", "ym"])
        mm = d["fact_member_month"].assign(ym=lambda x: x.month_start.str[:7]).set_index(["store_id", "ym"])
        sm = sm.join(fm[["other_cost", "is_existing"]]).join(mm[["active_members", "member_receipts"]])
        self.sm = sm
        self.area = d["dim_store"].set_index("store_id").area
        dd = d["dim_date"]; self.w = dd.groupby("ym").day_weight.sum()
        self.months = sorted(set(sm.index.get_level_values(1)))
        c = d["fact_store_day_category"].copy(); c["ym"] = c.biz_date.str[:7]
        self.cm = c.groupby(["category_id", "store_id", "ym"])[["sales", "gross_profit_before_waste", "waste"]].sum()
        self.cat = d["dim_category"].set_index("category_id").category

    def cat_measures(self, months, cid, scope="全社"):
        """部門の既存店の当月と前年同月（同じ店）。"""
        sc = self.stores(scope); acc1 = np.zeros(3); acc0 = np.zeros(3)
        cm = self.cm.xs(cid, level=0)
        for m in months:
            cur = self.sm.xs(m, level=1); S = sorted(set(cur.index[cur.is_existing == 1]) & sc)
            a = cm.xs(m, level=1).reindex(S).fillna(0).sum().values; b = cm.xs(ym_shift(m, -12), level=1).reindex(S).fillna(0).sum().values
            acc1 += a; acc0 += b
        s1, b1, w1 = acc1; s0, b0, w0 = acc0
        return {"部門_既存店売上": s1, "部門_既存店売上_前年比": s1 / s0 - 1,
                "部門_既存店粗利率_廃棄後": (b1 - w1) / s1, "部門_既存店粗利率_廃棄後_前年差": (b1 - w1) / s1 - (b0 - w0) / s0,
                "部門_既存店廃棄率": w1 / s1, "部門_既存店廃棄率_前年差": w1 / s1 - w0 / s0}

    def stores(self, scope):
        return set(self.area.index) if scope == "全社" else set(self.area[self.area == scope].index)

    def tot(self, months, scope, existing, ly, store=None):
        acc = pd.Series(0.0, index=SUMS + ["other_cost", "active_members", "member_receipts"])
        sc = self.stores(scope) if store is None else {store}
        for m in months:
            cur = self.sm.xs(m, level=1)
            S = set(cur.index[cur.is_existing == 1]) if existing else set(cur.index)
            S &= sc
            mm = ym_shift(m, -12) if ly else m
            if ly and mm not in self.months:
                return None
            src = self.sm.xs(mm, level=1)
            acc += src.loc[sorted(S & set(src.index)), acc.index].sum()
        return acc

    def measures(self, months, scope="全社", store=None):
        a = self.tot(months, scope, False, False, store)
        r = {"売上": a.sales, "粗利_廃棄後": a.gross_profit, "営業利益": a.gross_profit - a.labor_cost - a.other_cost}
        c = self.tot(months, scope, True, False, store); l = self.tot(months, scope, True, True, store)
        if l is None or l.sales == 0:
            return r
        op = lambda x: x.gross_profit - x.labor_cost - x.other_cost
        cal = sum(self.w[m] for m in months) / sum(self.w[ym_shift(m, -12)] for m in months) - 1
        yoy = c.sales / l.sales - 1
        r.update({
            "既存店売上": c.sales, "既存店売上_前年": l.sales, "既存店売上_前年比": yoy,
            "曜日の並びの効果": cal, "既存店売上_前年比_曜日補正": (1 + yoy) / (1 + cal) - 1,
            "既存店客数_前年比": c.receipts / l.receipts - 1,
            "既存店買上点数": c["items"] / c.receipts, "既存店買上点数_前年比": (c["items"] / c.receipts) / (l["items"] / l.receipts) - 1,
            "既存店一品単価": c.sales / c["items"], "既存店一品単価_前年比": (c.sales / c["items"]) / (l.sales / l["items"]) - 1,
            "既存店粗利率_廃棄後": c.gross_profit / c.sales, "既存店粗利率_廃棄後_前年差": c.gross_profit / c.sales - l.gross_profit / l.sales,
            "既存店廃棄率": c.waste / c.sales, "既存店廃棄率_前年差": c.waste / c.sales - l.waste / l.sales,
            "既存店人時粗利": c.gross_profit / c.labor_hours, "既存店人時粗利_前年比": (c.gross_profit / c.labor_hours) / (l.gross_profit / l.labor_hours) - 1,
            "既存店人件費率": c.labor_cost / c.sales, "既存店人件費率_前年差": c.labor_cost / c.sales - l.labor_cost / l.sales,
            "既存店営業利益": op(c), "既存店営業利益_前年": op(l), "既存店営業利益_前年比": op(c) / op(l) - 1,
            "来店頻度_会員": c.member_receipts / c.active_members,
            "来店頻度_会員_前年比": (c.member_receipts / c.active_members) / (l.member_receipts / l.active_members) - 1,
            # 営業利益の前年差の分け方（既存店）
            "橋_売上の伸び": (c.sales - l.sales) * (l.gross_profit_before_waste / l.sales),
            "橋_廃棄前の粗利率": c.sales * (c.gross_profit_before_waste / c.sales - l.gross_profit_before_waste / l.sales),
            "橋_廃棄": -(c.waste - l.waste), "橋_人件費": -(c.labor_cost - l.labor_cost), "橋_その他経費": -(c.other_cost - l.other_cost),
        })
        return r


def periods(eng):
    ps = [(m, [m]) for m in eng.months if m >= "2023-04"]
    for fy in (2023, 2024, 2025):
        ps.append((f"FY{fy}", [m for m in eng.months if (m >= f"{fy}-04" and m <= f"{fy + 1}-03")]))
    return ps


def expected(eng):
    rows = []
    for sc in SCOPES:
        for lab, ms in periods(eng):
            for k, v in eng.measures(ms, sc).items():
                rows.append({"範囲": sc, "期間": lab, "メジャー": k, "期待値": float(v)})
    for cid in sorted(eng.cat.index):
        for lab, ms in [("2026-03", ["2026-03"]), ("FY2025", [m for m in eng.months if "2025-04" <= m <= "2026-03"]),
                        ("FY2024", [m for m in eng.months if "2024-04" <= m <= "2025-03"])]:
            for k, v in eng.cat_measures(ms, cid).items():
                rows.append({"範囲": f"部門{cid}", "期間": lab, "メジャー": k, "期待値": float(v)})
    # 店ごと（2026-03 と FY2025）
    for s in sorted(eng.area.index):
        for lab, ms in [(m, [m]) for m in eng.months if m >= "2024-04"] + [("FY2025", [m for m in eng.months if "2025-04" <= m <= "2026-03"])]:
            for k, v in eng.measures(ms, "全社", store=s).items():
                rows.append({"範囲": f"店{s:02d}", "期間": lab, "メジャー": k, "期待値": float(v)})
    return pd.DataFrame(rows)


def sql_expected():
    con = duckdb.connect()
    q = open(ROOT / "sql" / "expected_measures.sql", encoding="utf-8").read().replace("{P}", str(P))
    t0 = time.perf_counter(); df = con.execute(q).df(); t = time.perf_counter() - t0
    return df, t


def compare(exp, sq):
    m = sq.melt(id_vars=["範囲", "期間"], var_name="メジャー", value_name="SQL")
    j = exp.merge(m, on=["範囲", "期間", "メジャー"], how="inner")
    j["差"] = (j.期待値 - j.SQL).abs(); j["相対差"] = j.差 / j.期待値.abs().clip(lower=1e-12)
    return j


# ---------- 偶然の幅で色をつける効果（F246 の gen(seed) で20通り） ----------
def load_gen():
    p = ROOT / "data" / "in" / "f246" / "src" / "02_整形.py"
    spec = importlib.util.spec_from_file_location("f246gen", p); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def grain_devs(fsd, exist):
    """店の売上の前年比 − 全社（既存店）の前年比、と廃棄率の前年差（pt）。FY2025 の期間。粒度ごとに key→値。"""
    f = fsd[["date", "store_id", "sales", "waste"]].copy()
    f["ym"] = f.date.dt.strftime("%Y-%m")
    f = f.merge(exist, on=["store_id", "ym"], how="left").fillna({"is_existing": 0})
    out = {}
    # 日：364日前
    cur = f[(f.date >= "2025-04-01") & (f.is_existing == 1)]
    prev = f[["date", "store_id", "sales", "waste"]].copy(); prev["date"] = prev.date + pd.to_timedelta(364, unit="D")
    j = cur.merge(prev, on=["date", "store_id"], suffixes=("", "_ly"))
    co = j.groupby("date")[["sales", "sales_ly"]].sum(); co = co.sales / co.sales_ly - 1
    j["dev"] = j.sales / j.sales_ly - 1 - j.date.map(co)
    j["wr"] = (j.waste / j.sales - j.waste_ly / j.sales_ly)
    out["店×日"] = j.set_index(["store_id", "date"])[["dev", "wr"]]
    # 週：月曜はじまり、52週前
    j["wk"] = j.date - pd.to_timedelta(j.date.dt.dayofweek, unit="D")
    g = j.groupby(["store_id", "wk"])[["sales", "sales_ly", "waste", "waste_ly"]].sum()
    g = g[j.groupby(["store_id", "wk"]).size() == 7]
    cw = g.groupby(level=1)[["sales", "sales_ly"]].sum(); cw = cw.sales / cw.sales_ly - 1
    g["dev"] = g.sales / g.sales_ly - 1 - cw.reindex(g.index.get_level_values(1)).values
    g["wr"] = g.waste / g.sales - g.waste_ly / g.sales_ly
    out["店×週"] = g[["dev", "wr"]]
    # 月：前年同月（同じ店）
    mcur = f[(f.ym >= "2025-04") & (f.is_existing == 1)].groupby(["store_id", "ym"])[["sales", "waste"]].sum()
    f2 = f.copy(); f2["ym"] = (pd.PeriodIndex(f2.ym, freq="M") + 12).strftime("%Y-%m")
    mly = f2.groupby(["store_id", "ym"])[["sales", "waste"]].sum()
    mj = mcur.join(mly, rsuffix="_ly", how="inner")
    cm = mj.groupby(level=1)[["sales", "sales_ly"]].sum(); cm = cm.sales / cm.sales_ly - 1
    mj["dev"] = mj.sales / mj.sales_ly - 1 - cm.reindex(mj.index.get_level_values(1)).values
    mj["wr"] = mj.waste / mj.sales - mj.waste_ly / mj.sales_ly
    out["店×月"] = mj[["dev", "wr"]]
    # 地域×月
    ar = mj.reset_index(); ar["area"] = ar.store_id.map(AREA)
    am = ar.groupby(["area", "ym"])[["sales", "sales_ly", "waste", "waste_ly"]].sum()
    am["dev"] = am.sales / am.sales_ly - 1 - cm.reindex(am.index.get_level_values(1)).values
    am["wr"] = am.waste / am.sales - am.waste_ly / am.sales_ly
    out["地域×月"] = am[["dev", "wr"]]
    # 店×12か月（FY2025 合計）
    y = mj.groupby(level=0)[["sales", "sales_ly", "waste", "waste_ly"]].sum()
    cy = y.sales.sum() / y.sales_ly.sum() - 1
    y["dev"] = y.sales / y.sales_ly - 1 - cy; y["wr"] = y.waste / y.sales - y.waste_ly / y.sales_ly
    out["店×12か月"] = y[["dev", "wr"]]
    return out


AREA = None


def kpi_yoy_bands(fsd_list, exist):
    """全社・地域 × 月・12か月（FY2025）の前年比の偶然の幅（20通りの標準偏差 ×1.96）。"""
    ex = exist.set_index(["store_id", "ym"]).is_existing
    out = []
    for s, fsd in enumerate(fsd_list):
        f = fsd.copy(); f["ym"] = f.date.dt.strftime("%Y-%m")
        g = f.groupby(["store_id", "ym"])[["receipts", "items", "sales", "gross_profit", "waste", "labor_hours", "labor_cost", "other_cost"]].sum()
        g["ex"] = ex.reindex(g.index).fillna(0).values
        months = [m for m in sorted(set(g.index.get_level_values(1))) if "2025-04" <= m <= "2026-03"]
        for sc in SCOPES + [f"店{k:02d}" for k in sorted(AREA)]:
            ids = set(AREA) if sc == "全社" else ({int(sc[1:])} if sc.startswith("店") else {k for k, v in AREA.items() if v == sc})
            if sc.startswith("店") and not all(g.loc[(int(sc[1:]), m), "ex"] == 1 if (int(sc[1:]), m) in g.index else False for m in months):
                continue  # 店は FY2025 の12か月とも既存店の店だけ
            for lab, ms in [(m, [m]) for m in months] + [("12か月", months)]:
                c = 0; l = 0
                for m in ms:
                    cur = g.xs(m, level=1); S = sorted(set(cur.index[cur.ex == 1]) & ids)
                    c = c + cur.loc[S].sum(); l = l + g.xs(ym_shift(m, -12), level=1).reindex(S).sum()
                op1 = c.gross_profit - c.labor_cost - c.other_cost; op0 = l.gross_profit - l.labor_cost - l.other_cost
                out.append({"seed": s, "範囲": sc, "期間": lab, "売上": c.sales / l.sales - 1, "客数": c.receipts / l.receipts - 1,
                            "買上点数": (c["items"] / c.receipts) / (l["items"] / l.receipts) - 1, "一品単価": (c.sales / c["items"]) / (l.sales / l["items"]) - 1,
                            "粗利率（廃棄後）": c.gross_profit / c.sales - l.gross_profit / l.sales, "廃棄率": c.waste / c.sales - l.waste / l.sales,
                            "人時粗利": (c.gross_profit / c.labor_hours) / (l.gross_profit / l.labor_hours) - 1, "営業利益": op1 / op0 - 1})
    df = pd.DataFrame(out)
    K = ["売上", "客数", "買上点数", "一品単価", "粗利率（廃棄後）", "廃棄率", "人時粗利", "営業利益"]
    sd = df.groupby(["範囲", "期間"])[K].std()
    rows = []
    for sc in sorted(set(df.範囲)):
        lv = "全社" if sc == "全社" else ("1店" if sc.startswith("店") else "地域")
        for gr, sel in [("月", [p for p in sd.loc[sc].index if p != "12か月"]), ("12か月", ["12か月"])]:
            v = sd.loc[sc].loc[sel].median()
            for k in K:
                rows.append({"level": lv, "scope": sc, "grain": gr, "KPI": k, "band": 1.96 * v[k] * 100,
                             "unit": "pt" if k in ("粗利率（廃棄後）", "廃棄率") else "%"})
    b = pd.DataFrame(rows)
    # 地域は3つの中央値を「地域」の幅にする
    reg = b[b.level == "地域"].groupby(["grain", "KPI", "unit"], as_index=False).band.median().assign(level="地域")
    # 店は「12か月」だけ足す（店・月は F246 の値を使う）
    st12 = b[(b.level == "1店") & (b.grain == "12か月")].groupby(["grain", "KPI", "unit"], as_index=False).band.median().assign(level="1店")
    reg = pd.concat([reg, st12])
    return b, reg


def noise_study(d, n_seed=20):
    global AREA
    gm = load_gen()
    AREA = d["dim_store"].set_index("store_id").area.to_dict()
    exist = d["fact_store_month"].assign(ym=lambda x: x.month_start.str[:7])[["store_id", "ym", "is_existing"]]
    per = {}; fsds = []
    for s in range(n_seed):
        _, fsd, *_ = gm.gen(s); fsds.append(fsd)
        for gr, v in grain_devs(fsd, exist).items():
            per.setdefault(gr, []).append(v.assign(seed=s))
    rows = []
    # 設定（F246 の company_spec）で分かっている差：地方の店は客数が年 −2.5%（全社より下）、FY2025 に廃棄が1.25倍（上）。
    # 郊外の店は客数の流れ 0%（全社との差は小さい）、廃棄の設定は変わらない → 「差がない店」として誤報を数える。
    for gr, lst in per.items():
        for col, fixed, unit in [("dev", 0.03, "売上の前年比の全社との差"), ("wr", 0.001, "廃棄率の前年差")]:
            a = pd.concat(lst).reset_index()
            key0 = a.columns[0]
            a["area"] = a[key0].map(AREA) if gr != "地域×月" else a[key0]
            piv = a.pivot_table(index=a.columns[:2].tolist() if gr != "店×12か月" else [key0], columns="seed", values=col)
            band = 1.96 * piv.std(1).median()
            for name, thr in [("決めた線（売上3pt・廃棄率0.1pt）", fixed), ("偶然の幅（1.96σ）", band),
                              ("偶然の幅（1.64σ）", band / 1.96 * 1.64), ("偶然の幅（2.58σ）", band / 1.96 * 2.58)]:
                a["flag"] = np.sign(a[col]) * (a[col].abs() > thr)
                rural, sub = a[a.area == "地方"], a[a.area == "郊外"]
                hit = (rural.flag == (-1 if col == "dev" else 1)).mean()
                # 翌期も同じ向き：同じ店（地域）で時間順に並べ、色がついた期の次の期
                pers = np.nan
                if gr != "店×12か月":
                    t = a.sort_values([key0, "seed", a.columns[1]])
                    nxt = t.groupby([key0, "seed"]).flag.shift(-1)
                    m = (t.flag != 0) & nxt.notna()
                    pers = float((nxt[m] == t.flag[m]).mean()) if m.any() else np.nan
                rows.append({"KPI": unit, "粒度": gr, "線": name, "線の値": thr, "偶然の幅": band,
                             "色がつく割合": float((a.flag != 0).mean()),
                             "郊外（設定上の差なし）に色がつく割合": float((sub.flag != 0).mean()),
                             "地方（設定上の差あり）に正しい向きの色がつく割合": float(hit),
                             "翌期も同じ向きの色": pers, "組の数（1通りあたり）": int(len(a) / len(lst))})
    return pd.DataFrame(rows), kpi_yoy_bands(fsds, exist)


def perf(eng, d):
    t0 = time.perf_counter(); expected(eng); t_pd = time.perf_counter() - t0
    con = duckdb.connect()
    t0 = time.perf_counter()
    con.execute(f"CREATE TABLE f AS SELECT * FROM read_csv_auto('{P}/fact_store_day.csv.gz')")
    con.execute(f"CREATE TABLE fc AS SELECT * FROM read_csv_auto('{P}/fact_store_day_category.csv.gz')")
    t_load = time.perf_counter() - t0
    t0 = time.perf_counter()
    for _ in range(20):
        con.execute("SELECT strftime(biz_date,'%Y-%m') ym, store_id, sum(sales), sum(receipts), sum(gross_profit) FROM f GROUP BY 1,2").fetchall()
    t_q = (time.perf_counter() - t0) / 20
    t0 = time.perf_counter()
    for _ in range(5):
        con.execute("SELECT strftime(biz_date,'%Y-%m') ym, store_id, category_id, sum(sales), sum(waste) FROM fc GROUP BY 1,2,3").fetchall()
    t_qc = (time.perf_counter() - t0) / 5
    # 平らな表（次元を全部つないだ1枚）にした場合の大きさ
    flat = d["fact_store_day_category"].merge(d["dim_store"], on="store_id").merge(d["dim_category"], on="category_id") \
        .merge(d["dim_date"], left_on="biz_date", right_on="date")
    flat_bytes = len(flat.to_csv(index=False).encode("utf-8"))
    star_bytes = sum((P / f).stat().st_size for f in [x.name for x in P.iterdir()])
    return {"pandas_期待値の全計算_秒": t_pd, "DuckDB_読み込み_秒": t_load, "DuckDB_店×月の集計_ミリ秒": t_q * 1000,
            "DuckDB_店×月×部門の集計_ミリ秒": t_qc * 1000, "平らな表_CSV_MB（圧縮なし）": flat_bytes / 1e6,
            "平らな表_列": flat.shape[1], "スター_ファイル合計_MB（gz込み）": star_bytes / 1e6,
            "店×日×部門_行": int(len(d["fact_store_day_category"]))}


def band_flags(eng, d):
    """F247 の mart（seed 0）で、2026-03 と FY2025 の各月に、店の色が何店つくか（幅の倍率を変えて）。"""
    nz = d["ref_noise_band"]; b = float(nz[(nz.level == "1店") & (nz.grain == "月") & (nz.KPI == "売上")].band_ratio.iloc[0])
    out = []
    months = [m for m in eng.months if "2025-04" <= m <= "2026-03"]
    for m in months:
        co = eng.measures([m])["既存店売上_前年比_曜日補正"]
        devs = []
        for s in sorted(eng.area.index):
            r = eng.measures([m], store=s)
            if "既存店売上_前年比_曜日補正" in r and eng.sm.loc[(s, m), "is_existing"] == 1:
                devs.append((s, r["既存店売上_前年比_曜日補正"] - co))
        for k in (1.64, 1.96, 2.58):
            out.append({"月": m, "倍率": k, "幅": b / 1.96 * k, "既存店の数": len(devs),
                        "色がつく店": sum(abs(v) > b / 1.96 * k for _, v in devs),
                        "色がつく店（決めた線3pt）": sum(abs(v) > 0.03 for _, v in devs),
                        "店": ",".join(f"{s:02d}" for s, v in devs if abs(v) > b / 1.96 * k)})
    return pd.DataFrame(out)


def main():
    d = load(); eng = Engine(d)
    exp = expected(eng)
    exp.to_csv(RES / "expected_values.csv", index=False, encoding="utf-8-sig")
    sq, t_sql = sql_expected()
    sq.to_csv(RES / "B_sql_measures.csv", index=False, encoding="utf-8-sig")
    cmp_ = compare(exp, sq)
    cmp_.to_csv(RES / "B_check_sql_vs_pandas.csv", index=False, encoding="utf-8-sig")
    # RLS：3つの地域の足し算が全社に一致するか（足せるメジャー）
    add = ["売上", "粗利_廃棄後", "営業利益", "既存店売上", "既存店売上_前年", "既存店営業利益", "既存店営業利益_前年"]
    e2 = exp[exp.範囲.isin(SCOPES) & exp.メジャー.isin(add)].pivot_table(index=["期間", "メジャー"], columns="範囲", values="期待値")
    rls = (e2[["都市", "郊外", "地方"]].sum(1) - e2["全社"]).abs()
    bf = band_flags(eng, d); bf.to_csv(RES / "C_band_flags_fy2025.csv", index=False, encoding="utf-8-sig")
    pf = perf(eng, d); pf["DuckDB_期待値SQL_秒"] = t_sql
    ns, (bands, reg) = noise_study(d); ns.to_csv(RES / "D_noise_flags_20seeds.csv", index=False, encoding="utf-8-sig")
    bands.to_csv(RES / "E_bands_company_area.csv", index=False, encoding="utf-8-sig")
    # Power BI の ref_noise_band に「全社・12か月」「地域・月」「地域・12か月」を足す（F246 の行はそのまま）
    nz = pd.read_csv(P / "ref_noise_band.csv", encoding="utf-8-sig")
    nz = nz[~((nz.grain == "12か月") | (nz.level == "地域"))]
    add = pd.concat([bands[(bands.level == "全社") & (bands.grain == "12か月")][["level", "grain", "KPI", "band", "unit"]],
                     reg[["level", "grain", "KPI", "band", "unit"]]])
    add["band_ratio"] = add.band / 100
    pd.concat([nz, add]).to_csv(P / "ref_noise_band.csv", index=False, encoding="utf-8-sig")
    print(pd.concat([nz, add]).pivot_table(index="KPI", columns=["level", "grain"], values="band").round(2).to_string())
    E = exp.set_index(["範囲", "期間", "メジャー"]).期待値
    main = {"FY2025_全社": {k: float(E[("全社", "FY2025", k)]) for k in exp[(exp.範囲 == "全社") & (exp.期間 == "FY2025")].メジャー},
            "2026-03_全社": {k: float(E[("全社", "2026-03", k)]) for k in exp[(exp.範囲 == "全社") & (exp.期間 == "2026-03")].メジャー},
            "期待値の行数": int(len(exp)), "SQLと照合した値の数": int(len(cmp_)), "SQLとの相対差_最大": float(cmp_.相対差.max()),
            "SQLとの差_最大（円などの単位）": float(cmp_.差.max()),
            "RLS_3地域の和と全社の差_最大": float(rls.max()), "速さ": pf}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps({k: v for k, v in main.items() if k not in ("2026-03_全社",)}, ensure_ascii=False, indent=1, default=float)[:3500])
    print(bf.groupby("倍率")[["色がつく店", "色がつく店（決めた線3pt）", "既存店の数"]].sum())
    print(ns[ns.線.str.contains("決めた|1.96")].drop(columns=["KPI"]).round(3).to_string())


if __name__ == "__main__":
    main()
