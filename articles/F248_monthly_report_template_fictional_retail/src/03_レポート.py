"""03 レポート：月次レポートの「型」を、Python で毎月同じ形に組み立てる。

型（上から順に）
  1. 今月のまとめ（3行まで）
  2. KPI 表（行は毎月同じ10行。前年比・計画比・先月までの流れ・偶然の幅・判定）
  3. 要因（既存店売上の分解、営業利益の計画との差の分解）
  4. 例外（店）（決まりを満たした店だけ、5行まで）
  5. 次のアクション（担当は役割の名前、期限つき。前月のアクションの状況も）
  6. 載せなかったもの・注記・改訂履歴

載せる／載せないの決まり（RULE）
  - KPI：前年比は毎月出すが、文章で説明するのは「先月までの3か月の平均から、偶然の幅を超えて動いた」ものだけ。
        既存店売上・客数は市場（商業動態統計・スーパー販売額）の前年比との差で判定する。
        上の KPI の動きが KPI ツリーの下の KPI（または市場と同じ売上の動き）で説明できるときは、説明は下で1回だけ。
  - 計画との差：偶然の幅を超えて下回った／上回ったときだけ、まとめに書く。
  - 店：既存店の真ん中の店（中央値）との差が、今月 3σ を超えたか、3か月続けて同じ向きに 1σ を超えた店だけ。
        同じ店で下の KPI（客数・廃棄率など）も例外なら、上の KPI（売上・人時粗利）は「も」として添える。
        同じ地域で同じ向きの店が3店以上なら1行にまとめる。店の営業利益は載せない（1店・月の偶然の幅が ±205%）。
  - 偶然の幅（σ）は、F246 の作り方（乱数の種だけ変えて20回作り直す）で、この表の KPI ごとに測り直した（noise_widths）。

版（VERSION）
  - v1 速報：翌月5日までに届いた POS で作り、6日に出す。「届いた割合」と「あとで動く幅」を書く。
  - v1 では、売上の届いた割合が 99.5% 未満の店は例外の判定を保留し、届いていない分を会計の売上高で補うと判定が変わるものを「境目」と書く。
  - v2 確定：20日（すべて届いたあと）に作り直し、同じ場所で v1 と置き換える。予告（保留・境目）していない判定が変わったときだけ
    全員に知らせ直し、そうでなければ改訂履歴に1行足すだけにする。
会社・数字はすべて架空（合成データ）。
"""
import base64, io, json, pathlib, importlib.util
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"; RES = ROOT / "results"; REP = ROOT / "reports"
F246 = ROOT.parent / "F246_kpi_definitions_fictional_retail"
MONTHS = list(pd.period_range("2025-04", "2026-03", freq="M").strftime("%Y-%m"))
RULE = dict(store_now=3.0, store_run=1.0, run_len=3, kpi_z=1.96, trail=3, max_store_lines=5, group_min=3, hold=0.995)

# KPI 表の行（毎月同じ）。kind：pct＝前年比（%）、pt＝前年差（pt）
KPIS = [
    ("K00", "営業利益（全店）", "pct"),
    ("K10", "売上（全店）", "pct"),
    ("K01", "既存店売上", "pct"),
    ("K02", "客数（レシート）", "pct"),
    ("K03", "買上点数（1回）", "pct"),
    ("K04", "一品単価", "pct"),
    ("K05", "来店頻度（会員）", "pct"),
    ("K06", "粗利率（廃棄後）", "pt"),
    ("K07", "廃棄率", "pt"),
    ("K08", "人時粗利", "pct"),
    ("K09", "人件費率", "pt"),
]
KNAME = {k: n for k, n, _ in KPIS}; KKIND = {k: t for k, _, t in KPIS}
CAL_ADJ = ("K02",)   # 曜日・祝日の並びを補正した値を参考に並べる行（F246 の決めごと）
MKT_ADJ = ("K01", "K02")   # 市場（商業動態統計・スーパー）の前年比との差で判定する行。市場の数字に曜日の並び・天気も入っている
NO_TREND = ("K10",)  # 全店売上は店の出入りで動くので、流れの判定はせず計画比だけで判定する
# KPI ツリー（F246）：上の KPI が動いたとき、下の KPI も動いていれば説明は下で1回だけ
TREE = {"K00": ["K01", "K06", "K09", "K08"], "K01": ["K02", "K03", "K04"], "K08": ["K01", "K06"], "K09": ["K01"], "K06": ["K07"], "K02": ["K05"]}
# 店の例外で見る KPI（店で動かせるもの。F246 の採点）
SKPIS = [("S_sales", "売上", "pct"), ("S_rcpt", "客数", "pct"), ("S_gpr0", "粗利率（廃棄前）", "pt"),
         ("S_waste", "廃棄率", "pt"), ("S_lp", "人時粗利", "pct")]
# 店の KPI ツリー：同じ店で下の KPI も例外なら、上の KPI は見出しにせず「も」として添える
STREE = {"S_lp": ["S_sales", "S_rcpt", "S_waste", "S_gpr0"], "S_sales": ["S_rcpt"]}
SNAME = {k: n for k, n, _ in SKPIS}; SKIND = {k: t for k, _, t in SKPIS}
ACTIONS = {  # 例外の種類 → 次のアクションの型（担当は役割）
    ("S_waste", 1): ("店舗運営部", "発注量と値引きの時間を、該当店と見直す。次の月次で廃棄率を確認"),
    ("S_waste", -1): ("店舗運営部", "廃棄が減った理由（発注の工夫か、欠品か）を店に確認"),
    ("S_sales", -1): ("営業企画", "店の事情（競合の出店・工事・改装など）を店長に確認"),
    ("S_sales", 1): ("営業企画", "伸びた理由を店に確認し、他店に使えるか判断"),
    ("S_rcpt", -1): ("営業企画", "客数が減った時間帯・曜日を分析担当と確認"),
    ("S_rcpt", 1): ("営業企画", "客数が増えた理由を店に確認"),
    ("S_gpr0", -1): ("商品部", "値下げ・売価変更の記録と突き合わせる"),
    ("S_gpr0", 1): ("商品部", "粗利率が上がった部門を確認"),
    ("S_lp", -1): ("店舗運営部", "シフトと客数の時間帯のずれを確認"),
    ("S_lp", 1): ("店舗運営部", "人時の使い方を他店と比べる"),
}


