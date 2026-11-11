"""決めごとのテスト：「既存店」の判定が、各回のコードで同じ答えになっているか。

    python tests/test_rules.py [work/repo]

既存店の判定は、F246・F247・F248・F250 の4か所にそれぞれ書かれている（docs/decisions.md の D1）。
各回のファイルから判定の関数だけを取り出し（コードは動かさず、関数の定義だけを読む）、同じ店・同じ月で比べる。

- 実際の24店（F246 の dim_store）：4か所と会社設定書の読み方（samplemart/rules.py）がすべて同じであること → 違えば失敗
- 境目の店（このテストのために置いた架空の4店）：月の途中で開店・閉店する店。
  いまのデータには無いが、来たときに答えが割れるかどうかを記録する。割れ方が docs/decisions.md に書いたものと
  変わったら失敗（＝誰かがコードを変えた合図）
"""
import ast, pathlib, sys
import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from samplemart.rules import is_existing  # noqa: E402

REPO = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "work" / "repo"
A = REPO / "articles"
MONTHS = list(pd.period_range("2022-04", "2026-03", freq="M").strftime("%Y-%m"))
EDGE = pd.DataFrame([  # 架空の境目の店（store_id 91〜94）
    (91, "2024-10-15", None), (92, "2024-10-01", None), (93, "2010-04-01", "2025-06-15"), (94, "2010-04-01", "2025-06-30")],
    columns=["store_id", "open_date", "close_date"])
# docs/decisions.md D1 に書いた「割れ方」：（店, 月）→ 暦の月の差で数える3か所だけ既存店になる
KNOWN_SPLIT = {(91, "2025-11")}


def grab(path, name, ns):
    """ファイルから関数 name の定義だけを取り出して ns の中で定義する（ファイルの他の行は流さない）"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), ns)
    return ns[name]


def stores():
    st = pd.read_csv(A / "F246_kpi_definitions_fictional_retail" / "data" / "dim_store.csv")[["store_id", "open_date", "close_date"]]
    st = pd.concat([st, EDGE], ignore_index=True)
    for c in ["open_date", "close_date"]:
        st[c] = pd.to_datetime(st[c])
    return st


def daily(st):
    """店×日（営業している日だけ、数字は1）。F247・F248 の関数に渡す形"""
    days = pd.date_range("2022-04-01", "2026-03-31")
    rows = []
    for _, s in st.iterrows():
        d = days[days >= s.open_date]
        if pd.notna(s.close_date):
            d = d[d <= s.close_date]
        rows.append(pd.DataFrame({"date": d, "store_id": s.store_id}))
    f = pd.concat(rows, ignore_index=True)
    for c in ["sales", "receipts", "member_receipts", "items", "gross_profit_before_waste", "waste", "gross_profit",
              "labor_hours", "labor_cost", "other_cost"]:
        f[c] = 1.0
    f["labor_imputed"] = 0
    return f


def run():
    st = stores(); fsd = daily(st)
    grid = pd.DataFrame([(s, m) for s in st.store_id for m in MONTHS], columns=["store_id", "ym"])
    res = grid.copy()
    o = st.set_index("store_id")
    res["設定書"] = [int(is_existing(o.open_date[s], o.close_date[s], m)) for s, m in zip(grid.store_id, grid.ym)]

    # F246：existing_mask(df, months)（グローバルの STORES を読む）
    ns = {"pd": pd, "np": np, "STORES": st}
    f = grab(A / "F246_kpi_definitions_fictional_retail" / "src" / "03_分析.py", "existing_mask", ns)
    res["F246"] = f(grid, 13).astype(int)

    # F247：store_month(fsd, acct, st, dd) の is_existing
    ns = {"pd": pd, "np": np}
    f = grab(A / "F247_data_mart_fictional_retail" / "src" / "03_整える.py", "store_month", ns)
    dd = pd.DataFrame({"date": pd.date_range("2022-04-01", "2026-03-31")})
    dd["ym"] = dd.date.dt.strftime("%Y-%m"); dd["fy"] = [int(y[:4]) if int(y[5:]) >= 4 else int(y[:4]) - 1 for y in dd.ym]
    acct = fsd.assign(年月=fsd.date.dt.strftime("%Y-%m")).groupby(["store_id", "年月"], as_index=False).size()
    acct = acct.rename(columns={"store_id": "店番"}).assign(その他経費=0.0)
    sm = f(fsd.rename(columns={"date": "biz_date"}), acct, st, dd)
    res = res.merge(sm[["store_id", "ym", "is_existing"]].rename(columns={"is_existing": "F247"}), on=["store_id", "ym"], how="left")

    # F248：store_month_from_gen(fsd, st)
    ns = {"pd": pd, "np": np}
    f = grab(A / "F248_monthly_report_template_fictional_retail" / "src" / "03_レポート.py", "store_month_from_gen", ns)
    sm = f(fsd, st)
    res = res.merge(sm[["store_id", "ym", "is_existing"]].rename(columns={"is_existing": "F248"}), on=["store_id", "ym"], how="left")

    # F250：existing_flags(st, months)
    ns = {"pd": pd, "np": np}
    f = grab(A / "F250_sales_drop_explanation_fictional_retail" / "src" / "02_整形.py", "existing_flags", ns)
    fl = f(st, MONTHS).rename(columns={"is_existing": "F250"})
    res = res.merge(fl, on=["store_id", "ym"], how="left")

    # 営業していない月（F247・F248 は行が無い）は 0 とみなす
    for c in ["F247", "F248"]:
        res[c] = res[c].fillna(0).astype(int)
    cols = ["設定書", "F246", "F247", "F248", "F250"]
    res["割れた"] = res[cols].nunique(axis=1) > 1
    real = res[res.store_id < 90]; edge = res[res.store_id >= 90]
    split_real = real[real.割れた]; split_edge = edge[edge.割れた]
    print(f"実際の24店×48か月＝{len(real)}：判定が割れたのは {len(split_real)}")
    print(f"境目の4店×48か月＝{len(edge)}：判定が割れたのは {len(split_edge)}")
    if len(split_edge):
        print(split_edge[["store_id", "ym", *cols]].to_string(index=False))
    got = {(int(r.store_id), r.ym) for r in split_edge.itertuples()}
    ok = len(split_real) == 0 and got == KNOWN_SPLIT
    print("結果：", "OK（docs/decisions.md の D1 のとおり）" if ok else "NG（コードか決めごとが変わった。D1 を見直す）")
    return ok, res


if __name__ == "__main__":
    ok, res = run()
    out = HERE / "work"; out.mkdir(exist_ok=True)
    res.to_csv(out / "test_rules.csv", index=False, encoding="utf-8-sig")
    sys.exit(0 if ok else 1)
