"""F275 03: 3つの書き方 × 8つの変更依頼で、直す場所の数・直し忘れの変異・テストで見つかる割合を数える。
使い方: python3 zz_f275_03_分析.py   （先に 01 を seed 2751〜2755 で実行しておく）
出力: results/*.csv, results/main.json, sql/（基準の SQL と変更依頼ごとの差分）
"""
import os, sys, json, difflib, itertools
import numpy as np, pandas as pd, duckdb, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zz_f275_sqlgen as G
import zz_f275_spec as SP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results"); os.makedirs(RES, exist_ok=True)
SEEDS = [2751, 2752, 2753, 2754, 2755]
KEYS = {"R1": ["ym"], "R2": ["ym", "store_id"], "R3": ["ym", "grp"], "R4": ["ym"], "R5": ["ym"],
        "R6": ["ym", "store_id", "grp"], "R7": ["ym"], "R8": ["date_key"]}
RATE_COLS = {"yoy", "comp_yoy", "ticket"}
VERS = [None] + list(G.CRS)
STY = ["S1", "S2", "S3"]
TABLES = ["calendar", "store", "item", "dept", "receipt", "sales_line", "returns_line"]


class Eng:
    def __init__(self, kind, t):
        self.kind = kind
        if kind == "duckdb":
            self.c = duckdb.connect()
            for k in TABLES:
                df = t[k]
                self.c.register("tmp_df", df); self.c.execute(f"CREATE TABLE {k} AS SELECT * FROM tmp_df"); self.c.unregister("tmp_df")
        else:
            self.c = sqlite3.connect(":memory:")
            for k in TABLES:
                df = t[k].copy()
                if k == "receipt":
                    df["member_id"] = df["member_id"].astype(object).where(df["member_id"].notna(), None)
                df.to_sql(k, self.c, index=False)
            for ix in ["sales_line(receipt_id, line_no)", "returns_line(receipt_id, line_no)", "calendar(date_key)", "store(store_id)", "item(item_id)", "receipt(receipt_id)"]:
                self.c.execute(f"CREATE INDEX ix_{ix.split('(')[0]} ON {ix}")

    def q(self, sql):
        if self.kind == "duckdb":
            return self.c.execute(sql).df()
        cur = self.c.execute(sql)
        cols = [d[0] for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)

    def ex(self, sql):
        self.c.execute(sql)


def norm(df, r):
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    for k in KEYS[r]:
        if k != "grp":
            df[k] = df[k].astype("int64")
    for c in df.columns:
        if c not in KEYS[r]:
            df[c] = df[c].astype(float)
    return df.sort_values(KEYS[r]).reset_index(drop=True)


def run_files(eng, style, fs, only=None):
    out = {}
    if style == "S3":
        for v in reversed(G.VIEW_ORDER):
            eng.ex(f"DROP VIEW IF EXISTS {v}")
        for v in G.VIEW_ORDER:
            eng.ex(fs[f"V_{v}.sql"])
    for r in (only or G.REPORTS):
        out[r] = norm(eng.q(fs[f"{r}.sql"]), r)
    return out


def same(a, b, r, tol):
    if len(a) != len(b):
        return False
    for k in KEYS[r]:
        if not (a[k].values == b[k].values).all():
            return False
    for c in b.columns:
        if c in KEYS[r]:
            continue
        x, y = a[c].values, b[c].values
        if not np.allclose(x, y, rtol=tol, atol=1e-6, equal_nan=True):
            return False
    return True


def close(x, y, tol):
    return abs(x - y) <= tol * max(abs(y), 1.0) + 1e-6


def t1(o, tol, reps=None):
    """レポート間の照合（売上）。食い違いがあれば True（=見つけた）"""
    reps = reps or G.REPORTS
    r1 = o["R1"].set_index("ym").sales
    sums = []
    if "R2" in reps: sums.append(o["R2"].groupby("ym").sales.sum())
    if "R3" in reps: sums.append(o["R3"].groupby("ym").sales.sum())
    if "R6" in reps: sums.append(o["R6"].groupby("ym").sales.sum())
    if "R5" in reps: sums.append(o["R5"].set_index("ym").sales)
    if "R7" in reps: sums.append(o["R7"].set_index("ym").sales)
    for s in sums:
        if set(s.index) != set(r1.index):
            return True
        if any(not close(s[k], r1[k], tol) for k in r1.index):
            return True
    if "R8" in reps:
        last = r1.index.max()
        if not close(o["R8"].sales.sum(), r1[last], tol):
            return True
    return False