# ---------------------------------------------------------------- 読み込み
def load_inputs():
    st = pd.read_csv(DATA / "in" / "dim_store.csv", parse_dates=["open_date", "close_date"])
    fm = pd.read_csv(DATA / "in" / "fact_member_month.csv")
    cal = pd.read_csv(DATA / "in" / "D_calendar_adjust.csv").set_index("ym")["曜日の並びの効果"]
    acct = pd.read_csv(DATA / "in" / "acct_store_month.csv").groupby("年月")["売上高"].sum()
    mkt = pd.read_csv(DATA / "in" / "market_super_monthly.csv").set_index("ym")["前年比_%"]
    plan = pd.read_csv(DATA / "plan_fy2025.csv")
    final = pd.read_csv(DATA / "in" / "store_month.csv")
    vers = {cd: pd.read_csv(DATA / "versions" / f"store_month_d{cd}.csv") for cd in (1, 3, 5, 10)}
    acct_store = pd.read_csv(DATA / "in" / "acct_store_month.csv").rename(columns={"店番": "store_id", "年月": "ym"})
    return dict(st=st, fm=fm, cal=cal, acct=acct, acct_store=acct_store, plan=plan, final=final, vers=vers, mkt=mkt)


def store_month_from_gen(fsd, st):
    """F246 の gen(seed) の店×日から、mart と同じ形の店×月を作る（偶然の幅を測るため）"""
    d = fsd.copy(); d["ym"] = d.date.dt.strftime("%Y-%m")
    S = ["sales", "receipts", "member_receipts", "items", "gross_profit_before_waste", "waste", "gross_profit",
         "labor_hours", "labor_cost", "other_cost"]
    sm = d.groupby(["ym", "store_id"], as_index=False).agg(days_with_sales=("sales", "size"), **{c: (c, "sum") for c in S})
    sm["fy"] = pd.PeriodIndex(sm.ym, freq="M").qyear - 1 + (pd.PeriodIndex(sm.ym, freq="M").month >= 4)
    sm["fy"] = [int(y[:4]) if int(y[5:]) >= 4 else int(y[:4]) - 1 for y in sm.ym]
    sm["operating_profit"] = sm.gross_profit - sm.labor_cost - sm.other_cost
    s = st.set_index("store_id"); ym = pd.PeriodIndex(sm.ym, freq="M")
    age = np.array([(y - pd.Period(o, "M")).n for y, o in zip(ym, s.reindex(sm.store_id).open_date)])
    cd = s.reindex(sm.store_id).close_date.values
    mend = ym.to_timestamp(how="end").normalize().values
    sm["is_existing"] = ((age >= 13) & (pd.isna(cd) | (cd >= mend))).astype(int)
    return sm


# ---------------------------------------------------------------- 計算
def _ym(ym, k):
    return (pd.Period(ym, "M") + k).strftime("%Y-%m")


def _ratios(g):
    return dict(sales=g.sales, rcpt=g.receipts, ipr=g["items"] / g.receipts, upi=g.sales / g["items"],
                gpr=g.gross_profit / g.sales, gpr0=g.gross_profit_before_waste / g.sales, waste=g.waste / g.sales, lp=g.gross_profit / g.labor_hours,
                lcr=g.labor_cost / g.sales)


def company_kpi(sm, final, fm, ym, plan=None, cal=None, mkt=None):
    """既存店（当月の is_existing）と、前年同月の同じ店（確定版）。全店の売上・営業利益は全店どうし。"""
    cur = sm[(sm.ym == ym) & (sm.is_existing == 1)]
    prv = final[(final.ym == _ym(ym, -12)) & final.store_id.isin(cur.store_id)]
    a, b = _ratios(cur.sum(numeric_only=True)), _ratios(prv.sum(numeric_only=True))
    fa = fm[(fm.ym == ym) & fm.store_id.isin(cur.store_id)].sum(numeric_only=True)
    fb = fm[(fm.ym == _ym(ym, -12)) & fm.store_id.isin(cur.store_id)].sum(numeric_only=True)
    allc, allp = sm[sm.ym == ym].sum(numeric_only=True), final[final.ym == _ym(ym, -12)].sum(numeric_only=True)
    y = {"K00": allc.operating_profit / allp.operating_profit - 1, "K10": allc.sales / allp.sales - 1,
         "K01": a["sales"] / b["sales"] - 1, "K02": a["rcpt"] / b["rcpt"] - 1, "K03": a["ipr"] / b["ipr"] - 1,
         "K04": a["upi"] / b["upi"] - 1,
         "K05": (fa.member_receipts / fa.active_members) / (fb.member_receipts / fb.active_members) - 1 if fb.active_members > 0 else np.nan,
         "K06": (a["gpr"] - b["gpr"]) * 100, "K07": (a["waste"] - b["waste"]) * 100, "K08": a["lp"] / b["lp"] - 1,
         "K09": (a["lcr"] - b["lcr"]) * 100}
    for k in y:
        if KKIND[k] == "pct":
            y[k] *= 100
    lvl = {"K00": allc.operating_profit, "K10": allc.sales, "K01": a["sales"], "K02": a["rcpt"], "K03": a["ipr"],
           "K04": a["upi"], "K05": fa.member_receipts / fa.active_members, "K06": a["gpr"] * 100,
           "K07": a["waste"] * 100, "K08": a["lp"], "K09": a["lcr"] * 100}
    out = {"yoy": y, "level": lvl, "n_existing": int(len(cur)),
           "all": allc[["sales", "gross_profit", "labor_cost", "other_cost", "operating_profit"]].to_dict(),
           "existing_cur": cur.sum(numeric_only=True)[["sales", "receipts", "items"]].to_dict(),
           "existing_prv": prv.sum(numeric_only=True)[["sales", "receipts", "items"]].to_dict()}
    if cal is not None and ym in cal.index:
        out["cal"] = float(cal[ym]) * 100
        out["yoy_adj"] = {k: ((1 + y[k] / 100) / (1 + cal[ym]) - 1) * 100 for k in CAL_ADJ}
    if mkt is not None and ym in mkt.index:
        out["market"] = float(mkt[ym])
        out["yoy_mkt"] = {k: y[k] - float(mkt[ym]) for k in MKT_ADJ}
    if plan is not None:
        p = plan[plan.ym == ym].sum(numeric_only=True)
        out["plan"] = {"K10": (allc.sales / p.plan_sales - 1) * 100, "K00": (allc.operating_profit / p.plan_operating_profit - 1) * 100,
                       "plan_sales": p.plan_sales, "plan_op": p.plan_operating_profit,
                       "bridge": {"売上の差": (allc.sales - p.plan_sales) * (p.plan_gross_profit / p.plan_sales),
                                  "粗利率の差": (allc.gross_profit / allc.sales - p.plan_gross_profit / p.plan_sales) * allc.sales,
                                  "人件費の差": -(allc.labor_cost - p.plan_labor_cost),
                                  "その他の経費の差": -(allc.other_cost - p.plan_other_cost)}}
    return out


