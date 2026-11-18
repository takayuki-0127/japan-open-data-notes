"""data/raw の Excel・CSV を読み、分析に使う CSV を data/ に作る。ネットにはつながない。
品目・年齢・列は、行や列の位置ではなく表の見出しの文字で選ぶ。点検は results/build_checks.csv に書く。"""
import gzip, io, pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; D = ROOT / "data"; R = ROOT / "results"
R.mkdir(exist_ok=True)
checks = []


def clean(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    s = str(v).replace("\n", "").replace("　", "").replace(" ", "").strip()
    return s or None


def header_paths(df, top, bottom):
    """見出しの段を、結合セルの分だけ右へ広げてから上から「/」でつなぐ。上の段に文字がある列で広げを切る。"""
    ncol = df.shape[1]
    filled, boundary = [], [False] * ncol
    for r in range(top, bottom + 1):
        row, cur = [], None
        for c in range(ncol):
            v = clean(df.iat[r, c])
            if boundary[c]:
                cur = None
            if v:
                cur = v
            row.append(cur)
        filled.append(row)
        boundary = [boundary[c] or clean(df.iat[r, c]) is not None for c in range(ncol)]
    return ["/".join([filled[i][c] for i in range(len(filled)) if filled[i][c]]) for c in range(ncol)]


def num(v):
    if isinstance(v, str):
        v = v.replace(",", "").strip()
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def year_of(lbl):
    m = re.search(r"\((\d{4})\)", str(lbl))
    return int(m.group(1)) if m else None


# 1) 花き 累年（全国）。切り花類は品目ごと、ほかは類の計
KAKI = {"kirihana": ("kirihana_zenkoku.xls", 4, 7, "切り花類"), "hachimono": ("hachimono_zenkoku.xls", 4, 7, "鉢もの類"),
        "naemono": ("naemono_zenkoku.xls", 4, 7, "花壇用苗もの類"), "kyukon": ("kyukon_zenkoku.xls", 4, 6, "球根類")}
recs = []
for key, (fn, top, bot, total_name) in KAKI.items():
    df = pd.read_excel(RAW / "kaki" / fn, header=None)
    paths = header_paths(df, top, bot - 1)          # 単位の段は除く
    units = [clean(df.iat[bot, c]) if key != "kyukon" else clean(df.iat[bot, c]) for c in range(df.shape[1])]
    first = bot + 1
    cols = {}
    for c, p in enumerate(paths):
        parts = p.split("/")
        if len(parts) < 2 or parts[0] == "年次":
            continue
        item, meas = parts[0], parts[1]
        sub = parts[2] if len(parts) > 2 else "計"
        if sub != "計" or meas not in ("作付面積", "収穫面積", "出荷量"):
            continue
        cols[(item, "area" if "面積" in meas else "ship")] = c
    for r in range(first, df.shape[0]):
        y = year_of(df.iat[r, 0])
        if y is None:
            continue
        for (item, m), c in cols.items():
            v = num(df.iat[r, c])
            u = units[c] if key != "kyukon" else units[c]
            if m == "area" and v == v:
                # 面積の単位：見出しは a だが、注記のとおり古い年は ha。注記の年で ha→a に直す
                if key == "kirihana" and y <= 2001: v *= 100
                if key == "hachimono" and y <= 1981: v *= 100
                if key == "naemono" and y <= 1979: v *= 100
                if key == "kyukon": v = v if y >= 2002 else v * 100
            recs.append({"group": key, "item": item, "is_total": item == total_name, "year": y, "measure": m, "value": v})
    checks.append({"check": f"花き {fn} の品目数（出荷量の計の列）", "value": sum(1 for k in cols if k[1] == "ship"), "ok": True})
K = pd.DataFrame(recs).dropna(subset=["value"])
# 2025年（令和7年産）の全国の表：品目名の文字で行を選ぶ
r7 = pd.read_excel(RAW / "kaki" / "r7_zenkoku.xlsx", header=None)
hdr = [clean(r7.iat[4, c]) for c in range(r7.shape[1])]
ca = hdr.index("作付（収穫）面積"); cs = hdr.index("出荷量")
group_of = {"切り花類": "kirihana", "球根類": "kyukon", "鉢もの類": "hachimono", "花壇用苗もの類": "naemono"}
g = None; seen = set()
for r in range(r7.shape[0]):
    names = [clean(r7.iat[r, c]) for c in range(1, ca)]
    names = [n for n in names if n and n != "うち"]
    if not names or not (num(r7.iat[r, cs]) == num(r7.iat[r, cs])):
        continue
    name = names[-1]
    if name in group_of:
        g = group_of[name]
    key = (g, name)
    if key in seen:
        continue
    seen.add(key)
    name_k = {"輪ぎく": "大・中輪ぎく"}.get(name, name)
    for m, c in [("area", ca), ("ship", cs)]:
        K = pd.concat([K, pd.DataFrame([{"group": g, "item": name_k, "is_total": name in group_of, "year": 2025, "measure": m, "value": num(r7.iat[r, c])}])])
K = K.sort_values(["group", "item", "measure", "year"]).reset_index(drop=True)
K.to_csv(D / "kaki_national.csv", index=False)
# 点検：2025年の表の「対前年産比」と、累年の2024年から計算した比が合うか（切り花類・きく・ばら）
for name in ["切り花類", "きく", "ばら", "カーネーション"]:
    row = [r for r in range(r7.shape[0]) if name in [clean(r7.iat[r, c]) for c in range(1, ca)]][0]
    ratio_tbl = num(r7.iat[row, cs + 2])
    s = K[(K.item == name) & (K.measure == "ship")].set_index("year").value
    ratio_calc = s[2025] / s[2024] * 100
    checks.append({"check": f"2025年の{name}の出荷量の対前年産比（表 {ratio_tbl:.0f}%）と計算値", "value": round(ratio_calc, 1), "ok": abs(ratio_calc - ratio_tbl) <= 1})
# 点検：切り花類の2002年前後の面積（ha→a の直し）がつながっているか
s = K[(K.item == "切り花類") & (K.measure == "area")].set_index("year").value
checks.append({"check": "切り花類の面積 2001→2002年の比（単位の直しの確かめ）", "value": round(s[2002] / s[2001], 3), "ok": 0.9 < s[2002] / s[2001] < 1.1})

# 2) 家計調査 第4-6表：切り花の支出（年齢階級別）。年齢の見出しと「支出金額」の見出しで列を選ぶ
AGES = ["平均", "29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
rows = []
for f in sorted((RAW / "kakei").glob("kakei_4-6_*")):
    y = int(re.search(r"(\d{4})", f.name).group(1))
    df = pd.read_excel(f, header=None)
    # 見出しの段：年齢と指標（2020年以降は「平均・支出金額」のように1つのセル）
    age_of, meas_of = {}, {}
    for r in range(0, 14):
        cur = None
        for c in range(df.shape[1]):
            v = clean(df.iat[r, c])
            if v and "・" in v and v.split("・")[0] in AGES:
                age_of[c] = v.split("・")[0]; meas_of[c] = v.split("・")[1]
    if not age_of:
        ra = [r for r in range(14) if "29歳以下" in [clean(x) for x in df.iloc[r].tolist()]][0]
        rm = [r for r in range(14) if "支出金額" in [clean(x) for x in df.iloc[r].tolist()]][0]
        rf = [r for r in range(14) if "購入頻度" in [clean(x) for x in df.iloc[r].tolist()]][0]
        # 年齢の見出しの位置から右で最初の「支出金額」の列を支出、その1つ左の「購入頻度」の列を頻度とする
        pos = {clean(df.iat[ra, c]): c for c in range(df.shape[1]) if clean(df.iat[ra, c]) in AGES}
        for a_, p0 in pos.items():
            cs0 = min(c for c in range(p0, df.shape[1]) if clean(df.iat[rm, c]) == "支出金額")
            cf0 = cs0 - 1
            assert "購入頻度" in ((clean(df.iat[rf, cf0]) or "") + (clean(df.iat[rm, cf0]) or "")), (f, a_)
            age_of[cs0] = a_; meas_of[cs0] = "支出金額"
            age_of[cf0] = a_; meas_of[cf0] = "購入頻度"
    rr = [r for r in range(df.shape[0]) if "切り花" in [clean(x) for x in df.iloc[r].tolist()]]
    assert len(rr) == 1, (f, rr)
    rw = [r for r in range(df.shape[0]) if any((clean(x) or "").startswith("世帯数分布") for x in df.iloc[r].tolist())][0]
    for a in AGES:
        cs_ = [c for c in age_of if age_of[c] == a and meas_of.get(c) == "支出金額"]
        cf_ = [c for c in age_of if age_of[c] == a and meas_of.get(c) == "購入頻度"]
        assert len(cs_) == 1 and len(cf_) == 1, (f, a, cs_, cf_)
        # 世帯数分布は購入頻度の列か支出金額の列のどちらかに入っている
        w = num(df.iat[rw, cf_[0]]); w = w if w == w else num(df.iat[rw, cs_[0]])
        rows.append({"year": y, "age": a, "spend": num(df.iat[rr[0], cs_[0]]), "freq_per100": num(df.iat[rr[0], cf_[0]]), "weight": w})
A = pd.DataFrame(rows)
A.to_csv(D / "kakei_cutflower_age.csv", index=False)
# 点検：年齢別の支出を世帯数分布で重み付けした平均が、表の「平均」と合うか
for y, gq in A.groupby("year", sort=True):
    sub = gq[gq.age != "平均"]
    wavg = (sub.spend * sub.weight).sum() / sub.weight.sum()
    avg = gq[gq.age == "平均"].spend.iloc[0]
    checks.append({"check": f"家計 {y}年 年齢別の重み付き平均と平均（円）", "value": f"{wavg:.0f} / {avg:.0f}", "ok": abs(wavg - avg) / avg < 0.02})

# 3) 長期時系列（1963〜2007年、農林漁家世帯を除く）
lt = pd.read_excel(RAW / "kakei" / "kakei_nonfarm_items_1963_2007.xls", header=None, sheet_name=None)
found = None
for sh, df in lt.items():
    for c in range(df.shape[1]):
        if clean(df.iat[8, c]) == "切り花" and clean(df.iat[10, c]) == "金額":
            found = (sh, c)
sh, c = found
df = lt[sh]
era, yrs = None, []
for r in range(12, df.shape[0]):
    lbl = clean(df.iat[r, 0])
    if lbl is None:
        continue
    m = re.match(r"(昭和|平成)?(元|\d+)", lbl)
    if not m:
        continue
    if m.group(1):
        era = m.group(1)
    n = 1 if m.group(2) == "元" else int(m.group(2))
    y = (1925 if era == "昭和" else 1988) + n
    yrs.append({"year": y, "spend_nonfarm": num(df.iat[r, c])})
LT = pd.DataFrame(yrs)
checks.append({"check": "長期時系列の年（最初・最後・数）", "value": f"{LT.year.min()}・{LT.year.max()}・{len(LT)}", "ok": LT.year.min() == 1963 and LT.year.max() == 2007 and len(LT) == 45})
LT.to_csv(D / "kakei_cutflower_longterm.csv", index=False)

# 4) 消費者物価指数（切り花、2025年=100）
cp = pd.read_csv(RAW / "kakei" / "cpi_item_annual.csv", encoding="cp932", header=None, low_memory=False)
cc = [i for i in range(cp.shape[1]) if clean(cp.iat[0, i]) == "切り花"]
assert len(cc) == 1
CPI = pd.DataFrame({"year": pd.to_numeric(cp.iloc[6:, 0], errors="coerce"), "cpi_cutflower": pd.to_numeric(cp.iloc[6:, cc[0]], errors="coerce")}).dropna()
CPI["year"] = CPI.year.astype(int)
CPI.to_csv(D / "cpi_cutflower.csv", index=False)
checks.append({"check": "CPI 切り花 2025年", "value": float(CPI.set_index("year").loc[2025, "cpi_cutflower"]), "ok": float(CPI.set_index("year").loc[2025, "cpi_cutflower"]) == 100.0})

# 5) 貿易統計：切り花（HS 0603）の輸入
IMP_NAME = {"060311": "ばら", "060312": "カーネーション", "060313": "ラン", "060314": "きく", "060315": "ゆり", "060319": "その他の生鮮", "060390": "乾燥・染色など"}
ex = []
for f in sorted((RAW / "trade").glob("import_*.csv.gz")):
    tr = pd.read_csv(io.StringIO(gzip.decompress(f.read_bytes()).decode("cp932")), dtype=str)
    tr["HS"] = tr["HS"].str.strip("'")
    b = tr[tr.HS.str[:4] == "0603"].copy()
    assert set(b.Unit2.str.strip()) == {"KG"}
    for c in ["Quantity2-Year", "Value-Year"]:
        b[c] = b[c].astype(float)
    y = int(tr.Year.iloc[0])
    for h6, gq in b.groupby(b.HS.str[:6], sort=True):
        ex.append({"year": y, "hs6": h6, "name": IMP_NAME[h6], "kg": gq["Quantity2-Year"].sum(), "value_1000yen": gq["Value-Year"].sum()})
IM = pd.DataFrame(ex).sort_values(["year", "hs6"])
IM.to_csv(D / "cutflower_import_hs6.csv", index=False)
checks.append({"check": "輸入の年数", "value": int(IM.year.nunique()), "ok": int(IM.year.nunique()) == 17})
pd.DataFrame(checks).to_csv(R / "build_checks.csv", index=False)
print(pd.DataFrame(checks).to_string())
