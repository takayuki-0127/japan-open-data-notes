"""03 分析：サンプルマート（架空）の KPI を決めるための確かめ。
A KPI ツリーの値（FY2024→FY2025、全店と既存店）と、営業利益の変化の分け方
B 全店と既存店：月の前年比の向きが逆になる月（既存店の定義を12・13・24か月で比べる）
C 粒度とばらつき：同じ設定で乱数の種だけ20通り変え、日・週・月 × 店・全社でどれだけ揺れるか（見分けられる差）
D 定義の違い：客単価（合計の比か店の平均か）、客数（レシートか会員の人数か）、粗利率（廃棄の前か後か）、曜日の並び
E KPI 候補の点検表：ばらつき・営業利益との関係・先行するか
"""
import importlib.util, json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location("g", ROOT / "src" / "02_整形.py"); G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
STORES = G.STORES

cal, fsd, fsdc, fmm, ec = G.gen(0)
fsd["ym"] = fsd.date.dt.strftime("%Y-%m")
fsd["fy"] = np.where(fsd.date.dt.month >= 4, fsd.date.dt.year, fsd.date.dt.year - 1)
SUMS = ["sales", "receipts", "member_receipts", "items", "labor_hours", "labor_cost", "other_cost", "gross_profit_before_waste", "waste", "gross_profit"]


def kpis(g):
    """合計の行から KPI を計算する（比は合計どうしの比）"""
    o = pd.Series(dtype=float)
    o["営業利益"] = g.gross_profit - g.labor_cost - g.other_cost
    o["営業利益率"] = o["営業利益"] / g.sales
    o["売上"] = g.sales
    o["客数"] = g.receipts
    o["客単価"] = g.sales / g.receipts
    o["買上点数"] = g["items"] / g.receipts
    o["一品単価"] = g.sales / g["items"]
    o["粗利（廃棄後）"] = g.gross_profit
    o["粗利率（廃棄後）"] = g.gross_profit / g.sales
    o["粗利率（廃棄前）"] = g.gross_profit_before_waste / g.sales
    o["廃棄率"] = g.waste / g.sales
    o["人時"] = g.labor_hours
    o["人時売上"] = g.sales / g.labor_hours
    o["人時粗利"] = g.gross_profit / g.labor_hours
    o["人件費率"] = g.labor_cost / g.sales
    return o


# ---------- 既存店の判定 ----------
def existing_mask(df, months=13):
    """月 m の既存店：m の月初で開店から months か月以上たっている、かつ m と前年同月の両方でその月の全日営業"""
    st = STORES.set_index("store_id")
    ym = pd.PeriodIndex(df.ym, freq="M")
    od = pd.PeriodIndex(st.loc[df.store_id, "open_date"].dt.to_period("M"))
    cd = st.loc[df.store_id, "close_date"]
    age = (ym - od).map(lambda x: x.n).values
    ok_open = age >= months
    month_end = ym.to_timestamp(how="end").normalize()
    ok_close = (cd.isna().values | (cd.values >= month_end.values))  # その月の末日まで営業している店だけ
    return ok_open & ok_close


def store_month(fsd):
    sm = fsd.groupby(["store_id", "ym"], as_index=False)[SUMS].sum()
    sm["fy"] = [int(y) if int(m) >= 4 else int(y) - 1 for y, m in (s.split("-") for s in sm.ym)]
    return sm


sm = store_month(fsd)
sm = sm.merge(fmm[["store_id", "ym", "active_members"]], on=["store_id", "ym"], how="left")

# ---------- A：KPI ツリー（FY2024→FY2025） ----------
def fy_kpis(sm, mask=None):
    d = sm if mask is None else sm[mask]
    g = d.groupby("fy")[SUMS + ["active_members"]].sum()
    out = {fy: kpis(g.loc[fy]) for fy in g.index}
    t = pd.DataFrame(out).T
    am = d.groupby("fy").active_members.sum()
    t["会員の延べ人数"] = am
    t["来店頻度（会員）"] = d.groupby("fy").member_receipts.sum() / am
    t["会員比率"] = d.groupby("fy").member_receipts.sum() / d.groupby("fy").receipts.sum()
    return t