def store_dev(sm, final, ym):
    """既存店ごとの KPI と、全社（既存店）との差。営業利益は見ない"""
    cur = sm[(sm.ym == ym) & (sm.is_existing == 1)].set_index("store_id")
    prv = final[(final.ym == _ym(ym, -12))].set_index("store_id").reindex(cur.index)
    a, b = _ratios(cur), _ratios(prv)
    v = pd.DataFrame({"S_sales": (a["sales"] / b["sales"] - 1) * 100, "S_rcpt": (a["rcpt"] / b["rcpt"] - 1) * 100,
                      "S_gpr0": (a["gpr0"] - b["gpr0"]) * 100, "S_waste": (a["waste"] - b["waste"]) * 100,
                      "S_lp": (a["lp"] / b["lp"] - 1) * 100})
    # 比べる相手は既存店の「真ん中の店」（中央値）。全社の合計と比べると、ある地域がまとめて動いたとき、ほかの地域の店が逆向きに見える
    dev = v - v.median()
    w = pd.DataFrame({"sales": cur.sales, "gp": cur.gross_profit, "prv_sales": prv.sales, "gpr": cur.gross_profit / cur.sales})
    return dev, v, w


# ---------------------------------------------------------------- 偶然の幅（20回の作り直し）
def load_gen():
    s = importlib.util.spec_from_file_location("g246", F246 / "src" / "02_整形.py")
    g = importlib.util.module_from_spec(s); s.loader.exec_module(g)
    return g


def noise_widths(n_seed=20, months=None):
    """乱数の種だけ変えて作り直し、同じ月・同じ店の値の種の間の標準偏差（σ）を KPI ごとに RMS で平均する"""
    g = load_gen(); st = pd.read_csv(DATA / "in" / "dim_store.csv", parse_dates=["open_date", "close_date"])
    months = months or list(pd.period_range("2023-04", "2026-03", freq="M").strftime("%Y-%m"))
    comp, stor, sms = [], [], {}
    for seed in range(n_seed):
        cal, fsd, fsdc, fmm, ec = g.gen(seed)
        sm = store_month_from_gen(fsd, st); sms[seed] = (sm, fmm)
        for ym in months:
            k = company_kpi(sm, sm, fmm, ym)
            comp.append({"seed": seed, "ym": ym, **k["yoy"]})
            dev, _, _ = store_dev(sm, sm, ym)
            d = dev.reset_index().assign(seed=seed, ym=ym); stor.append(d)
    comp, stor = pd.DataFrame(comp), pd.concat(stor)
    rows = []
    for k, n, t in KPIS:
        sd = comp.groupby("ym")[k].std(ddof=1)
        rows.append({"level": "全社（既存店）", "id": k, "KPI": n, "unit": "%" if t == "pct" else "pt", "sigma": float(np.sqrt((sd ** 2).mean()))})
    for k, n, t in SKPIS:
        sd = stor.groupby(["ym", "store_id"])[k].std(ddof=1)
        rows.append({"level": "店と真ん中の店の差", "id": k, "KPI": n, "unit": "%" if t == "pct" else "pt", "sigma": float(np.sqrt((sd ** 2).mean()))})
    W = pd.DataFrame(rows); W["width_1.96"] = W.sigma * 1.96
    return W, comp, stor, sms


# ---------------------------------------------------------------- 決まり（載せる／載せない）
def _jv(K, k, raw=False):
    if k in MKT_ADJ and "yoy_mkt" in K and not raw:
        return K["yoy_mkt"][k]
    return K["yoy"][k]


def judge_company(K, hist, sig):
    """hist：直前の月（確定版）の KPI。先月までの3か月の平均から、偶然の幅を超えて動いたか"""
    out = {}
    for k, n, t in KPIS:
        v = _jv(K, k)
        h = [_jv(hh, k) for hh in hist[-RULE["trail"]:]]
        h = [x for x in h if pd.notna(x)]
        trail = float(np.mean(h)) if h else np.nan
        w = RULE["kpi_z"] * sig[k] * np.sqrt(1 + 1 / max(len(h), 1))
        diff = v - trail if pd.notna(trail) else np.nan
        flag = int(np.sign(diff)) if pd.notna(diff) and abs(diff) > w and k not in NO_TREND else 0
        out[k] = {"value": v, "trail": trail, "diff": diff, "width": w, "flag": flag, "judged": k not in NO_TREND,
                  "basis": "市場との差" if k in MKT_ADJ else "前年比", "flag_raw": flag}
        if k in MKT_ADJ:   # 市場と同じ動き（市場との差では幅の中、前年比そのままでは幅の外）
            hr = [_jv(hh, k, True) for hh in hist[-RULE["trail"]:]]
            dr = K["yoy"][k] - float(np.mean(hr))
            out[k]["flag_raw"] = int(np.sign(dr)) if abs(dr) > w else 0
    # 木の下で説明できるもの（下の KPI も流れが変わった）は「従属」にして、説明は下で1回だけ
    def desc(k, seen=()):
        r = []
        for c in TREE.get(k, []):
            if c not in seen:
                r += [c] + desc(c, seen + (k,))
        return r
    for k in out:
        d = [c for c in desc(k) if out[c]["flag"] != 0]
        if not d and any(out[c]["flag_raw"] != 0 for c in desc(k)):
            d = ["MKT"]   # 市場と同じ売上・客数の動きで説明できる
        out[k]["explained_by"] = list(dict.fromkeys(d)) if out[k]["flag"] != 0 else []
    pj = {}
    if "plan" in K:
        for k in ("K10", "K00"):
            g = K["plan"][k]; w = RULE["kpi_z"] * sig[k]
            pj[k] = {"gap": g, "width": w, "flag": int(np.sign(g)) if abs(g) > w else 0}
    return out, pj


def store_exceptions(devs, ym, ssig, st, rule=None):
    """devs：{ym: dev}（当月と前の月々）。今月 store_now σ 超え、または run_len か月続けて store_run σ 超え（同じ向き）"""
    r = dict(RULE); r.update(rule or {})
    cur = devs[ym]
    prev = [devs.get(_ym(ym, -i)) for i in range(1, r["run_len"])]
    items = []
    for sid in cur.index:
        for k, n, t in SKPIS:
            d = cur.loc[sid, k]; s = ssig[k]
            if pd.isna(d):
                continue
            z = d / s
            run = 1
            for p in prev:
                if p is None or sid not in p.index or pd.isna(p.loc[sid, k]) or np.sign(p.loc[sid, k]) != np.sign(d) or abs(p.loc[sid, k]) / s <= r["store_run"]:
                    break
                run += 1
            # 何か月続いているか（1σ 超え・同じ向き）を、さかのぼれるだけ数える
            months_run = 0
            for i in range(0, 13):
                p = devs.get(_ym(ym, -i))
                if p is None or sid not in p.index or pd.isna(p.loc[sid, k]) or np.sign(p.loc[sid, k]) != np.sign(d) or abs(p.loc[sid, k]) / s <= r["store_run"]:
                    break
                months_run += 1
            hit_now = abs(z) > r["store_now"]
            hit_run = abs(z) > r["store_run"] and run >= r["run_len"]
            if hit_now or hit_run:
                items.append({"store_id": int(sid), "kpi": k, "dev": float(d), "z": float(z), "sign": int(np.sign(d)),
                              "why": "今月 %.0fσ 超え" % r["store_now"] if hit_now else "%dか月続けて %.0fσ 超え" % (r["run_len"], r["store_run"]),
                              "months_run": months_run})
    return items


