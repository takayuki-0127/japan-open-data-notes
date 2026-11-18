"""元データから分析用の CSV を作る（オフライン）。
- 県名は行の見出しの文字で、項目（生換算重量、板のりの枚数、月の区分）は列の見出しの文字で選ぶ
- 確かめ：全国の暦年の生換算重量と長期累年の表の全国の値、養殖年の「7〜12月＋翌年1〜6月＝養殖年」の板のりの枚数
"""
import json, pathlib, re, unicodedata
import numpy as np
import pandas as pd
import xlrd, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; D = ROOT / "data"; R = ROOT / "results"
R.mkdir(exist_ok=True)
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "千葉", "東京", "神奈川", "新潟", "富山", "石川", "福井",
         "静岡", "愛知", "三重", "京都", "大阪", "兵庫", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛",
         "高知", "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]


def nk(s):
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s)))


def rows_of(p):
    if p.suffix == ".xlsx":
        wb = openpyxl.load_workbook(p, data_only=True)
        return [["" if v is None else v for v in r] for r in wb.worksheets[0].iter_rows(values_only=True)]
    sh = xlrd.open_workbook(p, logfile=open("/dev/null", "w")).sheet_by_index(0)
    return [sh.row_values(i) for i in range(sh.nrows)]


def num(v):
    if isinstance(v, (int, float)): return float(v)
    s = nk(v).replace(",", "")
    if s in ("-",): return 0.0
    if s in ("x", "X", "…", "...", ""): return np.nan
    try: return float(s)
    except ValueError: return np.nan


def parse_year(y):
    p = next((RAW / "maff").glob(f"nori_{y}.xls*"))
    rows = rows_of(p)
    ncol = max(len(r) for r in rows)
    rows = [list(r) + [""] * (ncol - len(r)) for r in rows]
    iz = next(i for i, r in enumerate(rows) if any(nk(c) == "全国" for c in r[:3]))
    H = [nk("/".join(str(rows[i][j]) for i in range(iz) if str(rows[i][j]).strip() and not isinstance(rows[i][j], float))) for j in range(ncol)]
    c_cal = next(j for j, h in enumerate(H) if "生換算重量" in h and "1~12月" in h)
    c_sea = next(j for j, h in enumerate(H) if "生換算重量" in h and "翌年6月" in h)
    # 板のりの枚数（計）の列。近くの列（その列から右へ2列まで）にある「のり類養殖（…）」の文字で月の区分を決める
    ita = [j for j, h in enumerate(H) if "板のり" in h and "計" in h]
    lab = {}
    for j in ita:
        g = next((H[k] for k in range(j, min(j + 3, ncol)) if "のり類養殖" in H[k]), "")
        m = re.search(r"のり類養殖\(([^)]*)\)", g)
        lab[j] = m.group(1) if m else ""
    def cols(pats):
        return [j for j in ita if lab[j] in pats]
    c_seaita = cols({"7月~翌年6月", "養殖年7月~翌年6月", "養殖年前年7~6月"})
    if c_seaita and "前年" in lab[c_seaita[0]]:  # 2024年の表：養殖年は前年7月〜当年6月
        c_h2, c_h1n = cols({"前年7~12月"}), cols({"1~6月"})
    else:
        c_h2 = cols({"7~12月"}) or cols({"7~9月", "10~12月"})
        c_h1n = cols({"翌年1~6月"}) or cols({"翌年1~3月", "翌年4~6月"})
    assert c_h2 and c_h1n and len(c_seaita) == 1, (y, lab)
    out = []
    for r in rows[iz:]:
        name = next((nk(c) for c in r[:3] if nk(c)), "")
        if name == "全国" or name in PREFS:
            if any(o["pref"] == name for o in out):
                continue
            out.append(dict(table_year=y, pref=name, cal_t=num(r[c_cal]), season_t=num(r[c_sea]),
                            ita_season=num(r[c_seaita[0]]), ita_h2=sum(num(r[j]) for j in c_h2), ita_h1n=sum(num(r[j]) for j in c_h1n)))
    meta = dict(table_year=y, c_cal=H[c_cal], c_sea=H[c_sea], season_label=lab[c_seaita[0]], h2=[lab[j] for j in c_h2], h1n=[lab[j] for j in c_h1n],
                n_rows=len(out))
    return out, meta


def parse_long():
    wb = openpyxl.load_workbook(RAW / "maff" / "long_yoshoku_national.xlsx", data_only=True)
    rows = [["" if v is None else v for v in r] for r in wb.worksheets[0].iter_rows(values_only=True)]
    # 見出しの行から「のり類」の列を探す（下の行の「計」を優先）
    hi = [i for i, r in enumerate(rows[:12]) if any("のり" in nk(c) for c in r)]
    j_nori = None
    for i in hi:
        for j, c in enumerate(rows[i]):
            if nk(c).startswith("のり類"):
                j_nori = j; break
        if j_nori is not None: break
    out = []
    for r in rows:
        m = re.search(r"\((\d{4})\)", nk(r[0]))
        if m:
            out.append(dict(year=int(m.group(1)), nori_t=num(r[j_nori])))
    return pd.DataFrame(out).drop_duplicates("year"), nk(rows[hi[0]][j_nori]) if hi else ""