def t2(o, tol, reps=None):
    """中の整合：既存店の売上 ≦ 全店、客単価×客数＝売上"""
    reps = reps or G.REPORTS
    r1 = o["R1"].set_index("ym").sales
    if "R4" in reps:
        for _, x in o["R4"].iterrows():
            if x.ym not in r1.index or x.comp_sales > r1[x.ym] * (1 + tol) + 1e-6:
                return True
    for r in ["R5", "R7"]:
        if r in reps:
            d = o[r]
            if any(not close(a * b, c, max(tol, 1e-9)) for a, b, c in zip(d.ticket, d.customers, d.sales)):
                return True
    return False


def t3(of, exp, tol):
    return not same(of["R1"], exp["R1"], "R1", tol)


def t4(of, exp, tol, reps=None):
    return any(not same(of[r], exp[r], r, tol) for r in (reps or G.REPORTS))


def maxdiff(o, ref, reps=None):
    """影響を受けたレポートの最大のずれ（金額・人数・客単価の列は「その列の平均の大きさ」に対する％、前年比の列は差のポイント）"""
    rel, pt, wrong = 0.0, 0.0, []
    for r in (reps or G.REPORTS):
        a, b = o[r], ref[r]
        if same(a, b, r, 1e-9):
            continue
        wrong.append(r)
        m = b.merge(a, on=KEYS[r], how="outer", suffixes=("_ref", "_x"))
        for c in b.columns:
            if c in KEYS[r]:
                continue
            x, y = m[c + "_x"].fillna(0).values, m[c + "_ref"].fillna(0).values
            if c in RATE_COLS and c != "ticket":
                pt = max(pt, float(np.nanmax(np.abs(x - y))) * 100)
            else:
                # ずれ ÷ その列の正しい値の平均の大きさ（キーが食い違う行も 0 との差として数える）
                scale = max(float(np.nanmean(np.abs(b[c].values))), 1e-9)
                rel = max(rel, float(np.nanmax(np.abs(x - y))) / scale)
    return rel * 100, pt, wrong


def edit_stats(style):
    rows = []
    base = G.files(style, G.BASE)
    for cr in G.CRS:
        new = G.files(style, G.apply(cr))
        touched = [f for f in base if base[f] != new[f]]
        lines = 0
        for f in touched:
            a, b = base[f].splitlines(), new[f].splitlines()
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
                if tag != "equal":
                    lines += max(i2 - i1, j2 - j1)
        rows.append(dict(style=style, cr=cr, files=len(touched), lines=lines, touched=" ".join(touched),
                         total_lines=sum(len(v.splitlines()) for v in new.values())))
    return rows


def write_sql():
    """基準の SQL と、変更依頼ごとの差分をリポジトリ用に書き出す"""
    for s in STY:
        d = os.path.join(ROOT, "sql", s); os.makedirs(d, exist_ok=True)
        base = G.files(s, G.BASE)
        for f, v in base.items():
            open(os.path.join(d, f), "w").write(v)
        with open(os.path.join(ROOT, "sql", f"{s}_changes.diff"), "w") as fh:
            for cr in G.CRS:
                new = G.files(s, G.apply(cr))
                fh.write(f"######## {cr} {G.CRS[cr][0]}\n")
                for f in base:
                    if base[f] != new[f]:
                        fh.writelines(difflib.unified_diff(base[f].splitlines(True), new[f].splitlines(True), f"{s}/{f}", f"{s}/{f} ({cr})"))


def tsql_check():
    import sqlglot
    ok = bad = 0; errs = []
    for s in STY:
        for v in VERS:
            for f, sql in G.files(s, G.apply(v)).items():
                try:
                    sqlglot.parse(sql, read="tsql"); ok += 1
                except Exception as e:
                    bad += 1; errs.append(f"{s} {v} {f}: {str(e)[:80]}")
    return dict(parsed=ok, failed=bad, errors=errs[:5], version=sqlglot.__version__)


def all_outputs(kind, tmain, tfix):
    """3様式 × 9版 × 8本 を本番データと答え合わせ用データで実行"""
    em, ef = Eng(kind, tmain), Eng(kind, tfix)
    O = {}
    for s in STY:
        for v in VERS:
            fs = G.files(s, G.apply(v))
            O[(s, v, "main")] = run_files(em, s, fs)
            O[(s, v, "fix")] = run_files(ef, s, fs)
    return O, em, ef