def group_and_rank(items, w, st, ssig):
    """同じ地域・同じ KPI・同じ向きが group_min 店以上なら1行に。残りは店ごとに1行（いちばん大きく動いた KPI を見出しに）。
    影響（営業利益への概算、百万円）の大きい順に max_store_lines 行"""
    if not items:
        return [], []
    df = pd.DataFrame(items)
    df["area"] = df.store_id.map(st.set_index("store_id").area)
    flagged = set(zip(df.store_id, df.kpi))
    df["dep"] = [any((sid, c) in flagged for c in STREE.get(k, [])) for sid, k in zip(df.store_id, df.kpi)]
    deps = df[df.dep]; df = df[~df.dep]

    def impact(r):
        x = w.loc[r.store_id]
        if r.kpi in ("S_sales", "S_rcpt"):
            return r.dev / 100 * x.prv_sales * x.gpr
        if r.kpi == "S_gpr0":
            return r.dev / 100 * x.sales
        if r.kpi == "S_waste":
            return -r.dev / 100 * x.sales
        return r.dev / 100 * x.gp * 0.3   # 人時粗利：ごく粗い目安
    df["impact"] = df.apply(impact, axis=1) / 1e6
    lines, used = [], set()
    for (a, k, sg), g in df.groupby(["area", "kpi", "sign"]):
        if len(g) >= RULE["group_min"]:
            lines.append({"who": f"{a}の{len(g)}店", "stores": sorted(int(x) for x in g.store_id), "kpi": k, "sign": int(sg), "also": [],
                          "dev": float(g.dev.mean()), "z": float(g.z.mean()), "months_run": int(g.months_run.median()),
                          "why": "、".join(sorted(set(g.why))), "impact": float(g.impact.sum())})
            used |= set(g.index)
    rest = df.drop(index=list(used))
    for sid, g in rest.groupby("store_id"):
        g = g.reindex(g.z.abs().sort_values(ascending=False).index); r = g.iloc[0]
        lines.append({"who": "%02d店（%s）" % (sid, r.area), "stores": [int(sid)], "kpi": r.kpi, "sign": int(r.sign),
                      "also": [f"{SNAME[x.kpi]}{'+' if x.sign > 0 else '−'}" for _, x in g.iloc[1:].iterrows()],
                      "dev": float(r.dev), "z": float(r.z), "months_run": int(r.months_run), "why": r.why,
                      "impact": float(g.impact.abs().max() * np.sign(r.impact))})
    for _, d in deps.iterrows():   # 上の KPI は、その店の行に「も」で添える
        for L in lines:
            if d.store_id in L["stores"] and L["kpi"] in STREE.get(d.kpi, []):
                tag = f"{SNAME[d.kpi]}{'+' if d.sign > 0 else '−'}"
                if tag not in L["also"]:
                    L["also"].append(tag)
                break
    lines.sort(key=lambda x: -abs(x["impact"]))
    return lines[:RULE["max_store_lines"]], lines[RULE["max_store_lines"]:]


# ---------------------------------------------------------------- 1か月分のレポートの中身
def build_report(I, ym, version="v2", close_day=None, sig=None, ssig=None, prev_actions=None):
    sm = I["final"] if close_day is None else I["vers"][close_day]
    K = company_kpi(sm, I["final"], I["fm"], ym, I["plan"], I["cal"], I["mkt"])
    hist = [company_kpi(I["final"], I["final"], I["fm"], _ym(ym, -i), None, I["cal"], I["mkt"]) for i in range(RULE["trail"], 0, -1)]
    J, PJ = judge_company(K, hist, sig)
    devs = {}
    for i in range(0, 13):
        y = _ym(ym, -i)
        if y < "2023-04":
            break
        devs[y] = store_dev(sm if i == 0 else I["final"], I["final"], y)[0]
    _, _, w = store_dev(sm, I["final"], ym)
    # v1（速報）では、売上の届いた割合が hold 未満の店は例外の判定をしない（届いていない日の分だけ売上が低く見えるため）
    acs = I["acct_store"]; cur = sm[sm.ym == ym].set_index("store_id").sales
    arr_s = (cur / acs[acs.ym == ym].set_index("store_id")["売上高"].reindex(cur.index))
    held = sorted(arr_s[arr_s < RULE["hold"]].index.tolist()) if close_day is not None else []
    if held:
        devs[ym] = devs[ym].drop(index=[h for h in held if h in devs[ym].index])
    items = store_exceptions(devs, ym, ssig, I["st"])
    shown, hidden = group_and_rank(items, w, I["st"], ssig)
    arrived = float(sm[sm.ym == ym].sales.sum() / I["acct"][ym])
    # v1：届いていない分を、店ごとの「会計の売上高 ÷ 届いた POS の売上」で補った場合の判定と比べ、変わりうるものを「境目」として予告する
    unsure = []
    if close_day is not None:
        hi = sm.copy(); k = hi.ym == ym
        hi[["sales", "receipts", "items", "gross_profit_before_waste", "gross_profit", "member_receipts", "operating_profit"]] = hi[["sales", "receipts", "items", "gross_profit_before_waste", "gross_profit", "member_receipts", "operating_profit"]].astype(float)
        r = arr_s.reindex(hi.loc[k, "store_id"]).values
        for c in ("sales", "receipts", "items", "gross_profit_before_waste", "gross_profit", "member_receipts"):
            hi.loc[k, c] = hi.loc[k, c] / r
        hi.loc[k, "operating_profit"] = hi.loc[k, "gross_profit"] - hi.loc[k, "labor_cost"] - hi.loc[k, "other_cost"]
        Jh, PJh = judge_company(company_kpi(hi, I["final"], I["fm"], ym, I["plan"], I["cal"], I["mkt"]), hist, sig)
        unsure = [f"KPI:{q}" for q in J if J[q]["flag"] != Jh[q]["flag"]] + [f"計画:{q}" for q in PJ if PJ[q]["flag"] != PJh[q]["flag"]]
    R = {"ym": ym, "version": version, "close_day": close_day, "arrived": arrived, "held": held, "unsure": unsure, "K": K, "J": J, "PJ": PJ,
         "exceptions": shown, "exceptions_hidden": hidden, "n_store_tests": int(len(devs[ym]) * len(SKPIS))}
    R["summary"] = summarize(R)
    R["actions"] = make_actions(R, prev_actions)
    R["not_shown"] = not_shown(R)
    return R


