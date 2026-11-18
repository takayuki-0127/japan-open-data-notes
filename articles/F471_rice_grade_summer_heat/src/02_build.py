"""元データから分析用の CSV を作る（オフライン）。
- 県名・地方名（農政局）は、行の順ではなく表の見出しの文字で付ける
- 1等比率は「1等の数量 ÷ 総計」で計算し直し、表に印刷された比率と照らす
"""
import json, pathlib, re, html
import numpy as np
import pandas as pd
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; D = ROOT / "data"; R = ROOT / "results"
R.mkdir(exist_ok=True)
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "山梨", "長野", "静岡", "新潟", "富山", "石川", "福井", "岐阜", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良",
         "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分",
         "宮崎", "鹿児島", "沖縄"]
# 表の地方の見出し（農政局）→ 地方名。北海道・沖縄は県の行がそのまま地方
REGION_HEAD = {"東北農政局": "東北", "関東農政局": "関東", "北陸農政局": "北陸", "東海農政局": "東海",
               "近畿農政局": "近畿", "中国四国農政局": "中国四国", "九州農政局": "九州"}
STATIONS = {  # 01_fetch.py と同じ（block_no, 地点名）
    "北海道": (47412, "札幌"), "青森": (47575, "青森"), "岩手": (47584, "盛岡"), "宮城": (47590, "仙台"), "秋田": (47582, "秋田"),
    "山形": (47588, "山形"), "福島": (47595, "福島"), "茨城": (47629, "水戸"), "栃木": (47615, "宇都宮"), "群馬": (47624, "前橋"),
    "埼玉": (47626, "熊谷"), "千葉": (47682, "千葉"), "東京": (47662, "東京"), "神奈川": (47670, "横浜"), "山梨": (47638, "甲府"),
    "長野": (47610, "長野"), "静岡": (47656, "静岡"), "新潟": (47604, "新潟"), "富山": (47607, "富山"), "石川": (47605, "金沢"),
    "福井": (47616, "福井"), "岐阜": (47632, "岐阜"), "愛知": (47636, "名古屋"), "三重": (47651, "津"), "滋賀": (47761, "彦根"),
    "京都": (47759, "京都"), "大阪": (47772, "大阪"), "兵庫": (47770, "神戸"), "奈良": (47780, "奈良"), "和歌山": (47777, "和歌山"),
    "鳥取": (47746, "鳥取"), "島根": (47741, "松江"), "岡山": (47768, "岡山"), "広島": (47765, "広島"), "山口": (47784, "山口"),
    "徳島": (47895, "徳島"), "香川": (47891, "高松"), "愛媛": (47887, "松山"), "高知": (47893, "高知"), "福岡": (47807, "福岡"),
    "佐賀": (47813, "佐賀"), "長崎": (47817, "長崎"), "熊本": (47819, "熊本"), "大分": (47815, "大分"), "宮崎": (47830, "宮崎"),
    "鹿児島": (47827, "鹿児島"), "沖縄": (47936, "那覇")}


def num(v):
    if v is None: return np.nan
    if isinstance(v, (int, float)): return float(v)
    s = str(v).replace(",", "").strip()
    if s in ("-", "", "…", "x"): return 0.0 if s == "-" else np.nan
    return float(s)


def from_xlsx(y):
    wb = openpyxl.load_workbook(RAW / "maff" / f"kensa_{y}.xlsx", read_only=True, data_only=True)
    ws = wb[[n for n in wb.sheetnames if "粳等級" in n][0]]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    # 見出しの行（総計・１等…）を文字で探し、列の位置を決める
    hi = next(i for i, r in enumerate(rows) if r and "総計" in [str(v) for v in r])
    h = [str(v) if v is not None else "" for v in rows[hi]]
    c_tot = h.index("総計"); c1 = [i for i, v in enumerate(h) if v == "１等"]
    c_q1, c_r1 = c1[0], c1[1]
    c_q = {g: h.index(g) for g in ["２等", "３等", "規格外"]}
    out, region = [], None
    for r in rows[hi + 1:]:
        name = "".join(str(v) for v in r[:2] if v is not None).replace(" ", "").replace("　", "")
        if name in REGION_HEAD: region = REGION_HEAD[name]; continue
        if name.startswith("合計"):
            out.append(dict(year=y, pref="全国", region="全国", total=num(r[c_tot]), q1=num(r[c_q1]), r1_printed=num(r[c_r1]),
                            q2=num(r[c_q["２等"]]), q3=num(r[c_q["３等"]]), qx=num(r[c_q["規格外"]])))
            break
        if name in PREFS:
            reg = name if name in ("北海道", "沖縄") else region
            out.append(dict(year=y, pref=name, region=reg, total=num(r[c_tot]), q1=num(r[c_q1]), r1_printed=num(r[c_r1]),
                            q2=num(r[c_q["２等"]]), q3=num(r[c_q["３等"]]), qx=num(r[c_q["規格外"]])))
    return out