def mutants(style):
    """直し忘れの変異：(cr, 種類, 古いままのファイル)"""
    out = []
    for cr in G.CRS:
        base, new = G.files(style, G.BASE), G.files(style, G.apply(cr))
        touched = [f for f in base if base[f] != new[f]]
        rep_touched = [f[:-4] for f in touched if f.startswith("R")]
        if style != "S3":
            for r in rep_touched:
                out.append((cr, "1つだけ直し忘れ", [r]))
        out.append((cr, "全部直し忘れ", "ALL"))
    return out


def mutant_outputs(O, style, cr, missed, ds):
    new, base = O[(style, cr, ds)], O[(style, None, ds)]
    if missed == "ALL":
        return dict(base)
    o = dict(new)
    for r in missed:
        o[r] = base[r]
    return o


def evaluate(O, EXP, tol=1e-9, reps=None, fixkey="fix"):
    rows = []
    for s in STY:
        for cr, kind, missed in mutants(s):
            if reps and missed != "ALL" and not set(missed) <= set(reps):
                continue
            om = mutant_outputs(O, s, cr, missed, "main")
            of = mutant_outputs(O, s, cr, missed, fixkey)
            om = {r: om[r] for r in (reps or G.REPORTS)}; of = {r: of[r] for r in (reps or G.REPORTS)}
            a, b = t1(om, tol, reps), t2(om, tol, reps)
            rel, pt, wrong = maxdiff(om, O[(s, cr, "main")], reps)
            rows.append(dict(style=s, cr=cr, kind=kind, missed="ALL" if missed == "ALL" else ",".join(missed),
                             T1=a, T2=b, T12=a or b, T3=t3(of, EXP[(cr, fixkey)], tol), T4=t4(of, EXP[(cr, fixkey)], tol, reps),
                             max_rel_pct=rel, max_pt=pt, n_wrong=len(wrong), wrong=" ".join(wrong)))
    return pd.DataFrame(rows)


def random_miss(O, EXP, p=0.2, n=200, seed=275):
    rng = np.random.default_rng(seed)
    rows = []
    for s in ["S1", "S2"]:
        for cr in G.CRS:
            base, new = G.files(s, G.BASE), G.files(s, G.apply(cr))
            rep_touched = [f[:-4] for f in base if base[f] != new[f] and f.startswith("R")]
            for i in range(n):
                miss = [r for r in rep_touched if rng.random() < p]
                if not miss:
                    rows.append(dict(style=s, cr=cr, draw=i, k=0)); continue
                mm = "ALL" if len(miss) == len(rep_touched) else miss
                om = mutant_outputs(O, s, cr, mm, "main"); of = mutant_outputs(O, s, cr, mm, "fix")
                rows.append(dict(style=s, cr=cr, draw=i, k=len(miss), T12=t1(om, 1e-9) or t2(om, 1e-9), T4=t4(of, EXP[(cr, "fix")], 1e-9)))
    return pd.DataFrame(rows)


BUGS = {
    "B1": ("キャンセルの除外漏れ", [("l.status <> 'cancel'", "1 = 1")]),
    "B2": ("返品の結合キー不足", [(" AND l.line_no = r.line_no", ""), (" AND o.line_no = r.line_no", "")]),
    "B3": ("既存店の境目のずれ（<= を <）", [("oc.cal_mi <= a.mi - 13", "oc.cal_mi < a.mi - 13"), ("om.mi <= m.mi - 13", "om.mi < m.mi - 13")]),
    "B4": ("客数で明細のないレシートも数える", [("WHERE EXISTS (", "WHERE 1 = 1 OR EXISTS (")]),
}


def inject(text, subs):
    n = 0
    for a, b in subs:
        if a in text:
            text = text.replace(a, b); n += 1
    return text, n > 0


