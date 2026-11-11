"""dq_check：毎月の数字の品質チェック（この記事の成果物）。

確定（または速報）の mart の「その月の分」に、次の8つのチェックをかけ、引っかかった行を一覧にする。
どんな汚れが入っているかを前もって知らなくても使えるよう、チェックは「汚れの種類」ではなく「ありえない形」で書いた。

| ID  | チェック | 何を見るか |
|-----|----------|------------|
| Q01 | キーの重複 | 店×日が2行以上ある |
| Q02 | 行の欠け | 営業しているはずの店×日の行がない（開店日・閉店日は dim_store から） |
| Q03 | 空の値 | 必須の列が空 |
| Q04 | 営業日のゼロ | 営業しているはずの日に、売上・客数・点数・人時が0以下 |
| Q05 | ほかの日と同じ値 | 客数・点数・売上が、同じ店のほかの日（その月と前の7日）と1円まで同じ |
| Q06 | ふだんとの比 | 売上・客数・点数・人時・廃棄が、その店のふだんの値の T 倍より大きいか 1/T より小さい（T は売上・客数・点数・人時 1.5、廃棄 2.0） |
| Q07 | 中の関係 | 一品単価・1回の買上点数・時給・廃棄率が、その店のふだんの値から外れる。会員の客数が客数より多い |
| Q08 | 部門の合計 | 部門の売上の合計が、店の売上と 0.5% 以上違う。片方にしか行がない |

重さ：A＝数字が確実に壊れている（Q01〜Q05・Q08、Q06・Q07 で5倍以上・5分の1以下のずれ）。直すまで、その店×日を月の数字から外す。
      B＝ふだんと大きく違う（Q06・Q07 のそれ以外）。店に確かめてから出す。保留＝速報の未着（確定でもう一度チェック）。

「その店のふだんの値」（Q06・Q07）は、チェックする月より前の確定の数字だけから作る（その月の数字は使わない）。
- 参照 a：月初の前の8週の、同じ曜日の中央値
- 参照 b：364日前（同じ曜日）の値 × その店の伸び（月初の前の8週の合計 ÷ その1年前の8週の合計）。曜日で動くものに合う
- 参照 c：1年前の同じ日付の値 × 同じ伸び。年末（12/28〜31）のように「毎年同じ日付で動く」ものに合う
- 既定（ref_mode="abc"）は、使える参照のうち「ずれのいちばん小さいもの」で判定する（どの参照から見てもおかしいときだけ鳴らす）。
  b・c がない店（開店から1年たっていない）は a だけ、a もない店（開店から8週たっていない）は判定しない（info に残す）。

使い方：
    python src/dq_check.py --month 2025-12 --mart data/in --out reports
    （mart のフォルダに fact_store_day.csv.gz・fact_store_day_category.csv.gz・dim_store.csv・dim_date.csv があること）
会社・数字はすべて架空（合成データ）。
"""
import argparse, json, pathlib, warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import numpy as np
import pandas as pd

KEY = ["biz_date", "store_id"]
REQ = ["receipts", "member_receipts", "items", "sales", "gross_profit_before_waste", "waste", "labor_hours", "labor_cost"]
SAME = ["receipts", "items", "sales"]
RATIO = ["sales", "receipts", "items", "labor_hours", "waste"]
INNER = {"一品単価": ("sales", "items", 1.5), "買上点数": ("items", "receipts", 1.5),
         "時給": ("labor_cost", "labor_hours", 1.5), "廃棄率": ("waste", "sales", 2.0)}
BIG = 5.0   # これ以上のずれは「桁・単位の疑い」（重さ A）
DEFAULT_T = {"sales": 1.5, "receipts": 1.5, "items": 1.5, "labor_hours": 1.5, "waste": 2.0}   # 03_分析.py の結果から決めた線
JP = {"sales": "売上", "receipts": "客数", "items": "点数", "labor_hours": "人時", "waste": "廃棄", "member_receipts": "会員の客数",
      "gross_profit_before_waste": "廃棄前の粗利", "labor_cost": "人件費"}