def _f(v, kind, sign=True):
    if pd.isna(v):
        return "―"
    s = (("%+.2f" if sign else "%.2f") if kind == "pt" else ("%+.1f" if sign else "%.1f")) % v
    return s.replace("-", "−") + ("%" if kind == "pct" else "pt")


def summarize(R):
    K, J, PJ = R["K"], R["J"], R["PJ"]
    op, op_p = K["all"]["operating_profit"] / 1e6, K["plan"]["plan_op"] / 1e6
    s1 = "営業利益（全店）は %.0f 百万円で、前年比 %s、計画比 %s" % (op, _f(K["yoy"]["K00"], "pct"), _f(PJ["K00"]["gap"], "pct"))
    s1 += "（計画を幅を超えて下回った" if PJ["K00"]["flag"] < 0 else "（計画を幅を超えて上回った" if PJ["K00"]["flag"] > 0 else "（計画との差は偶然の幅の中"
    s1 += "。ただし境目で、確定版で確かめる）。" if "計画:K00" in R.get("unsure", []) else "）。"
    roots = [k for k, _, _ in KPIS if J[k]["flag"] != 0 and not J[k]["explained_by"] and k != "K00"]
    deps = [k for k, _, _ in KPIS if J[k]["flag"] != 0 and J[k]["explained_by"]]
    if roots:
        s2 = "先月までと流れが変わったのは " + "、".join("%s（%s）" % (KNAME[k], "上向き" if J[k]["flag"] > 0 else "下向き") for k in roots) + "。"
        if deps:
            s2 += "%sの動きもこれで説明できる。" % "・".join(KNAME[k] for k in deps)
    elif deps:
        s2 = "%sは先月までと動いたが、市場と同じ売上の動きで説明できる（既存店売上の市場との差 %s は幅の中）。" % ("・".join(KNAME[k] for k in deps), _f(K["yoy_mkt"]["K01"], "pct"))
    else:
        s2 = "ほかの KPI は先月までと同じ流れ（既存店売上 %s は単価 %s が中心）。" % (_f(K["yoy"]["K01"], "pct"), _f(K["yoy"]["K04"], "pct"))
    ex = R["exceptions"]
    if ex:
        e = ex[0]
        s3 = "店では %s の%s（真ん中の店との差 %s、%s）など %d 件。" % (e["who"], SNAME[e["kpi"]], _f(e["dev"], SKIND[e["kpi"]]),
                                                     "%dか月続く" % e["months_run"] if e["months_run"] >= 2 else "今月から", len(ex) + len(R["exceptions_hidden"]))
    else:
        s3 = "決まりを満たす店の例外はなし。"
    return [s1, s2, s3]


def make_actions(R, prev_actions):
    acts = []
    for e in R["exceptions"]:
        role, txt = ACTIONS[(e["kpi"], e["sign"])]
        acts.append({"what": f"{e['who']}：{txt}", "role": role, "due": "次の月次（%s）まで" % _ym(R["ym"], 1), "key": e["kpi"], "stores": e["stores"]})
    for k, _, _ in KPIS:
        if R["J"][k]["flag"] != 0 and not R["J"][k]["explained_by"]:
            acts.append({"what": f"{KNAME[k]}の動きを部門・地域に分けて確かめる", "role": "分析担当", "due": "%s 15日まで" % _ym(R["ym"], 1), "key": k})
    if R["PJ"]["K00"]["flag"] < 0:
        acts.append({"what": "営業利益の計画との差を、残りの月の見通しに反映する", "role": "経営企画", "due": "次の経営会議", "key": "plan"})
    status = []
    for a in (prev_actions or []):
        still = any(a["key"] == b["key"] and set(a.get("stores", [])) == set(a.get("stores", [])) & set(b.get("stores", a.get("stores", [])))
                    or (a["key"] == b["key"] and set(a.get("stores", [])) & set(b.get("stores", []))) for b in acts)
        hold = set(a.get("stores", [])) & set(R.get("held", []))
        st_ = "続く（今月も例外）" if still else "保留（速報では判定しない店。確定版で判定）" if hold else "今月は例外から外れた"
        status.append({"what": a["what"], "role": a["role"], "status": st_})
    return {"new": acts, "prev": status}


def not_shown(R):
    J = R["J"]
    calm = [KNAME[k] for k, _, _ in KPIS if J[k]["flag"] == 0]
    return {"calm_kpis": calm, "hidden_exceptions": len(R["exceptions_hidden"]), "n_store_tests": R["n_store_tests"],
            "fixed": ["店ごとの営業利益（1店・月の偶然の幅が ±205%）", "日ごとの上下（1店・日の売上の幅 ±20%）", "幅の中の動きの理由"]}


# ---------------------------------------------------------------- 出力（Markdown・HTML）
def bridge_png(R):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Noto Sans CJK JP"
    K = R["K"]; fig, ax = plt.subplots(1, 2, figsize=(9.2, 2.9), dpi=110, gridspec_kw={"width_ratios": [1, 1.35]})
    c, p = K["existing_cur"], K["existing_prv"]
    parts = {"客数": (c["receipts"] / p["receipts"] - 1) * 100, "買上点数": ((c["items"] / c["receipts"]) / (p["items"] / p["receipts"]) - 1) * 100,
             "一品単価": ((c["sales"] / c["items"]) / (p["sales"] / p["items"]) - 1) * 100}
    tot = K["yoy"]["K01"]
    xs = list(parts) + ["既存店売上"]; vs = list(parts.values()) + [tot]
    cols = ["#2a6fb0" if v >= 0 else "#c0504d" for v in vs[:-1]] + ["#555"]
    ax[0].bar(xs, vs, color=cols); ax[0].axhline(0, color="#999", lw=0.8)
    for x, v in zip(xs, vs):
        ax[0].text(x, v + (0.15 if v >= 0 else -0.15), _f(v, "pct"), ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5)
    ax[0].set_title("既存店売上の前年比の分解", fontsize=10); ax[0].tick_params(labelsize=8.5)
    ax[0].set_ylim(min(0, min(vs)) - 1.2, max(0, max(vs)) + 1.2); ax[0].spines[["top", "right"]].set_visible(False)
    b = K["plan"]["bridge"]; start = K["plan"]["plan_op"] / 1e6
    lab = ["計画"] + list(b) + ["実績"]; cur = start; xs2 = range(len(lab))
    ax[1].bar(0, start, color="#999")
    for i, (k, v) in enumerate(b.items(), 1):
        v /= 1e6
        ax[1].bar(i, v, bottom=cur if v >= 0 else cur + v, color="#2a6fb0" if v >= 0 else "#c0504d")
        ax[1].text(i, max(cur, cur + v) + 1, ("%+.1f" % v).replace("-", "−"), ha="center", fontsize=8.5)
        cur += v
    ax[1].bar(len(lab) - 1, cur, color="#555")
    ax[1].text(0, start + 1, "%.0f" % start, ha="center", fontsize=8.5); ax[1].text(len(lab) - 1, cur + 1, "%.0f" % cur, ha="center", fontsize=8.5)
    ax[1].set_xticks(list(xs2)); ax[1].set_xticklabels([l.replace("の差", "") for l in lab], fontsize=8.5)
    ax[1].set_title("営業利益（全店）：計画との差の分解（百万円）", fontsize=10); ax[1].spines[["top", "right"]].set_visible(False)
    ax[1].set_ylim(0, max(start, cur) * 1.18); ax[1].tick_params(labelsize=8.5)
    fig.tight_layout(); bio = io.BytesIO(); fig.savefig(bio, format="png"); plt.close(fig)
    return base64.b64encode(bio.getvalue()).decode()