def reask(eng_m, eng_f, O, EXPB, tol=1e-9):
    """もう一度問う：誤りを共通の定義に入れたら、照合で見つかるか（S1・S2 は1ファイル、S3 は共通ビュー）"""
    rows = []
    for s in STY:
        base = G.files(s, G.BASE)
        for bug, (name, subs) in BUGS.items():
            if s == "S3":
                fs = dict(base); hit = []
                for f in base:
                    if f.startswith("V_"):
                        fs[f], ok = inject(base[f], subs)
                        if ok: hit.append(f)
                assert hit, (s, bug)
                om = run_files(eng_m, s, fs); of = run_files(eng_f, s, fs)
                targets = [(",".join(hit), om, of)]
            else:
                targets = []
                for f in base:
                    t, ok = inject(base[f], subs)
                    if not ok: continue
                    r = f[:-4]
                    om = dict(O[(s, None, "main")]); of = dict(O[(s, None, "fix")])
                    om[r] = norm(eng_m.q(t), r); of[r] = norm(eng_f.q(t), r)
                    targets.append((f, om, of))
            for where, om, of in targets:
                rel, pt, wrong = maxdiff(om, O[(s, None, "main")])
                if not wrong:  # 結果が変わらない場所（例：誤りが効かない）は数えない
                    continue
                rows.append(dict(style=s, bug=bug, bug_name=name, where=where, T12=t1(om, tol) or t2(om, tol),
                                 T4=t4(of, EXPB, tol), n_wrong=len(wrong), wrong=" ".join(wrong), max_rel_pct=rel, max_pt=pt))
    return pd.DataFrame(rows)