def comparable_fy(sm, months=13, fy0=2024, fy1=2025):
    """既存店の年度比較：FY1 の各月で既存店の条件を満たす店×月と、その前年同月だけを使う"""
    m = existing_mask(sm, months)
    cur = sm[m & (sm.fy == fy1)][["store_id", "ym"]].copy()
    cur["ym0"] = (pd.PeriodIndex(cur.ym, freq="M") - 12).strftime("%Y-%m")
    a = sm.merge(cur[["store_id", "ym"]], on=["store_id", "ym"])
    b = sm.merge(cur[["store_id", "ym0"]].rename(columns={"ym0": "ym"}), on=["store_id", "ym"])
    return a, b


all_t = fy_kpis(sm)
a, b = comparable_fy(sm, 13)
ka = kpis(a[SUMS].sum()); kb = kpis(b[SUMS].sum())
for t, d in ((ka, a), (kb, b)):
    t["会員の延べ人数"] = d.active_members.sum(); t["来店頻度（会員）"] = d.member_receipts.sum() / d.active_members.sum()
    t["会員比率"] = d.member_receipts.sum() / d.receipts.sum()
treeA = pd.DataFrame({
    "全店_FY2024": all_t.loc[2024], "全店_FY2025": all_t.loc[2025],
    "既存店_FY2024": kb, "既存店_FY2025": ka,
})
treeA["全店_変化率"] = treeA["全店_FY2025"] / treeA["全店_FY2024"] - 1
treeA["既存店_変化率"] = treeA["既存店_FY2025"] / treeA["既存店_FY2024"] - 1
treeA.to_csv(RES / "A_kpi_tree_fy2024_fy2025.csv", encoding="utf-8-sig")

# 営業利益の変化の分け方（既存店）：売上の分・粗利率の分・人件費・その他
S0, S1 = b.sales.sum(), a.sales.sum()
r0, r1 = b.gross_profit.sum() / S0, a.gross_profit.sum() / S1
opbridge = {
    "売上の増減の分": (S1 - S0) * r0,
    "粗利率（廃棄後）の分": S1 * (r1 - r0),
    "人件費の分": -(a.labor_cost.sum() - b.labor_cost.sum()),
    "その他の経費の分": -(a.other_cost.sum() - b.other_cost.sum()),
}
opbridge["営業利益の変化"] = sum(opbridge.values())
# 人件費をさらに：時給の分と人時の分
w0 = b.labor_cost.sum() / b.labor_hours.sum(); w1 = a.labor_cost.sum() / a.labor_hours.sum()
opbridge["うち人時の増減"] = -(a.labor_hours.sum() - b.labor_hours.sum()) * w0
opbridge["うち時給の上昇"] = -a.labor_hours.sum() * (w1 - w0)
pd.Series(opbridge).to_csv(RES / "A_op_bridge_existing.csv", header=["円"], encoding="utf-8-sig")

# ---------- B：全店と既存店の月の前年比 ----------
def yoy_monthly(sm, months):
    mon = sorted(sm.ym.unique())
    rows = []
    for ym in mon:
        y0 = (pd.Period(ym) - 12).strftime("%Y-%m")
        if y0 not in set(sm.ym):
            continue
        c = sm[sm.ym == ym]; p = sm[sm.ym == y0]
        m = existing_mask(c, months)
        ids = set(c[m].store_id)
        ce, pe = c[c.store_id.isin(ids)], p[p.store_id.isin(ids)]
        rows.append({"ym": ym,
                     "全店_売上": c.sales.sum() / p.sales.sum() - 1, "既存店_売上": ce.sales.sum() / pe.sales.sum() - 1,
                     "全店_客数": c.receipts.sum() / p.receipts.sum() - 1, "既存店_客数": ce.receipts.sum() / pe.receipts.sum() - 1,
                     "既存店の数": len(ids), "全店の数": c.store_id.nunique()})
    return pd.DataFrame(rows)