CHECKS = {
    "Q01": ("キーの重複", "A", "重複した行のどちらを残すか、送り元（POS・勤怠）に確かめる。確かめるまで、その店×日は月の数字から除いて表示しない"),
    "Q02": ("行の欠け", "A", "送り元に再送を頼む。速報では『未着』として保留し、確定でもう一度チェックする"),
    "Q03": ("空の値", "A", "送り元に確かめる。埋めるときは埋めた印をつける（F247 の人時と同じ）"),
    "Q04": ("営業日のゼロ", "A", "休業・システム停止の連絡があったかを店に確かめる。なければ欠測として再送を頼む"),
    "Q05": ("ほかの日と同じ値", "A", "前の日のファイルの送り直しを疑い、送り元に確かめる"),
    "Q06": ("ふだんとの比", "B", "店のできごと（改装・イベント・休業）を確かめ、なければ桁・単位・二重の取り込みを疑う"),
    "Q07": ("中の関係", "B", "どちらの列がおかしいか（単位・桁）を確かめる"),
    "Q08": ("部門の合計", "A", "店と部門のファイルのどちらが欠けたか・重複したかを確かめる"),
}


def month_days(month):
    p = pd.Period(month, "M")
    return pd.date_range(p.start_time, p.end_time.normalize(), freq="D")


def expected_rows(dim_store, month):
    days = month_days(month)
    rows = []
    for _, s in dim_store.iterrows():
        o = pd.Timestamp(s.open_date)
        c = pd.Timestamp(s.close_date) if pd.notna(s.close_date) else pd.Timestamp("2099-12-31")
        d = days[(days >= o) & (days <= c)]
        rows.append(pd.DataFrame({"biz_date": d, "store_id": s.store_id}))
    return pd.concat(rows, ignore_index=True)


def references(hist, keys, cols, m0, weeks=8, level_weeks=8):
    """keys（biz_date, store_id）ごとに、cols の参照 a・b を返す。hist はチェックする月より前の確定の店×日"""
    out = keys[KEY].drop_duplicates().copy()
    out["dow"] = out.biz_date.dt.dayofweek
    h = hist[(hist.biz_date < m0)].copy()
    w = h[h.biz_date >= m0 - pd.Timedelta(weeks=weeks)].copy()
    w["dow"] = w.biz_date.dt.dayofweek
    a = w.groupby(["store_id", "dow"])[cols].median()
    a.columns = [c + "__a" for c in cols]
    out = out.merge(a, left_on=["store_id", "dow"], right_index=True, how="left")
    # 参照 b：364日前の値 × 伸び
    lw0, lw1 = m0 - pd.Timedelta(weeks=level_weeks), m0
    this = h[(h.biz_date >= lw0) & (h.biz_date < lw1)].groupby("store_id")[cols].sum()
    prev = h[(h.biz_date >= lw0 - pd.Timedelta(days=364)) & (h.biz_date < lw1 - pd.Timedelta(days=364))]
    nthis = h[(h.biz_date >= lw0) & (h.biz_date < lw1)].groupby("store_id").size()
    nprev = prev.groupby("store_id").size()
    prev = prev.groupby("store_id")[cols].sum()
    full = (nthis.reindex(prev.index) == nprev) & (nprev == level_weeks * 7)   # 前年の8週がそろっている店だけ
    lev = (this.reindex(prev.index) / prev.replace(0, np.nan))[full]
    for tag, shift in (("b", "364d"), ("c", "1y")):
        ly = h[["biz_date", "store_id"] + cols].copy()
        ly["biz_date"] = ly.biz_date + (pd.Timedelta(days=364) if shift == "364d" else pd.DateOffset(years=1))
        ly = ly.drop_duplicates(KEY)
        b = out[KEY].merge(ly, on=KEY, how="left")
        for c in cols:
            out[c + "__" + tag] = b[c].values * out.store_id.map(lev[c] if c in lev else pd.Series(dtype=float)).values
    return out