def main():
    write_sql()
    res = {}
    # 1. 直す場所の数
    ed = pd.DataFrame(sum([edit_stats(s) for s in STY], []))
    ed.to_csv(os.path.join(RES, "A_edits.csv"), index=False)
    med = ed.groupby("style")[["files", "lines"]].median()
    res["edits_median"] = med.to_dict()
    res["H1_ratio_S1_S3_files"] = float(med.loc["S1", "files"] / med.loc["S3", "files"])
    res["H2_ratio_S2_S1_files"] = float(med.loc["S2", "files"] / med.loc["S1", "files"])
    res["lines_total_base"] = {s: int(sum(len(v.splitlines()) for v in G.files(s, G.BASE).values())) for s in STY}
    res["tsql"] = tsql_check()
    print("edits\n", ed.pivot(index="cr", columns="style", values=["files", "lines"]))
    # 2. 正しい版がすべて pandas と一致するか（本番・答え合わせ、DuckDB と SQLite）
    per_seed = []
    for seed in SEEDS:
        tm = SP.load(os.path.join(ROOT, "data", f"main_{seed}")); tf = SP.load(os.path.join(ROOT, "data", f"fixture_{seed}"))
        tp = SP.load(os.path.join(ROOT, "data", f"fixture_plain_{seed}"))
        EXP = {}
        for v in VERS:
            EXP[(v, "fix")] = SP.reports(tf, G.apply(v)); EXP[(v, "plain")] = SP.reports(tp, G.apply(v))
        kinds = ["duckdb", "sqlite"] if seed == SEEDS[0] else ["duckdb"]
        REFM = {v: SP.reports(tm, G.apply(v)) for v in (VERS if seed == SEEDS[0] else [None])}
        for kind in kinds:
            O, em, ef = all_outputs(kind, tm, tf)
            # 答え合わせ（確かめ）：正しい版が pandas と一致
            bad = 0; n = 0
            for s in STY:
                for v in VERS:
                    ref_m = REFM.get(v)
                    for r in G.REPORTS:
                        n += 1
                        if not same(O[(s, v, "fix")][r], EXP[(v, "fix")][r], r, 1e-9): bad += 1
                        if ref_m is not None:
                            n += 1
                            if not same(O[(s, v, "main")][r], ref_m[r], r, 1e-9): bad += 1
            # 答え合わせ用データ（境目なし）でも実行
            ep = Eng(kind, tp)
            for s in STY:
                for v in VERS:
                    O[(s, v, "plain")] = run_files(ep, s, G.files(s, G.apply(v)))
            print(seed, kind, "spec mismatches", bad, "/", n)
            res.setdefault("spec_check", {})[f"{seed}_{kind}"] = dict(mismatch=bad, compared=n)
            ev = evaluate(O, EXP)
            ev["seed"], ev["engine"], ev["tol"], ev["reps"], ev["fixture"] = seed, kind, "exact", "8", "boundary"
            per_seed.append(ev)
            if seed == SEEDS[0] and kind == "duckdb":
                ev5 = evaluate(O, EXP, tol=0.005); ev5[["seed", "engine", "tol", "reps", "fixture"]] = [seed, kind, "0.5%", "8", "boundary"]
                evr = evaluate(O, EXP, reps=["R1", "R2", "R3", "R4", "R5"]); evr[["seed", "engine", "tol", "reps", "fixture"]] = [seed, kind, "exact", "5", "boundary"]
                evp = evaluate(O, EXP, fixkey="plain"); evp[["seed", "engine", "tol", "reps", "fixture"]] = [seed, kind, "exact", "8", "plain"]
                per_seed += [ev5, evr, evp]
                rm = random_miss(O, EXP); rm.to_csv(os.path.join(RES, "D_random_miss.csv"), index=False)
                EXPB = EXP[(None, "fix")]
                rq = reask(em, ef, O, EXPB); rq.to_csv(os.path.join(RES, "E_reask_bugs.csv"), index=False)
                O0 = O
    ev_all = pd.concat(per_seed, ignore_index=True)
    ev_all.to_csv(os.path.join(RES, "B_mutants.csv"), index=False)
    main_ev = ev_all[(ev_all.seed == SEEDS[0]) & (ev_all.engine == "duckdb") & (ev_all.tol == "exact") & (ev_all.reps == "8") & (ev_all.fixture == "boundary")]
    summ = main_ev.groupby(["style", "kind"])[["T1", "T2", "T12", "T3", "T4"]].mean().round(4)
    cnt = main_ev.groupby(["style", "kind"]).size()
    summ["n"] = cnt
    summ.to_csv(os.path.join(RES, "C_detection_summary.csv"))
    print(summ)
    one = main_ev[(main_ev["style"] == "S1") & (main_ev.kind == "1つだけ直し忘れ")]
    res["H3_S1_one_missed_T12"] = float(one.T12.mean()); res["H3_n"] = int(len(one))
    res["H4_T4_all"] = float(main_ev.T4.mean()); res["H4_n"] = int(len(main_ev))
    res["detection"] = {f"{s}|{k}": {c: float(summ.loc[(s, k), c]) for c in ["T1", "T2", "T12", "T3", "T4"]} | {"n": int(summ.loc[(s, k), "n"])} for s, k in summ.index}
    # 頑健性のまとめ
    rob = ev_all.groupby(["seed", "engine", "tol", "reps", "fixture", "style", "kind"])[["T12", "T3", "T4"]].mean().reset_index()
    rob.to_csv(os.path.join(RES, "C_detection_robustness.csv"), index=False)
    res["robust_S1_one_T12"] = rob[(rob["style"] == "S1") & (rob.kind == "1つだけ直し忘れ")][["seed", "engine", "tol", "reps", "fixture", "T12", "T4"]].to_dict("records")
    res["robust_T4_min"] = float(rob[rob.fixture == "boundary"].T4.min())
    res["plain_fixture_T4"] = rob[rob.fixture == "plain"].groupby("style").T4.mean().to_dict()
    rm = pd.read_csv(os.path.join(RES, "D_random_miss.csv")); rmm = rm[rm.k > 0]
    res["random_miss"] = dict(n=int(len(rmm)), T12=rmm.groupby("style").T12.mean().to_dict(), T4=rmm.groupby("style").T4.mean().to_dict(),
                              share_no_miss=float((rm.k == 0).mean()))
    # ずれの大きさ（S1 の1つだけ直し忘れ）
    res["missed_size"] = main_ev[(main_ev.kind == "1つだけ直し忘れ") & (main_ev["style"] == "S1")].groupby("cr")[["max_rel_pct", "max_pt"]].max().round(3).to_dict()
    undet = main_ev[(main_ev["style"] == "S1") & (main_ev.kind == "1つだけ直し忘れ") & (~main_ev.T12)]
    res["S1_undetected_by_T12"] = undet[["cr", "missed", "max_rel_pct", "max_pt"]].round(3).to_dict("records")
    rq = pd.read_csv(os.path.join(RES, "E_reask_bugs.csv"))
    res["reask"] = rq.groupby("style").agg(n=("bug", "size"), T12=("T12", "mean"), T4=("T4", "mean"), n_wrong=("n_wrong", "mean")).round(4).to_dict("index")
    res["reask_by_bug"] = rq.groupby(["style", "bug"]).agg(n=("bug", "size"), T12=("T12", "mean"), T4=("T4", "mean"), n_wrong=("n_wrong", "mean"), rel=("max_rel_pct", "max"), pt=("max_pt", "max")).round(3).reset_index().to_dict("records")
    json.dump(res, open(os.path.join(RES, "main.json"), "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps({k: res[k] for k in ["H1_ratio_S1_S3_files", "H2_ratio_S2_S1_files", "H3_S1_one_missed_T12", "H4_T4_all", "random_miss", "reask", "plain_fixture_T4", "robust_T4_min", "tsql", "spec_check", "lines_total_base"]}, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