B = {}
for n in (12, 13, 24):
    y = yoy_monthly(sm, n)
    y.to_csv(RES / f"B_yoy_all_vs_existing_{n}m.csv", index=False, encoding="utf-8-sig")
    opp_s = int((np.sign(y["全店_売上"]) != np.sign(y["既存店_売上"])).sum())
    opp_c = int((np.sign(y["全店_客数"]) != np.sign(y["既存店_客数"])).sum())
    gap = (y["全店_客数"] - y["既存店_客数"]).abs()
    B[n] = {"months": len(y), "opp_sales": opp_s, "opp_receipts": opp_c, "max_gap_receipts_pt": float(gap.max() * 100), "mean_gap_receipts_pt": float(gap.mean() * 100), "mean_gap_sales_pt": float((y["全店_売上"] - y["既存店_売上"]).abs().mean() * 100),
            "n_existing_min": int(y["既存店の数"].min()), "n_existing_max": int(y["既存店の数"].max())}

# ---------- C：粒度とばらつき（乱数の種20通り） ----------
SEEDS = range(20)
KPI_C = ["売上", "客数", "客単価", "買上点数", "一品単価", "粗利率（廃棄後）", "廃棄率", "人時", "人時粗利", "人件費率", "営業利益"]
rec = []
tgt_store = 2  # 都市のM店
KEEP = set(STORES.store_id) - {8, 16, 21, 24}  # 2年とも通して営業している店だけ（開店・閉店の影響を外す）
RATE = ("粗利率（廃棄後）", "廃棄率", "人件費率")
for s in SEEDS:
    _, f, _, _, _ = G.gen(s)
    f = f[(f.date >= "2024-04-01") & f.store_id.isin(KEEP)].copy()
    f["dnum"] = (f.date - pd.Timestamp("2024-04-01")).dt.days
    f["day"] = f.dnum
    f["week"] = f.dnum // 7
    f["month"] = f.date.dt.strftime("%Y-%m")
    for lvl, d in (("1店", f[f.store_id == tgt_store]), ("全社", f)):
        for gr, key, lag in (("日", "day", 364), ("週", "week", 52), ("月", "month", None)):
            g = d.groupby(key)[SUMS].sum()
            if gr == "週":
                g = g[d.groupby(key).date.nunique() >= 7]
            k = pd.DataFrame({i: kpis(g.loc[i]) for i in g.index}).T[KPI_C]
            if lag is None:
                prev_idx = (pd.PeriodIndex(k.index, freq="M") - 12).strftime("%Y-%m")
            else:
                prev_idx = k.index - lag
            k0 = k.reindex(prev_idx); k0.index = k.index
            ch = pd.DataFrame(index=k.index)
            for c in KPI_C:
                ch[c] = (k[c] - k0[c]) * 100 if c in RATE else (k[c] / k0[c] - 1) * 100
            ch = ch.dropna()
            ch["seed"] = s; ch["level"] = lvl; ch["grain"] = gr; ch["key"] = ch.index.astype(str)
            rec.append(ch)
C = pd.concat(rec, ignore_index=True)
# 同じ日・週・月の前年比が、種によってどれだけ違うか ＝ 本当の変化がなくても出る「揺れ」
rows = []
for (lvl, gr), d in C.groupby(["level", "grain"]):
    for k in KPI_C:
        piv = d.pivot(index="key", columns="seed", values=k)
        sd = piv.std(1).median()
        rows.append({"level": lvl, "grain": gr, "KPI": k, "前年比の揺れ（標準偏差）": sd, "単位": "pt" if k in RATE else "%",
                     "偶然の幅（±1.96σ）": 1.96 * sd})
Cn = pd.DataFrame(rows)
Cn.to_csv(RES / "C_noise_by_grain.csv", index=False, encoding="utf-8-sig")