NUM = r"(-|[0-9][0-9,]*\.?[0-9]*)"


def from_txt(y):
    lines = (RAW / "pdf_text" / f"kensa_{y}.txt").read_text(encoding="utf-8").splitlines()
    i0 = next(i for i, l in enumerate(lines) if "等級別検査数量" in l)
    i1 = next(i for i in range(i0, len(lines)) if "水稲うるち玄米" in lines[i])
    out, region = [], None
    for l in lines[i1 + 1:]:
        m = re.match(r"^\s*([^\d\-]+?)\s+" + r"\s+".join([NUM] * 9) + r"\s*$", l)
        if not m:
            continue
        name = re.sub(r"[\s　]", "", m.group(1))
        if name.endswith(("県", "府", "都")) and name[:-1] in PREFS: name = name[:-1]  # 「沖縄県」と書かれた年がある
        vals = [num(v) for v in m.groups()[1:]]
        rec = dict(year=y, total=vals[0], q1=vals[1], q2=vals[2], q3=vals[3], qx=vals[4], r1_printed=vals[5])
        if name in REGION_HEAD: region = REGION_HEAD[name]; continue
        if name == "合計":
            out.append(dict(pref="全国", region="全国", **rec)); break
        if name in PREFS:
            out.append(dict(pref=name, region=name if name in ("北海道", "沖縄") else region, **rec))
    return out