def _jcell(j, k):
    if not j["judged"]:
        return '<span class="calm">計画比で判定</span>'
    if j["flag"] != 0 and j["explained_by"]:
        return '<span class="%s">%s 動いた</span><br><span class="sm">%sで説明</span>' % ("up" if j["flag"] > 0 else "dn", "▲" if j["flag"] > 0 else "▼", _ename(j["explained_by"]))
    if j["flag"] > 0:
        return '<span class="up">▲ 流れが変わった</span>'
    if j["flag"] < 0:
        return '<span class="dn">▼ 流れが変わった</span>'
    return '<span class="calm">幅の中</span>'


def _ename(e):
    return "・".join("市場と同じ売上の動き" if c == "MKT" else KNAME[c] for c in e[:2])


def fmt_level(k, v):
    if k in ("K00", "K10", "K01"):
        return "%s 百万円" % format(round(v / 1e6), ",")
    if k == "K02":
        return "%s 枚" % format(round(v), ",")
    if k == "K03":
        return "%.2f 点" % v
    if k == "K04":
        return "%.1f 円" % v
    if k == "K05":
        return "%.2f 回" % v
    if k == "K08":
        return "%s 円" % format(round(v), ",")
    return "%.2f%%" % v


def render_html(R, log=None):
    K, J, PJ = R["K"], R["J"], R["PJ"]
    y, m = R["ym"].split("-")
    ver = "v1 速報" if R["version"] == "v1" else "v2 確定"
    made = ("%s-06" % _ym(R["ym"], 1)) if R["version"] == "v1" else ("%s-20" % _ym(R["ym"], 1))
    note_v = ("翌月%d日までに届いた POS で作成。売上の届いた割合 %.1f%%。既存店売上の前年比は、確定までに平均 0.5pt・最大 1.6pt 上に動くことがある（F247 の測定）。"
              % (R["close_day"], R["arrived"] * 100)) if R["version"] == "v1" else "すべてのデータが届いたあとの確定版（売上の届いた割合 %.1f%%）。" % (R["arrived"] * 100)
    rows = []
    for k, n, t in KPIS:
        j = J[k]
        yo = _f(K["yoy"][k], t)
        if k in CAL_ADJ and "yoy_adj" in K:
            yo += '<br><span class="sm">曜日補正後 %s</span>' % _f(K["yoy_adj"][k], t)
        if k in MKT_ADJ and "yoy_mkt" in K:
            yo += '<br><span class="sm">市場との差 %s</span>' % _f(K["yoy_mkt"][k], t)
        pl = _f(PJ[k]["gap"], "pct") if k in PJ else ""
        if f"計画:{k}" in R.get("unsure", []):
            pl += '<br><span class="sm">境目（確定版で確認）</span>'
        jc = _jcell(j, k) + ('<br><span class="sm">境目（確定版で確認）</span>' if f"KPI:{k}" in R.get("unsure", []) else "")
        if k in PJ and PJ[k]["flag"] != 0:
            pl = '<b class="%s">%s</b>' % ("dn" if PJ[k]["flag"] < 0 else "up", pl)
        rows.append(f"<tr><td class='l'>{n}</td><td>{fmt_level(k, K['level'][k])}</td><td>{yo}</td><td>{pl}</td>"
                    f"<td>{_f(j['trail'], t) if j['judged'] else ''}</td><td>±{(j['width'] if j['judged'] else PJ[k]['width']):.{2 if t == 'pt' else 1}f}{'%' if t == 'pct' else 'pt'}</td><td>{jc}</td></tr>")
    if "market" in K:
        rows.append(f"<tr class='ref'><td class='l'>参考：市場（スーパー販売額）</td><td></td><td>{_f(K['market'], 'pct')}</td><td></td><td></td><td></td><td><span class='calm'>参考</span></td></tr>")
    ex = "".join(f"<tr><td class='l'>{e['who']}</td><td>{SNAME[e['kpi']]}{'<br><span class=sm>（' + '・'.join(e['also']) + ' も）</span>' if e['also'] else ''}</td><td>{_f(e['dev'], SKIND[e['kpi']])}</td>"
                 f"<td>{e['why']}（{e['months_run']}か月）</td><td>{e['impact']:+.1f}</td></tr>".replace("+-", "−").replace("-", "−")
                 for e in R["exceptions"]) or "<tr><td colspan=5 class='l'>決まりを満たす店はなし</td></tr>"
    acts = "".join(f"<tr><td class='l'>{a['what']}</td><td>{a['role']}</td><td>{a['due']}</td></tr>" for a in R["actions"]["new"]) or "<tr><td colspan=3 class='l'>なし</td></tr>"
    prev = "".join(f"<li>{a['what']}（{a['role']}）→ {a['status']}</li>" for a in R["actions"]["prev"]) or "<li>前月のアクションなし</li>"
    drivers = []
    for k, _, t in KPIS:
        if J[k]["flag"] != 0 and not J[k]["explained_by"]:
            drivers.append(f"<li><b>{KNAME[k]}</b>（{J[k]['basis']}）：{_f(J[k]['value'], t)}。先月までの3か月の平均 {_f(J[k]['trail'], t)} から {_f(J[k]['diff'], t)}（幅 ±{J[k]['width']:.{2 if t == 'pt' else 1}f}）。理由は分析担当が部門・地域に分けて次の月次までに報告する。</li>")
    dep = [k for k, _, _ in KPIS if J[k]["flag"] != 0 and J[k]["explained_by"]]
    if dep:
        drivers.append("<li>%s も流れが変わったが、KPI ツリーの下の動き（%s）で説明できるので、別には書かない。</li>" % ("・".join(KNAME[k] for k in dep), "、".join(sorted(set(_ename(J[k]["explained_by"]) for k in dep)))))
    if not drivers:
        drivers.append("<li>流れが変わった KPI はなし。売上の伸びは一品単価（物価）、利益の重しは廃棄率と時給の上昇、という先月までの説明のまま。</li>")
    b = K["plan"]["bridge"]; big = max(b, key=lambda x: abs(b[x]))
    drivers.append(f"<li>営業利益の計画との差 {(K['all']['operating_profit'] - K['plan']['plan_op']) / 1e6:+.1f} 百万円のうち、いちばん大きいのは{big.replace('の差', '')}（{b[big] / 1e6:+.1f} 百万円）。</li>".replace("+-", "−").replace("-", "−"))
    ns = R["not_shown"]
    logh = "".join(f"<tr><td>{l['version']}</td><td>{l['date']}</td><td class='l'>{l['note']}</td></tr>" for l in (log or []))
    img = bridge_png(R)
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>月次レポート {y}年{int(m)}月 {ver}</title>
<style>
body{{font-family:'Noto Sans CJK JP','Noto Sans JP',sans-serif;color:#222;margin:0;background:#fff}}
.page{{width:900px;margin:0 auto;padding:22px 30px}}
h1{{font-size:21px;margin:0 0 2px}} h2{{font-size:15px;border-left:5px solid #2a6fb0;padding-left:8px;margin:18px 0 6px}}
.meta{{font-size:11.5px;color:#555}} .badge{{display:inline-block;padding:1px 8px;border-radius:3px;font-size:12px;color:#fff;background:{'#d98200' if R['version']=='v1' else '#2a7d3f'};margin-left:6px;vertical-align:middle}}
.fict{{font-size:11px;color:#a33;margin-top:2px}}
ol.sum{{margin:4px 0 0 0;padding-left:22px;font-size:14px;line-height:1.6}}
table{{border-collapse:collapse;width:100%;font-size:12px}} th,td{{border-bottom:1px solid #ddd;padding:4px 6px;text-align:right;vertical-align:top}}
th{{background:#f2f4f7;font-weight:600;text-align:center}} td.l{{text-align:left}}
tr.ref td{{color:#666;font-size:11px}} .up{{color:#1f5fa0;font-weight:600}} .dn{{color:#b8312f;font-weight:600}} .calm{{color:#999}} .sm{{font-size:10.5px;color:#666}}
ul{{margin:4px 0;padding-left:20px;font-size:12.5px;line-height:1.55}} .note{{font-size:11.5px;color:#555}}
</style></head><body><div class="page">
<h1>サンプルマート（架空） 月次レポート {y}年{int(m)}月 <span class="badge">{ver}</span></h1>
<div class="meta">作成 {made}｜{note_v}｜既存店 {K['n_existing']} 店</div>
<div class="fict">会社・数字はすべて架空（合成データ）。実在の会社とは関係がない。</div>
<h2>1. 今月のまとめ</h2><ol class="sum">{''.join(f'<li>{s}</li>' for s in R['summary'])}</ol>
<h2>2. KPI 表（行は毎月同じ）</h2>
<table><tr><th>KPI</th><th>今月</th><th>前年比・前年差</th><th>計画比</th><th>先月までの3か月</th><th>偶然の幅</th><th>判定</th></tr>{''.join(rows)}</table>
<div class="note">前年比は既存店どうし（営業利益・売上（全店）は全店）。判定は「先月までの3か月の平均から、偶然の幅（±1.96σ）を超えて動いたか」。既存店売上・客数は市場（経済産業省「商業動態統計」スーパー販売額）の前年比との差で判定。上の KPI の動きが下の KPI で説明できるときは、説明は下で1回だけ。</div>
<h2>3. 要因</h2><img src="data:image/png;base64,{img}" style="width:100%">
<ul>{''.join(drivers)}</ul>
<h2>4. 例外（店）</h2>
<table><tr><th>店</th><th>KPI</th><th>真ん中の店との差</th><th>決まり（続いている月数）</th><th>利益への影響の目安（百万円）</th></tr>{ex}</table>
<div class="note">店は {ns['n_store_tests']} 通り（既存店 × 5つの KPI）を、既存店の真ん中の店（中央値）と比べ、「今月 3σ 超え」か「3か月続けて同じ向きに 1σ 超え」だけを載せる。同じ地域で同じ向きが3店以上なら1行にまとめる。5行を超えた分は {ns['hidden_exceptions']} 件（付録）。{('速報のため、売上の届いた割合が99.5%未満の ' + str(len(R['held'])) + ' 店（' + '・'.join('%02d' % h for h in R['held']) + '店）は判定を確定版に回した。') if R['held'] else ''}</div>
<h2>5. 次のアクション</h2>
<table><tr><th>内容</th><th>担当（役割）</th><th>期限</th></tr>{acts}</table>
<div class="note">前月のアクション</div><ul>{prev}</ul>
<h2>6. 載せなかったもの・改訂履歴</h2>
<ul><li>幅の中の KPI（{len(ns['calm_kpis'])} 行）は数字だけ載せ、理由は書かない：{'、'.join(ns['calm_kpis'])}</li>
{''.join(f'<li>毎月載せない：{x}</li>' for x in ns['fixed'])}</ul>
<table><tr><th>版</th><th>日付</th><th>内容</th></tr>{logh}</table>
</div></body></html>"""


def render_md(R, log=None):
    K, J, PJ = R["K"], R["J"], R["PJ"]
    y, m = R["ym"].split("-")
    L = [f"# サンプルマート（架空） 月次レポート {y}年{int(m)}月（{'v1 速報' if R['version'] == 'v1' else 'v2 確定'}）", "",
         "> 会社・数字はすべて架空（合成データ）。", "", "## 1. 今月のまとめ"] + [f"{i}. {s}" for i, s in enumerate(R["summary"], 1)]
    L += ["", "## 2. KPI 表", "| KPI | 今月 | 前年比 | 計画比 | 先月までの3か月 | 偶然の幅 | 判定 |", "|---|---|---|---|---|---|---|"]
    for k, n, t in KPIS:
        j = J[k]; jj = "▲" if j["flag"] > 0 else "▼" if j["flag"] < 0 else "幅の中"
        L.append(f"| {n} | {fmt_level(k, K['level'][k])} | {_f(K['yoy'][k], t)} | {_f(PJ[k]['gap'], 'pct') if k in PJ else ''} | {_f(j['trail'], t)} | ±{j['width']:.1f} | {jj} |")
    L += ["", "## 4. 例外（店）"] + [f"- {e['who']}：{SNAME[e['kpi']]} 真ん中の店との差 {_f(e['dev'], SKIND[e['kpi']])}（{e['why']}、{e['months_run']}か月）" for e in R["exceptions"]]
    L += ["", "## 5. 次のアクション"] + [f"- {a['what']}（{a['role']}、{a['due']}）" for a in R["actions"]["new"]]
    L += ["", "## 6. 改訂履歴"] + [f"- {l['version']} {l['date']}：{l['note']}" for l in (log or [])]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- 版の差
def judgments(R):
    """出し直すかどうかを決める「判定」の集まり"""
    j = {f"KPI:{k}": R["J"][k]["flag"] for k, _, _ in KPIS}
    j.update({f"計画:{k}": R["PJ"][k]["flag"] for k in R["PJ"]})
    for e in R["exceptions"] + R["exceptions_hidden"]:
        for sid in e["stores"]:
            j[f"例外:{sid:02d}店:{e['kpi']}"] = e["sign"]
    return j


def diff_versions(R1, R2):
    """v1 で保留にした店の判定は「変わった」に数えない（保留と書いてあるので）"""
    a, b = judgments(R1), judgments(R2)
    held = {f"{h:02d}店" for h in R1.get("held", [])}
    keys = sorted(set(a) | set(b))
    ch = [(k, a.get(k, 0), b.get(k, 0)) for k in keys if a.get(k, 0) != b.get(k, 0) and not (k.startswith("例外:") and k.split(":")[1] in held)
          and k not in R1.get("unsure", [])]
    num = {k: R2["K"]["yoy"][k] - R1["K"]["yoy"][k] for k, _, _ in KPIS}
    naive = [(k, a.get(k, 0), b.get(k, 0)) for k in keys if a.get(k, 0) != b.get(k, 0)]   # 保留・境目の予告がない場合に「変わった」と見えるもの
    return ch, num, naive


def _jlabel(k):
    t, q = k.split(":", 1)
    if t == "KPI":
        return KNAME[q] + "の判定"
    if t == "計画":
        return KNAME[q] + "の計画比の判定"
    sid, kk = q.split(":")
    return f"{sid}の{SNAME[kk]}"


def revision_note(ch, num, sig, naive=()):
    """v2 はいつも同じ場所で v1 と置き換える。全員に知らせ直すのは、予告していない判定が変わったときだけ"""
    big = max(num, key=lambda k: abs(num[k]))
    moved = ("数字の動きは最大で %s の前年比 %spt。" if KKIND[big] == "pct" else "数字の動きは最大で %s の前年差 %spt。") % (KNAME[big], ("%+.1f" % num[big]).replace("-", "−"))
    pre = [k for k, _, _ in naive if k not in {c for c, _, _ in ch}]
    pre_txt = ("速報で境目・保留とした %d つが確定（%s）。" % (len(pre), "、".join(_jlabel(k) for k in pre))) if pre else ""
    if not ch:
        return False, "確定版に置き換え（知らせ直しなし）。" + pre_txt + moved
    return True, "予告していない判定が %d つ変わったので知らせ直し：" % len(ch) + "、".join(_jlabel(k) for k, _, _ in ch) + "。" + pre_txt + moved


def jdump(o, p):
    def cv(x):
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, (np.floating,)):
            return float(x)
        return str(x)
    p.write_text(json.dumps(o, ensure_ascii=False, indent=1, default=cv), encoding="utf-8")


# ---------------------------------------------------------------- 実行
if __name__ == "__main__":
    RES.mkdir(exist_ok=True); REP.mkdir(exist_ok=True)
    wp = RES / "A_noise_widths.csv"
    W, comp, stor, _ = noise_widths()
    W.to_csv(wp, index=False, encoding="utf-8-sig"); print(W)
    sig = dict(zip(W.id, W.sigma))
    I = load_inputs()
    prev_actions, rows, revs = None, [], []
    for ym in MONTHS:
        R1 = build_report(I, ym, "v1", 5, sig, sig, prev_actions)
        R2 = build_report(I, ym, "v2", None, sig, sig, prev_actions)
        ch, num, naive = diff_versions(R1, R2)
        reissue, note = revision_note(ch, num, sig, naive)
        log1 = [{"version": "v1", "date": "%s-06" % _ym(ym, 1), "note": "速報（翌月5日の締め、売上の届いた割合 %.1f%%）" % (R1["arrived"] * 100)}]
        log2 = log1 + [{"version": "v2", "date": "%s-20" % _ym(ym, 1), "note": note}]
        tag = ym.replace("-", "")
        (REP / f"report_{tag}_v1.html").write_text(render_html(R1, log1), encoding="utf-8")
        (REP / f"report_{tag}_v2.html").write_text(render_html(R2, log2), encoding="utf-8")
        (REP / f"report_{tag}_v2.md").write_text(render_md(R2, log2), encoding="utf-8")
        jdump({"v1": R1, "v2": R2, "changes": ch, "changes_naive": naive, "reissue": reissue, "note": note}, REP / f"report_{tag}.json")
        prev_actions = R2["actions"]["new"]
        rows.append({"ym": ym, "v1_arrived": R1["arrived"], "op_yoy": R2["K"]["yoy"]["K00"], "op_vs_plan": R2["PJ"]["K00"]["gap"],
                     "op_plan_flag": R2["PJ"]["K00"]["flag"], "sales_vs_plan": R2["PJ"]["K10"]["gap"], "existing_yoy": R2["K"]["yoy"]["K01"],
                     "existing_yoy_v1": R1["K"]["yoy"]["K01"], "kpi_moved": sum(R2["J"][k]["flag"] != 0 for k, _, _ in KPIS),
                     "kpi_moved_list": "、".join(KNAME[k] for k, _, _ in KPIS if R2["J"][k]["flag"] != 0),
                     "exceptions_shown": len(R2["exceptions"]), "exceptions_hidden": len(R2["exceptions_hidden"]),
                     "exceptions_list": " / ".join(f"{e['who']} {SNAME[e['kpi']]}{'+' if e['sign'] > 0 else '−'}" for e in R2["exceptions"]),
                     "v1_v2_changes": len(ch), "v1_v2_changes_naive": len(naive), "v1_unsure": len(R1["unsure"]), "v1_held": len(R1["held"]),
                     "naive_list": "、".join(k for k, _, _ in naive), "reissue": reissue, "note": note})
        print(ym, rows[-1]["kpi_moved_list"], "|", rows[-1]["exceptions_list"], "|", note)
    pd.DataFrame(rows).to_csv(RES / "B_reports_fy2025.csv", index=False, encoding="utf-8-sig")