# ---------- D：定義の違い ----------
D = {}
# 客単価：合計の比 vs 店の平均（FY2025 の前年比、既存店）
pa = a.groupby("store_id")[SUMS].sum(); pb = b.groupby("store_id")[SUMS].sum()
D["客単価_合計の比"] = float((a.sales.sum() / a.receipts.sum()) / (b.sales.sum() / b.receipts.sum()) - 1)
D["客単価_店の単純平均"] = float((pa.sales / pa.receipts).mean() / (pb.sales / pb.receipts).mean() - 1)
D["客単価_店の前年比の平均"] = float(((pa.sales / pa.receipts) / (pb.sales / pb.receipts) - 1).mean())
# 全店では店の構成が変わる：全店の合計の比
D["客単価_全店_合計の比"] = float(treeA.loc["客単価", "全店_変化率"])
# 客数：レシート vs 会員の人数 vs 来店頻度（既存店）
D["客数_レシート"] = float(a.receipts.sum() / b.receipts.sum() - 1)
D["客数_会員レシート"] = float(a.member_receipts.sum() / b.member_receipts.sum() - 1)
D["客数_会員の延べ人数"] = float(a.active_members.sum() / b.active_members.sum() - 1)
D["来店頻度_会員"] = float((a.member_receipts.sum() / a.active_members.sum()) / (b.member_receipts.sum() / b.active_members.sum()) - 1)
# 地域別：会員の人数と来店頻度
reg = []
for ar in ("都市", "郊外", "地方"):
    ids = set(STORES[STORES.area == ar].store_id)
    aa, bb = a[a.store_id.isin(ids)], b[b.store_id.isin(ids)]
    reg.append({"地域": ar, "レシート": aa.receipts.sum() / bb.receipts.sum() - 1,
                "会員の人数": aa.active_members.sum() / bb.active_members.sum() - 1,
                "来店頻度": (aa.member_receipts.sum() / aa.active_members.sum()) / (bb.member_receipts.sum() / bb.active_members.sum()) - 1,
                "会員比率の変化pt": (aa.member_receipts.sum() / aa.receipts.sum() - bb.member_receipts.sum() / bb.receipts.sum()) * 100})
pd.DataFrame(reg).to_csv(RES / "D_receipts_vs_members_by_area.csv", index=False, encoding="utf-8-sig")
# 粗利率：廃棄の前と後
D["粗利率_廃棄前_FY24"] = float(kb["粗利率（廃棄前）"]); D["粗利率_廃棄前_FY25"] = float(ka["粗利率（廃棄前）"])
D["粗利率_廃棄後_FY24"] = float(kb["粗利率（廃棄後）"]); D["粗利率_廃棄後_FY25"] = float(ka["粗利率（廃棄後）"])
# 店ごとの廃棄率の差
st_w = (fsd[fsd.fy == 2025].groupby("store_id").waste.sum() / fsd[fsd.fy == 2025].groupby("store_id").sales.sum())
D["廃棄率_店の最小"] = float(st_w.min()); D["廃棄率_店の最大"] = float(st_w.max())
# 曜日の並び：月の客数の前年比を、曜日・祝日の並びで調整した値と比べる
daily = fsd.groupby("date")[["receipts"]].sum().join(cal.set_index("date")[["dow", "hol", "ym"]])
daily["n_store"] = fsd.groupby("date").store_id.nunique()
daily["rps"] = daily.receipts / daily.n_store
w_dow = daily.groupby("dow").rps.mean(); w_dow = w_dow / w_dow.mean()
w_hol = daily[daily.dow < 5].groupby("hol").rps.mean(); hol_mult = w_hol.loc[True] / w_hol.loc[False]
daily["w"] = w_dow.reindex(daily.dow).values * np.where(daily.hol & (daily.dow < 5), hol_mult, 1.0)
wm = daily.groupby("ym").w.sum()
y13 = yoy_monthly(sm, 13).set_index("ym")
adj = []
for ym, r in y13.iterrows():
    y0 = (pd.Period(ym) - 12).strftime("%Y-%m")
    cal_eff = wm[ym] / wm[y0] - 1
    adj.append({"ym": ym, "既存店_客数_そのまま": r["既存店_客数"], "曜日の並びの効果": cal_eff,
                "既存店_客数_曜日調整後": (1 + r["既存店_客数"]) / (1 + cal_eff) - 1})
adj = pd.DataFrame(adj)
adj.to_csv(RES / "D_calendar_adjust.csv", index=False, encoding="utf-8-sig")
D["曜日効果_1pt以上の月"] = int((adj["曜日の並びの効果"].abs() >= 0.01).sum())
D["曜日調整で符号が変わる月"] = int((np.sign(adj["既存店_客数_そのまま"]) != np.sign(adj["既存店_客数_曜日調整後"])).sum())
D["月の数"] = len(adj)
D["曜日効果_最大pt"] = float(adj["曜日の並びの効果"].abs().max() * 100)