def jma(block):
    s = (RAW / "jma" / f"{block}.html").read_text(encoding="utf-8")
    rows = []
    for m in re.finditer(r"year=(\d{4})&month=&day=&view=\">(\d{4})</a></div>(.*?)</tr>", s, re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", m.group(3), re.S)]
        y = int(m.group(2))
        for mo in range(1, 13):
            raw = cells[mo - 1] if mo - 1 < len(cells) else ""
            flag = "" if re.fullmatch(r"-?\d+\.\d", raw) else raw
            v = re.match(r"-?\d+\.\d", raw)
            rows.append(dict(year=y, month=mo, temp=float(v.group()) if v else np.nan, raw=raw, flag=flag))
    return pd.DataFrame(rows)


def varieties(y):
    """銘柄別（品種×産地）の検査数量と1等比率（2016年産以降の Excel）。"""
    wb = openpyxl.load_workbook(RAW / "maff" / f"kensa_{y}.xlsx", read_only=True, data_only=True)
    rows = [list(r) for r in wb["水粳品種"].iter_rows(values_only=True)]
    hi = next(i for i, r in enumerate(rows) if r[:2] == ["品種", "産地"])
    c_tot = rows[hi].index("総計"); c1 = rows[hi + 1].index("１等")
    out = []
    for r in rows[hi + 2:]:
        v, area = (str(r[0]).strip() if r[0] else ""), (str(r[1]).strip() if r[1] else "")
        if area in PREFS and v:
            tot = num(r[c_tot]); r1 = num(r[c1]) if tot and tot > 0 else np.nan
            out.append(dict(year=y, variety=v, pref=area, total=tot, r1=r1))
    return out


def main():
    recs = []
    for y in range(2006, 2025):
        recs += from_txt(y) if y <= 2015 else from_xlsx(y)
    g = pd.DataFrame(recs)
    g["r1"] = 100 * g["q1"] / g["total"]
    checks = []
    for y, d in g.groupby("year", sort=True):
        p = d[d.pref != "全国"]
        nat = d[d.pref == "全国"].iloc[0]
        checks.append(dict(year=y, n_pref=len(p), n_unique=p.pref.nunique(),
                           sum_total_vs_national=round(p.total.sum() / nat.total, 5),
                           grades_sum_vs_total_maxdiff=round(float(((p.q1 + p.q2 + p.q3 + p.qx) / p.total - 1).abs().max()), 5),
                           max_abs_r1_recalc_minus_printed=round(float((p.r1 - p.r1_printed).abs()[p.total > 1000].max()), 3),
                           regions=",".join(pd.unique(p.region.astype(str)))))
    ck = pd.DataFrame(checks)
    # 全国の 1等比率の推移の表（別ファイル）と照らす
    wb = openpyxl.load_workbook(RAW / "maff" / "ittou_suii_national.xlsx", data_only=True)
    ws = wb[wb.sheetnames[0]]
    nat = {}
    for r in ws.iter_rows(values_only=True):
        r = [v for v in r if v is not None]
        if len(r) >= 2 and isinstance(r[0], str) and r[0].endswith("年") and isinstance(r[1], (int, float)):
            t = r[0].replace("元", "1")
            era, n = ("平成", 1988) if t.startswith("平成") else ("令和", 2018)
            nat[n + int(re.sub(r"\D", "", t))] = float(r[1])
    ck["national_series"] = ck.year.map(nat)
    ck["national_recalc"] = ck.year.map(g[g.pref == "全国"].set_index("year").r1.round(1))
    ck.to_csv(R / "build_checks.csv", index=False)
    assert (ck.n_pref == 47).all() and (ck.n_unique == 47).all(), ck
    assert (ck.max_abs_r1_recalc_minus_printed <= 0.11).all(), ck
    assert ((ck.national_series - ck.national_recalc).abs() <= 0.11).all(), ck
    g = g.drop(columns=["r1_printed"])
    # 気温
    t = []
    for pref, (b, name) in STATIONS.items():
        d = jma(b); d["pref"] = pref; d["station"] = name; t.append(d)
    t = pd.concat(t, ignore_index=True)
    t = t[(t.year >= 1991) & (t.year <= 2024)]
    t.to_csv(D / "jma_monthly_temp.csv", index=False)
    w = t.pivot_table(index=["pref", "year"], columns="month", values="temp").reset_index()
    w["t_aug"] = w[8]; w["t_julaug"] = (w[7] + w[8]) / 2; w["t_augsep"] = (w[8] + w[9]) / 2
    fl = t[t.month.isin([7, 8, 9]) & (t.flag != "")][["pref", "year", "month", "raw"]]
    fl.to_csv(R / "temp_flags_jul_sep.csv", index=False)
    panel = g.merge(w[["pref", "year", "t_aug", "t_julaug", "t_augsep"]], on=["pref", "year"], how="left")
    panel["station"] = panel.pref.map({k: v[1] for k, v in STATIONS.items()})
    panel = panel.sort_values(["year", "pref"], key=lambda s: s.map({p: i for i, p in enumerate(["全国"] + PREFS)}) if s.name == "pref" else s)
    panel.to_csv(D / "panel.csv", index=False, float_format="%.6g")
    v = pd.DataFrame(sum([varieties(y) for y in range(2016, 2025)], []))
    v.to_csv(D / "varieties.csv", index=False, float_format="%.6g")
    # 銘柄の合計が県の総計を超えないか（総計には銘柄以外も入る）
    vs = v.groupby(["year", "pref"]).total.sum().rename("v_total").reset_index().merge(g[["year", "pref", "total"]], on=["year", "pref"])
    pd.DataFrame([dict(rows=len(v), max_ratio_variety_sum_to_pref_total=round(float((vs.v_total / vs.total).max()), 4),
                       median_ratio=round(float((vs.v_total / vs.total).median()), 4))]).to_csv(R / "build_checks_varieties.csv", index=False)
    print(ck.to_string())


if __name__ == "__main__":
    main()
