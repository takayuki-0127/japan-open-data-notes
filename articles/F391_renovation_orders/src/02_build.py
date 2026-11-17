"""data/raw から年度の表を作る（data/*.csv）。
- reform_total.csv：リフォーム受注高（年度、計・住宅・非住宅、億円）。各年度は、その年度を含む最も新しい公表資料の表1-1の値。
- reform_purpose.csv：表2-3-3 用途（住宅・非住宅の総計）×主たる工事目的の受注高（億円）。各年度の公表資料から。
- reform_nonres_use.csv：表2-3-3 非住宅の用途別の受注高（計）。
- starts.csv：建築着工統計 工事費予定額（年度、全国計・住宅計、億円）。
- deflator.csv：建設工事費デフレーター（2020年度=100）建築補修・住宅総合・非住宅総合。
"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
YEARS = range(2016, 2026)
ERA = {"平成": 1988, "令和": 2018}


def wareki(s):
    s = str(s).translate(str.maketrans("０１２３４５６７８９", "0123456789")).replace("元", "1")
    m = re.search(r"(平成|令和)\s*(\d+)", s)
    return ERA[m.group(1)] + int(m.group(2)) if m else None


def num(v):
    return pd.to_numeric(str(v).replace(",", "").strip(), errors="coerce")


def main():
    # 1. 受注高（表1-1）
    tot = {}
    for y in YEARS:
        d = pd.read_excel(RAW / f"reform_fy{y}.xlsx", header=None, sheet_name="年表1-1")
        for i in range(6, len(d)):
            fy = wareki(d.iloc[i, 0])
            if fy and not pd.isna(num(d.iloc[i, 4])):
                tot[fy] = dict(fiscal_year=fy, total=num(d.iloc[i, 4]), housing=num(d.iloc[i, 7]), nonres=num(d.iloc[i, 10]), from_file=y)
    pd.DataFrame([tot[k] for k in sorted(tot)]).to_csv(DATA / "reform_total.csv", index=False)

    # 2. 工事目的（表2-3-3）
    pur, use = [], []
    for y in YEARS:
        d = pd.read_excel(RAW / f"reform_fy{y}.xlsx", header=None, sheet_name="年表2-3-3")
        heads = [str(v).strip() for v in d.iloc[4].tolist()]
        for i in range(7, len(d)):
            g, u = str(d.iloc[i, 1]).strip(), str(d.iloc[i, 2]).strip()
            if g in ("住宅", "非住宅建築物") and u == "総計":
                for j in range(4, len(heads)):
                    if heads[j] not in ("nan", ""):
                        pur.append(dict(fiscal_year=y, group="住宅" if g == "住宅" else "非住宅", purpose=heads[j], value=num(d.iloc[i, j])))
            if g == "非住宅建築物" and u not in ("総計", "nan"):
                use.append(dict(fiscal_year=y, use=u, value=num(d.iloc[i, 4])))
    pd.DataFrame(pur).to_csv(DATA / "reform_purpose.csv", index=False)
    pd.DataFrame(use).to_csv(DATA / "reform_nonres_use.csv", index=False)

    # 3. 着工（工事費予定額、万円→億円）
    xs = pd.read_excel(RAW / "starts_fy_struct_use_pref.xls", header=None, sheet_name=None)
    st = {}
    for name, d in xs.items():
        fy = wareki(name)
        if fy is None or fy < 2014:
            continue
        col0 = d.iloc[:, 0].astype(str).str.replace(r"[\s　]", "", regex=True)
        total = num(d.iloc[col0[col0 == "全国計"].index[0], 3])
        housing = sum(num(v) for v in d.loc[col0 == "住宅計", 3])
        n_pref = int((col0 == "住宅計").sum())
        assert n_pref == 47, (name, n_pref)
        s = st.setdefault(fy, dict(fiscal_year=fy, starts_total=0.0, starts_housing=0.0, sheets=0))
        s["starts_total"] += total / 1e4
        s["starts_housing"] += housing / 1e4
        s["sheets"] += 1
    st = pd.DataFrame([st[k] for k in sorted(st)])
    st["starts_nonres"] = st.starts_total - st.starts_housing
    st.to_csv(DATA / "starts.csv", index=False)

    # 4. デフレーター
    d = pd.read_excel(RAW / "deflator_fy2020base.xlsx", header=None)
    hdr = ["/".join(str(d.iloc[i, j]) for i in range(2, 8)) for j in range(d.shape[1])]
    c_rep = [j for j, h in enumerate(hdr) if h.startswith("建設総合/建築補修")][0]
    c_h = [j for j, h in enumerate(hdr) if h.endswith("住宅総合/住宅総合/住宅総合/住宅総合") and "非住宅" not in h][0]
    c_n = [j for j, h in enumerate(hdr) if h.endswith("非住宅総合/非住宅総合/非住宅総合/非住宅総合")][0]
    rows = []
    for i in range(8, len(d)):
        m = re.match(r"^(\d{4})(年度|$)", str(d.iloc[i, 0]).replace(".0", ""))
        if m:
            rows.append(dict(fiscal_year=int(m.group(1)), defl_repair=num(d.iloc[i, c_rep]), defl_housing=num(d.iloc[i, c_h]),
                             defl_nonres=num(d.iloc[i, c_n]), provisional="暫定" in str(d.iloc[i, 0])))
    pd.DataFrame(rows).to_csv(DATA / "deflator.csv", index=False)
    print("ok")


if __name__ == "__main__":
    main()