# ---------- E：KPI 候補の点検表 ----------
# 店×月の前年同月差：KPI の前年比 と 営業利益の前年差（円）の順位相関、1〜3か月先との相関
sm2 = sm.copy()
km = pd.DataFrame([kpis(r) for _, r in sm2[SUMS].iterrows()])
km = pd.concat([sm2[["store_id", "ym"]].reset_index(drop=True), km.reset_index(drop=True)], axis=1)
km["来店頻度（会員）"] = (sm2.member_receipts / sm2.active_members).values
km["会員の人数"] = sm2.active_members.values
km["P"] = pd.PeriodIndex(km.ym, freq="M")
prev = km.copy(); prev["P"] = prev.P + 12
mm2 = km.merge(prev, on=["store_id", "P"], suffixes=("", "_0"))
mm2 = mm2[existing_mask(mm2.assign(ym=mm2.P.astype(str)), 13)]
cand = ["売上", "客数", "会員の人数", "来店頻度（会員）", "客単価", "買上点数", "一品単価", "粗利率（廃棄後）", "廃棄率", "人時", "人時粗利", "人件費率"]
E = []
mm2 = mm2.sort_values(["store_id", "P"])
mm2["dOP"] = mm2["営業利益"] - mm2["営業利益_0"]
for k in cand:
    if k in ("粗利率（廃棄後）", "廃棄率", "人件費率"):
        x = (mm2[k] - mm2[k + "_0"]) * 100
    else:
        x = mm2[k] / mm2[k + "_0"] - 1
    mm2["x"] = x.values
    same = mm2[["x", "dOP"]].corr("spearman").iloc[0, 1]
    leads = []
    for h in (1, 2, 3):
        fut = mm2.groupby("store_id").dOP.shift(-h)
        leads.append(pd.concat([mm2.x, fut], axis=1).dropna().corr("spearman").iloc[0, 1])
    E.append({"KPI": k, "営業利益の前年差との順位相関（同じ月）": same, "1〜3か月先との順位相関（平均）": float(np.mean(leads))})
E = pd.DataFrame(E)
noise = Cn[(Cn.level == "1店") & (Cn.grain == "月")].set_index("KPI")["偶然の幅（±1.96σ）"]
E["1店・月の前年比の偶然の幅"] = E.KPI.map(noise)
judge = {  # 判断（作成者がつけた。データからは出ない）
    "売上": ("○", "結果の数字。店だけでは動かせない"), "客数": ("○", "チラシ・品ぞろえで動く"), "会員の人数": ("○", "会員の勧誘で動く"),
    "来店頻度（会員）": ("◎", "アプリのクーポン・品ぞろえで動く"), "客単価": ("○", "点数と単価の掛け算で、理由が見えにくい"),
    "買上点数": ("◎", "売場・関連陳列で動く"), "一品単価": ("△", "物価の影響が大きい"), "粗利率（廃棄後）": ("◎", "値入れ・発注・値引きで動く"),
    "廃棄率": ("◎", "発注と値引きのタイミングで動く"), "人時": ("◎", "シフトで動く"), "人時粗利": ("◎", "シフトと売上の両方"), "人件費率": ("△", "時給の改定は店では動かせない"),
}
E["店で動かせるか（判断）"] = E.KPI.map(lambda k: judge[k][0]); E["メモ（判断）"] = E.KPI.map(lambda k: judge[k][1])
E.to_csv(RES / "E_kpi_scorecard.csv", index=False, encoding="utf-8-sig")

main = {
    "期間": "2022-04〜2026-03（FY2022〜FY2025、4月始まり）。会社と数字は架空（合成）",
    "店の数": {"FY2025の営業店": int(sm[sm.fy == 2025].store_id.nunique()), "全期間": int(sm.store_id.nunique())},
    "A_tree": {k: {c: float(v) for c, v in r.items()} for k, r in treeA.iterrows()},
    "A_op_bridge_existing": {k: float(v) for k, v in opbridge.items()},
    "B_all_vs_existing": B,
    "C_noise": Cn.to_dict(orient="records"),
    "D_definitions": D,
    "E_scorecard": E.to_dict(orient="records"),
}
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(treeA[["全店_変化率", "既存店_変化率"]].round(4))
print(pd.Series(opbridge).round(-6) / 1e6)
print(B)
print(Cn.pivot_table(index="KPI", columns=["level", "grain"], values="偶然の幅（±1.96σ）").round(2))
print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in D.items()})
print(pd.read_csv(RES / "D_receipts_vs_members_by_area.csv").round(4))
print(E.round(3).to_string())