def sst(a):
    lines = (RAW / "jma" / f"area{a}_SST.txt").read_text(encoding="utf-8").splitlines()
    normal = [float(x) for x in lines[3].split(",")[1:]]
    rec = []
    for l in lines:
        m = re.match(r"^(\d{4})\s*,(.*)$", l)
        if m:
            v = [np.nan if "NoData" in x else float(x) for x in m.group(2).split(",")]
            rec.append(dict(year=int(m.group(1)), area=a, annual=v[0], winter=v[1], spring=v[2], summer=v[3], autumn=v[4],
                            autumn_normal=normal[4]))
    return rec


def station(b):
    import html as _h
    s = (RAW / "jma" / f"station_{b}.html").read_text(encoding="utf-8")
    name = re.findall(r"<h3[^>]*>(.*?)（", s, re.S)[0].strip()
    rec = []
    for m in re.finditer(r"year=(\d{4})&month=&day=&view=\">(\d{4})</a></div>(.*?)</tr>", s, re.S):
        cells = [_h.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", m.group(3), re.S)]
        for mo in range(1, 13):
            raw = cells[mo - 1] if mo - 1 < len(cells) else ""
            v = re.match(r"-?\d+\.\d", raw)
            rec.append(dict(station=name, block=b, year=int(m.group(2)), month=mo, temp=float(v.group()) if v else np.nan, flag="" if re.fullmatch(r"-?\d+\.\d", raw) else raw))
    return rec


def main():
    allrows, metas = [], []
    for y in range(2004, 2025):
        o, m = parse_year(y); allrows += o; metas.append(m)
    T = pd.DataFrame(allrows)
    meta = pd.DataFrame(metas)
    # 養殖年：表の年 y の「7月〜翌年6月」は y年7月からの1期。2024年の表だけ「前年7〜6月」（2023年7月からの期）
    T["season"] = np.where(T.table_year == 2024, 2023, T.table_year)
    chk = []
    # 確かめ1：2024年の表と2023年の表の養殖年の値が一致するか（同じ期）
    a = T[T.table_year == 2023].set_index("pref").season_t; b = T[T.table_year == 2024].set_index("pref").season_t
    both = a.notna() & b.notna()
    chk.append(dict(check="season_2023_in_2023_vs_2024_table_maxabs", value=float((a[both] - b[both]).abs().max()), n=int(both.sum())))
    # 確かめ2：7〜12月＋翌年1〜6月＝養殖年（板のりの枚数、県の行）
    ok = T[["ita_season", "ita_h2", "ita_h1n"]].notna().all(axis=1)
    diff = (T.ita_h2 + T.ita_h1n - T.ita_season)[ok]
    chk.append(dict(check="ita_h2_plus_h1n_minus_season_maxabs", value=float(diff.abs().max()), n=int(ok.sum())))
    # 確かめ3：全国の暦年の生換算重量と長期累年の表
    Lg, lab = parse_long()
    nat = T[T.pref == "全国"].set_index("table_year").cal_t
    m = Lg.set_index("year").nori_t.reindex(nat.index)
    chk.append(dict(check=f"national_cal_vs_long_table({lab})_maxabs", value=float((nat - m).abs().max()), n=int(m.notna().sum())))
    ck = pd.DataFrame(chk); ck.to_csv(R / "build_checks.csv", index=False)
    meta.to_csv(R / "build_columns.csv", index=False)
    # 2024年の表は2023年の期を改めて載せている（数県で数十t の改定）。2023年の期は新しい2024年の表の値を使う
    chk[0]["note"] = "2024年の表で改定（全国 -94t など）。2023年の期は2024年の表の値を使う"
    ck = pd.DataFrame(chk); ck.to_csv(R / "build_checks.csv", index=False)
    assert ck.value.iloc[0] <= 0.001 * float(b["全国"]) and ck.value.iloc[1] <= 2 and ck.value.iloc[2] <= 1, ck
    S = pd.concat([T[T.table_year <= 2022], T[T.table_year == 2024]]).drop(columns=["table_year", "cal_t"]).copy()
    assert sorted(S.season.unique()) == list(range(2004, 2024))
    S.to_csv(D / "nori_by_pref_season.csv", index=False)
    T[["table_year", "pref", "cal_t"]].rename(columns={"table_year": "year"}).to_csv(D / "nori_by_pref_calendar.csv", index=False)
    Lg.to_csv(D / "nori_national_long.csv", index=False)
    pd.DataFrame(sum([sst(a) for a in ["C", "N", "M", "K", "all"]], [])).to_csv(D / "jma_sst_area_anomaly.csv", index=False)
    st = pd.DataFrame(sum([station(b) for b in [47813, 47891, 47636, 47682, 47590]], []))
    st[(st.year >= 1991) & (st.year <= 2024)].to_csv(D / "jma_station_monthly_temp.csv", index=False)
    print(ck.to_string()); print(meta.to_string())


if __name__ == "__main__":
    main()