def _ratio_flags(cur, ref, cols, T, ref_mode, check, label=None):
    m = cur.merge(ref, on=KEY, how="left")
    rows = []
    for c in cols:
        v = m[c].astype(float)
        lr = pd.Series(np.nan, index=m.index); rf = pd.Series(np.nan, index=m.index)
        for tag in ref_mode:   # 参照が複数あれば、ずれのいちばん小さいもので判定する
            r = m[c + "__" + tag]
            l = np.log(v / r).where((v > 0) & (r > 0))
            use = l.notna() & (lr.isna() | (l.abs() < lr.abs()))
            lr = lr.where(~use, l); rf = rf.where(~use, r)
        t = T[c] if isinstance(T, dict) else T
        hit = lr.abs() > np.log(t)
        for i in np.flatnonzero(hit.values):
            rows.append(dict(check=check, store_id=int(m.store_id.iat[i]), biz_date=m.biz_date.iat[i], metric=label or JP.get(c, c),
                             value=float(v.iat[i]), ref=float(rf.iat[i]), ratio=float(np.exp(lr.iat[i]))))
    return rows


def run_checks(cur, cat, hist, hist_cat, dim_store, month, T=None, ref_mode="abc", weeks=8, mode="確定", inner_T=None):
    """cur：その月の店×日（そのまま。重複・欠け・空があってもよい）、cat：その月の店×日×部門、hist：前の月までの確定の店×日。
    返り値：(flags, info)。flags は引っかかった行の一覧（1行＝1つのチェック×1つの店×日×列）。"""
    m0 = pd.Period(month, "M").start_time
    T = DEFAULT_T if T is None else T
    cur = cur.copy(); cur["biz_date"] = pd.to_datetime(cur.biz_date)
    flags, info = [], {}
    # Q01 キーの重複
    d = cur[cur.duplicated(KEY, keep=False)]
    for (bd, sid), g in d.groupby(["biz_date", "store_id"]):
        flags.append(dict(check="Q01", store_id=int(sid), biz_date=bd, metric="行", value=float(len(g)), ref=1.0, ratio=float(len(g))))
    # Q02 行の欠け
    exp = expected_rows(dim_store, month)
    miss = exp.merge(cur[KEY].drop_duplicates(), on=KEY, how="left", indicator=True)
    miss = miss[miss._merge == "left_only"]
    for _, r in miss.iterrows():
        flags.append(dict(check="Q02", store_id=int(r.store_id), biz_date=r.biz_date, metric="行", value=0.0, ref=1.0, ratio=0.0))
    extra = cur[KEY].merge(exp, on=KEY, how="left", indicator=True)
    for _, r in extra[extra._merge == "left_only"].drop_duplicates(KEY).iterrows():   # 営業していないはずの日の行
        flags.append(dict(check="Q02", store_id=int(r.store_id), biz_date=r.biz_date, metric="営業日の外の行", value=1.0, ref=0.0, ratio=np.inf))
    # Q03 空の値
    for c in REQ:
        for _, r in cur[cur[c].isna()].iterrows():
            flags.append(dict(check="Q03", store_id=int(r.store_id), biz_date=r.biz_date, metric=JP.get(c, c), value=np.nan, ref=np.nan, ratio=np.nan))
    # Q04 営業日のゼロ
    for c in ["sales", "receipts", "items", "labor_hours"]:
        for _, r in cur[cur[c] <= 0].iterrows():
            flags.append(dict(check="Q04", store_id=int(r.store_id), biz_date=r.biz_date, metric=JP[c], value=float(r[c]), ref=np.nan, ratio=0.0))
    # Q05 ほかの日と同じ値（その月と、前の7日）
    prev7 = hist[(hist.biz_date >= m0 - pd.Timedelta(days=7)) & (hist.biz_date < m0)][KEY + SAME]
    s = pd.concat([cur[KEY + SAME].assign(_cur=1), prev7.assign(_cur=0)], ignore_index=True).dropna(subset=SAME)
    s = s[(s.sales > 0)]
    s["_k"] = s.receipts.astype(int).astype(str) + "_" + s["items"].astype(int).astype(str) + "_" + s.sales.round(0).astype(int).astype(str)
    s = s.drop_duplicates(KEY + ["_k"])
    g = s.groupby(["store_id", "_k"]).biz_date.transform("nunique")
    for _, r in s[(g > 1) & (s._cur == 1)].iterrows():
        flags.append(dict(check="Q05", store_id=int(r.store_id), biz_date=r.biz_date, metric="客数・点数・売上", value=float(r.sales), ref=np.nan, ratio=1.0))
    # Q06・Q07 は重複を除いた行で（重複は Q01 で別に出している）
    cu = cur.drop_duplicates(KEY, keep="first")
    cols_in = sorted({x for v in INNER.values() for x in v[:2]})
    ref = references(hist, cu, sorted(set(RATIO) | set(cols_in)), m0, weeks=weeks)
    have_a = ref.groupby("store_id")["sales__a"].apply(lambda x: x.notna().any())
    info["参照なしの店"] = [int(x) for x in have_a[~have_a].index]
    have_b = ref.groupby("store_id")["sales__b"].apply(lambda x: x.notna().any())
    info["1年前の参照なしの店"] = [int(x) for x in have_b[~have_b].index]
    flags += _ratio_flags(cu, ref, RATIO, T, ref_mode, "Q06")
    # Q07 中の関係：比どうしの参照は、参照 a・b の分子 ÷ 分母（同じ日の同じ参照から作る）
    it = inner_T or {k: v[2] for k, v in INNER.items()}
    for name, (n, dn, _) in INNER.items():
        cc = cu[KEY].copy(); cc[name] = cu[n] / cu[dn].replace(0, np.nan)
        rr = ref[KEY].copy()
        for tag in "abc":
            rr[name + "__" + tag] = ref[n + "__" + tag] / ref[dn + "__" + tag]
        flags += _ratio_flags(cc, rr, [name], {name: it[name]}, ref_mode, "Q07", label=name)
    for _, r in cu[cu.member_receipts > cu.receipts].iterrows():
        flags.append(dict(check="Q07", store_id=int(r.store_id), biz_date=r.biz_date, metric="会員の客数＞客数", value=float(r.member_receipts), ref=float(r.receipts), ratio=float(r.member_receipts / max(r.receipts, 1))))
    # Q08 部門の合計
    cat = cat.copy(); cat["biz_date"] = pd.to_datetime(cat.biz_date)
    cs = cat.groupby(KEY, as_index=False).sales.sum().rename(columns={"sales": "dept_sales"})
    j = cu[KEY + ["sales"]].merge(cs, on=KEY, how="outer", indicator=True)
    for _, r in j.iterrows():
        if r._merge != "both":
            flags.append(dict(check="Q08", store_id=int(r.store_id), biz_date=r.biz_date, metric="部門の行なし" if r._merge == "left_only" else "店の行なし",
                              value=float(r.sales if r._merge == "left_only" else r.dept_sales), ref=np.nan, ratio=np.nan))
        elif pd.notna(r.sales) and r.sales > 0 and abs(r.dept_sales - r.sales) > 0.005 * r.sales:
            flags.append(dict(check="Q08", store_id=int(r.store_id), biz_date=r.biz_date, metric="部門の合計÷店の売上", value=float(r.dept_sales), ref=float(r.sales), ratio=float(r.dept_sales / r.sales)))
    f = pd.DataFrame(flags, columns=["check", "store_id", "biz_date", "metric", "value", "ref", "ratio"])
    f["チェック"] = f.check.map(lambda c: CHECKS[c][0]); f["重さ"] = f.check.map(lambda c: CHECKS[c][1])
    f["次にやること"] = f.check.map(lambda c: CHECKS[c][2])
    # Q06・Q07 で5倍以上・5分の1以下は「桁・単位の疑い」として A に上げる（汚れのない480か月で、この大きさのずれは一度もなかった）
    big = f.check.isin(["Q06", "Q07"]) & ((f.ratio >= BIG) | (f.ratio <= 1 / BIG))
    f.loc[big, "重さ"] = "A"; f.loc[big, "チェック"] = f.loc[big, "チェック"] + "（桁・単位の疑い）"
    f.loc[big, "次にやること"] = "桁・単位の誤りを疑い、送り元に確かめる。確かめるまで、その店×日の数字を月の数字から外す"
    if mode == "速報":   # 速報では行の欠けは「未着」として保留（確定でもう一度チェック）
        k = (f.check == "Q02") & (f.metric == "行")
        f.loc[k, "重さ"] = "保留"; f.loc[k, "チェック"] = "行の欠け（未着）"
        f.loc[k, "次にやること"] = "未着として保留し、確定でもう一度チェックする。確定でも欠けていれば再送を頼む"
    return f.sort_values(["重さ", "check", "store_id", "biz_date"]).reset_index(drop=True), info


