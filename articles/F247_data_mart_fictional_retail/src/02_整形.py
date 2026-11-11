"""02 整形（合成）：現場から届く“汚れた”ファイルを、F246 の正しいデータ（data/truth/）から作る。

架空の会社「サンプルマート（架空）」の分析担当が、POS・勤怠・廃棄登録・会計から受け取るファイルを想定した合成データ。
実在の会社のデータではない。汚れの種類と量は作成者が決めた設定（下の RATES と ISSUES）。

届くファイル（data/raw_synth/）
- pos_store_day.csv.gz   : POS の店×日（店コード, 営業日, レシート枚数, 会員レシート枚数, 点数, 売上金額, 送信日時）
- pos_dept_day.csv.gz    : POS の店×日×部門（店コード, 営業日, 部門コード, 売上金額, 粗利金額, 送信日時）
- hr_attendance.csv.gz   : 勤怠の店×日（勤怠店番, 勤務日, 人時, 人件費）
- waste_register.csv.gz  : 廃棄登録の店×日×部門（店コード, 登録日, 部門コード, 廃棄金額）
- acct_store_month.csv   : 会計の店×月（店番, 年月, 売上高, その他経費）
- map_store_pos.csv      : 情報システム部から受け取った POS 店コードの対応表（店コード, 有効開始, 有効終了, 店番）
- map_store_hr.csv       : 勤怠の店番の対応表
- map_dept.csv           : 部門コードの対応表（部門コード, 有効開始, 有効終了, 部門番号, 部門名）

入れた汚れ（ISSUES。すべて合成。どこに入れたかは results/issue_log.csv に残す）
- dup         : POS の再送で、店×日の 0.6% が2回届く（部門のファイルも同じ日が2回）
- late        : 店×日の 2% が 3〜20日遅れて届く（ふだんは翌朝）
- store_code  : 2024-04-01 に POS の店コードが振り直される。新しいコードも「1001〜1024」で、同じ番号が別の店を指す（対応表に有効期間つきである）
- s16_missing : 2025-04 に開店した16店の新コードが、対応表から漏れている
- test_store  : POS のトレーニング用の店コード 9999 の売上が、日の 1% に混ざる
- dept_split  : 2025-04-01 に部門コードが変わる（日用品 7→8、惣菜 4 を 4 惣菜・9 弁当寿司 に 6:4 で分割）
- hr_null     : 勤怠の店×日の 1.5% で人時・人件費が空（締め忘れ）
- waste_unit  : 19店が 2025-06〜08 の廃棄金額を「千円」で入力（0.1千円単位）
"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
TRUTH = ROOT / "data" / "truth"
OUT = ROOT / "data" / "raw_synth"

ALL_ISSUES = ["dup", "late", "store_code", "s16_missing", "test_store", "dept_split", "hr_null", "waste_unit"]
RATES = {"dup": 0.006, "late": 0.02, "test_store": 0.01, "hr_null": 0.015}
CODE_CHANGE = pd.Timestamp("2024-04-01")
DEPT_CHANGE = pd.Timestamp("2025-04-01")
WASTE_UNIT = (19, pd.Timestamp("2025-06-01"), pd.Timestamp("2025-08-31"))
FAR = pd.Timestamp("2099-12-31")


def load_truth():
    t = {}
    t["dim_store"] = pd.read_csv(TRUTH / "dim_store.csv", parse_dates=["open_date", "close_date"])
    t["dim_category"] = pd.read_csv(TRUTH / "dim_category.csv")
    t["dim_date"] = pd.read_csv(TRUTH / "dim_date.csv", parse_dates=["date"])
    t["fsd"] = pd.read_csv(TRUTH / "fact_store_day.csv.gz", parse_dates=["date"])
    t["fsdc"] = pd.read_csv(TRUTH / "fact_store_day_category.csv.gz", parse_dates=["date"])
    return t


# 2024-04 の振り直し：大きさ（L→M→S）の順、同じ大きさの中は店番の順に 1001 から振る（合成の設定）
_SIZE = {"L": 0, "M": 1, "S": 2}


def new_numbers(dim_store):
    o = dim_store.assign(k=dim_store["size"].map(_SIZE)).sort_values(["k", "store_id"])
    return dict(zip(o.store_id, range(1, len(o) + 1)))


def pos_code(store_id, date, newnum, store_code_issue=True):
    if store_code_issue and date >= CODE_CHANGE:
        return f"{1000 + newnum[store_id]}"
    return f"{1000 + store_id}"


def make_raw(t, seed=0, issues=None, rates=None):
    """t: load_truth() の結果。issues: 入れる汚れの集合（None ならすべて）。戻り値：dict（テーブル名→DataFrame）と汚れの記録"""
    issues = set(ALL_ISSUES if issues is None else issues)
    r = dict(RATES); r.update(rates or {})
    rng = np.random.default_rng(1000 + seed)
    fsd, fsdc = t["fsd"].copy(), t["fsdc"].copy()
    log = []

    # ---- 送信日時（ふだんは翌朝 6時台。late のときは 3〜20日遅れ）----
    n = len(fsd)
    sent = fsd.date + pd.Timedelta(days=1) + pd.to_timedelta(rng.integers(6 * 60, 7 * 60, n), unit="m")
    if "late" in issues:
        late = rng.random(n) < r["late"]
        sent = sent.where(~late, sent + pd.to_timedelta(rng.integers(3, 21, n), unit="D"))
        log += [("late", d, s) for d, s in zip(fsd.date[late], fsd.store_id[late])]
    fsd["sent_at"] = sent.values
    sc = "store_code" in issues
    newnum = new_numbers(t["dim_store"])
    fsd["pos_code"] = [pos_code(s, d, newnum, sc) for s, d in zip(fsd.store_id, fsd.date)]

    ps = pd.DataFrame({"店コード": fsd.pos_code, "営業日": fsd.date, "レシート枚数": fsd.receipts,
                       "会員レシート枚数": fsd.member_receipts, "点数": fsd["items"].round().astype(int),
                       "売上金額": fsd.sales.round().astype(int), "送信日時": fsd.sent_at})

    # 部門：sent_at と pos_code は店×日に合わせる
    fsdc = fsdc.merge(fsd[["date", "store_id", "sent_at", "pos_code"]], on=["date", "store_id"])
    dept = fsdc.category_id.copy()
    rows_split = []
    if "dept_split" in issues:
        after = fsdc.date >= DEPT_CHANGE
        dept = dept.where(~(after & (fsdc.category_id == 7)), 8)
        sp = fsdc[after & (fsdc.category_id == 4)].copy()
        s4 = (sp.sales * 0.6).round(); g4 = (sp.gross_profit_before_waste * 0.6).round(); w4 = (sp.waste * 0.6).round()
        b = sp.copy(); b["sales"] = sp.sales - s4; b["gross_profit_before_waste"] = sp.gross_profit_before_waste - g4; b["waste"] = sp.waste - w4
        b["dept"] = 9
        fsdc.loc[sp.index, ["sales", "gross_profit_before_waste", "waste"]] = np.c_[s4, g4, w4]
        rows_split = [b]
    fsdc["dept"] = dept
    if rows_split:
        fsdc = pd.concat([fsdc] + rows_split, ignore_index=True)
    pdp = pd.DataFrame({"店コード": fsdc.pos_code, "営業日": fsdc.date, "部門コード": fsdc.dept.astype(int),
                        "売上金額": fsdc.sales.round().astype(int), "粗利金額": fsdc.gross_profit_before_waste.round().astype(int),
                        "送信日時": fsdc.sent_at})

    # ---- 再送（重複）----
    if "dup" in issues:
        k = rng.random(n) < r["dup"]
        keys = fsd.loc[k, ["date", "pos_code", "sent_at", "store_id"]]
        log += [("dup", d, s) for d, s in zip(keys.date, keys.store_id)]
        extra = pd.to_timedelta(rng.integers(1, 4, len(keys)), unit="D")
        resend = dict(zip(zip(keys.pos_code, keys.date), keys.sent_at + extra))
        d1 = ps[[(c, d) in resend for c, d in zip(ps["店コード"], ps["営業日"])]].copy()
        d1["送信日時"] = [resend[(c, d)] for c, d in zip(d1["店コード"], d1["営業日"])]
        d2 = pdp[[(c, d) in resend for c, d in zip(pdp["店コード"], pdp["営業日"])]].copy()
        d2["送信日時"] = [resend[(c, d)] for c, d in zip(d2["店コード"], d2["営業日"])]
        ps = pd.concat([ps, d1], ignore_index=True); pdp = pd.concat([pdp, d2], ignore_index=True)

    # ---- トレーニング用の店コード 9999 ----
    if "test_store" in issues:
        days = t["dim_date"].date
        pick = days[rng.random(len(days)) < r["test_store"]]
        for d in pick:
            sales = int(rng.integers(5, 51)) * 10000
            ps.loc[len(ps)] = ["9999", d, int(rng.integers(3, 30)), 0, int(rng.integers(10, 80)), sales, d + pd.Timedelta(hours=30)]
            dpt = int(rng.integers(1, 7))
            pdp.loc[len(pdp)] = ["9999", d, dpt, sales, int(sales * 0.25), d + pd.Timedelta(hours=30)]
            log.append(("test_store", d, 9999))

    # ---- 勤怠 ----
    hr = pd.DataFrame({"勤怠店番": [f"T-{s:02d}" for s in fsd.store_id], "勤務日": fsd.date,
                       "人時": fsd.labor_hours.round(1), "人件費": fsd.labor_cost.round().astype("Int64")})
    if "hr_null" in issues:
        m = rng.random(n) < r["hr_null"]
        hr.loc[m, "人時"] = np.nan; hr.loc[m, "人件費"] = pd.NA
        log += [("hr_null", d, s) for d, s in zip(fsd.date[m], fsd.store_id[m])]

    # ---- 廃棄登録（廃棄のある部門だけ）----
    wr = fsdc[fsdc.waste > 0]
    wv = wr.waste.astype(float).values.copy()
    if "waste_unit" in issues:
        s, a, b = WASTE_UNIT
        m = ((wr.store_id == s) & (wr.date >= a) & (wr.date <= b)).values
        wv[m] = np.round(wv[m] / 1000, 1)
        log += [("waste_unit", d, s_) for d, s_ in zip(wr.date[m], wr.store_id[m])]
    waste = pd.DataFrame({"店コード": wr.pos_code.values, "登録日": wr.date.values, "部門コード": wr.dept.astype(int).values, "廃棄金額": wv})

    # ---- 会計（店番＝store_id。POS とは別の仕組みで締める）----
    fsd["ym"] = fsd.date.dt.strftime("%Y-%m")
    acct = fsd.groupby(["store_id", "ym"], as_index=False).agg(売上高=("sales", "sum"), その他経費=("other_cost", "sum"))
    acct = acct.rename(columns={"store_id": "店番", "ym": "年月"}).round(0)

    # ---- 対応表（情報システム部から受け取ったもの）----
    ms = []
    for s in t["dim_store"].store_id:
        if sc:
            ms.append([f"{1000 + s}", pd.Timestamp("2000-01-01"), CODE_CHANGE - pd.Timedelta(days=1), s])
            if not ("s16_missing" in issues and s == 16):
                ms.append([f"{1000 + newnum[s]}", CODE_CHANGE, FAR, s])
        else:
            if not ("s16_missing" in issues and s == 16):
                ms.append([f"{1000 + s}", pd.Timestamp("2000-01-01"), FAR, s])
    map_pos = pd.DataFrame(ms, columns=["店コード", "有効開始", "有効終了", "店番"])
    map_hr = pd.DataFrame({"勤怠店番": [f"T-{s:02d}" for s in t["dim_store"].store_id], "店番": t["dim_store"].store_id})
    cats = t["dim_category"]
    md = []
    end_old = (DEPT_CHANGE - pd.Timedelta(days=1)) if "dept_split" in issues else FAR
    for c, nm in zip(cats.category_id, cats.category):
        md.append([c, pd.Timestamp("2000-01-01"), end_old, c, nm])
    if "dept_split" in issues:
        for c, nm in zip(cats.category_id, cats.category):
            if c in (1, 2, 3, 4, 5, 6):
                md.append([c, DEPT_CHANGE, FAR, c, nm])
        md.append([8, DEPT_CHANGE, FAR, 7, "日用品"])
        md.append([9, DEPT_CHANGE, FAR, 4, "弁当・寿司（惣菜に含める）"])
    map_dept = pd.DataFrame(md, columns=["部門コード", "有効開始", "有効終了", "部門番号", "部門名"])

    raw = {"pos_store_day": ps.sort_values(["営業日", "店コード", "送信日時"]).reset_index(drop=True),
           "pos_dept_day": pdp.sort_values(["営業日", "店コード", "部門コード", "送信日時"]).reset_index(drop=True),
           "hr_attendance": hr, "waste_register": waste, "acct_store_month": acct,
           "map_store_pos": map_pos, "map_store_hr": map_hr, "map_dept": map_dept}
    lg = pd.DataFrame(log, columns=["issue", "date", "store_id"])
    return raw, lg


def write_raw(raw, lg, out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    for k, v in raw.items():
        v = v.copy()
        for c in ("営業日", "勤務日", "登録日", "有効開始", "有効終了"):
            if c in v.columns:
                v[c] = pd.to_datetime(v[c]).dt.strftime("%Y-%m-%d")
        if k.startswith(("pos_", "hr_", "waste_")):
            v.to_csv(out / f"{k}.csv.gz", index=False, encoding="utf-8", date_format="%Y-%m-%d %H:%M:%S" if "pos" in k else "%Y-%m-%d")
        else:
            v.to_csv(out / f"{k}.csv", index=False, encoding="utf-8", date_format="%Y-%m-%d")
    lg.to_csv(ROOT / "results" / "issue_log.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    t = load_truth()
    raw, lg = make_raw(t, seed=0)
    write_raw(raw, lg)
    for k, v in raw.items():
        print(k, v.shape)
    print(lg.issue.value_counts())
