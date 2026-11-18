"""02 整形（オフライン）。
- 6IIP.xls（単位10億円、10倍して億円に）：見出しの行（「資産残高」「負債残高」「対外純資産」と、その下の項目名）から列の名前を付け、暦年末×項目の長い表にする（億円）。
- 金融収支（月次、億円）を暦年に合計する。12か月そろった年だけ。
- ドル円は12月末の値。
- 増減要因（試算）の抜き出し表を読み、内訳の合計と恒等式を確かめる。
出力：data/iip_annual.csv、data/fin_account_annual.csv、data/usdjpy_yearend.csv、data/factors.csv、results/factor_checks.csv
"""
import json, pathlib, re
import pandas as pd
import xlrd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D, X, R = ROOT / "data" / "raw", ROOT / "data", ROOT / "data" / "extracted", ROOT / "results"
R.mkdir(exist_ok=True)


def iip():
    s = xlrd.open_workbook(RAW / "6IIP.xls").sheet_by_index(0)
    unit = [c for c in s.row_values(3) if "単位" in str(c)][0]
    assert "10億円" in unit, unit   # 表の単位は10億円。金融収支（億円）とそろえるため10倍して億円にする
    top, sub = s.row_values(4), s.row_values(6)
    side, cols = None, {}
    for j in range(2, s.ncols):
        if str(top[j]).strip():
            side = {"資産残高": "assets", "負債残高": "liabilities", "対外純資産": "net"}[str(top[j]).strip()]
        if side is None:
            continue
        item = str(sub[j]).strip() or "合計"
        cols[j] = (side, item)
    rows = []
    for r in range(8, s.nrows):
        m = re.match(r"End of (\d{4})", str(s.cell_value(r, 1)))
        if not m:
            continue
        for j, (side, item) in cols.items():
            v = s.cell_value(r, j)
            if v != "":
                rows.append({"year": int(m.group(1)), "side": side, "item": item, "value_oku": float(v) * 10})
    df = pd.DataFrame(rows)
    # 照らし合わせ：資産・負債の項目の合計と合計の列、純資産＝資産−負債
    w = df.pivot_table(index="year", columns=["side", "item"], values="value_oku")
    for sd in ["assets", "liabilities"]:
        items = [c for c in w[sd].columns if c != "合計"]
        assert (w[sd][items].sum(axis=1) - w[sd]["合計"]).abs().max() <= 30, sd
    assert (w["assets"]["合計"] - w["liabilities"]["合計"] - w["net"]["合計"]).abs().max() <= 30
    return df


def boj(name):
    out = {}
    for s in json.load(open(RAW / name, encoding="utf-8")):
        out[(s["SERIES_CODE"], s["NAME_OF_TIME_SERIES_J"])] = pd.Series(s["VALUES"]["VALUES"], index=s["VALUES"]["SURVEY_DATES"], dtype=float)
    return out


def main():
    iip().to_csv(D / "iip_annual.csv", index=False)
    rows = []
    for (code, name), v in boj("boj_bp01_financial_account.json").items():
        yr = (v.index // 100)
        g = v.groupby(yr)
        n = g.count()
        for y, val in g.sum().items():
            if n[y] == 12:
                rows.append({"year": int(y), "code": code, "name": name, "value_oku": float(val)})
    pd.DataFrame(rows).sort_values(["code", "year"]).to_csv(D / "fin_account_annual.csv", index=False)
    (code, name), fx = next(iter(boj("boj_fm08_usdjpy.json").items()))
    dec = fx[[d for d in fx.index if d % 100 == 12]]
    pd.DataFrame({"year": [d // 100 for d in dec.index], "usdjpy_dec_end": dec.values}).to_csv(D / "usdjpy_yearend.csv", index=False)

    f = pd.read_csv(X / "iip_factors.csv")
    f.to_csv(D / "factors.csv", index=False)
    chk = []
    for (y, sd), g in f.groupby(["year", "side"]):
        tot = g[g["item"] == "合計"].iloc[0]
        it = g[g["item"] != "合計"]
        chk.append({"year": y, "side": sd,
                    "items_minus_total_curr": float(it["curr"].sum() - tot["curr"]) if len(it) else 0.0,
                    "max_identity_gap": float((g["change"] - g["flow"] - g["fx"] - g["other"]).abs().max()),
                    "max_prev_curr_gap": float((g["prev"] + g["change"] - g["curr"]).abs().max())})
    c = pd.DataFrame(chk)
    c.to_csv(R / "factor_checks.csv", index=False)
    assert c["items_minus_total_curr"].abs().max() <= 5 and c["max_identity_gap"].max() <= 3 and c["max_prev_curr_gap"].max() <= 3, c
    print(c.drop(columns="side").abs().max().to_dict())


if __name__ == "__main__":
    main()