def load_mart(d):
    d = pathlib.Path(d)
    fsd = pd.read_csv(d / "fact_store_day.csv.gz", parse_dates=["biz_date"])
    cat = pd.read_csv(d / "fact_store_day_category.csv.gz", parse_dates=["biz_date"])
    st = pd.read_csv(d / "dim_store.csv", parse_dates=["open_date", "close_date"], encoding="utf-8-sig")
    return fsd, cat, st


def split_month(fsd, cat, month):
    p = pd.Period(month, "M")
    inm = (fsd.biz_date >= p.start_time) & (fsd.biz_date <= p.end_time)
    inc = (cat.biz_date >= p.start_time) & (cat.biz_date <= p.end_time)
    return fsd[inm], cat[inc], fsd[fsd.biz_date < p.start_time], cat[cat.biz_date < p.start_time]


def summary(flags, info, month, n_rows, mode="確定"):
    by = flags.groupby(["check", "重さ"]).size().rename("件数").reset_index()
    stores = flags.groupby("重さ").store_id.nunique().to_dict()
    nA = int((flags["重さ"] == "A").sum()); nB = int((flags["重さ"] == "B").sum()); nP = int((flags["重さ"] == "保留").sum())
    verdict = "要確認（A あり：直すまで該当の店×日を数字から外す）" if nA else ("要確認（B のみ：確かめてから出す）" if nB else ("保留あり（確定で再チェック）" if nP else "合格"))
    return dict(month=month, mode=mode, rows=int(n_rows), verdict=verdict, A=nA, B=nB, 保留=nP, stores=stores,
                by_check={f"{r.check}_{r['重さ']}": int(r["件数"]) for _, r in by.iterrows()}, info=info)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True); ap.add_argument("--mart", default="data/in"); ap.add_argument("--out", default="reports")
    ap.add_argument("--T", type=float, default=None, help="Q06 の線をすべての列で同じ値にするとき（既定は DEFAULT_T）"); ap.add_argument("--mode", default="確定")
    a = ap.parse_args()
    fsd, cat, st = load_mart(a.mart)
    cur, cc, hist, hc = split_month(fsd, cat, a.month)
    flags, info = run_checks(cur, cc, hist, hc, st, a.month, T=a.T, mode=a.mode)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    flags.to_csv(out / f"dq_{a.month}_{a.mode}_flags.csv", index=False, encoding="utf-8-sig")
    s = summary(flags, info, a.month, len(cur), a.mode)
    (out / f"dq_{a.month}_{a.mode}_summary.json").write_text(json.dumps(s, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(s, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
