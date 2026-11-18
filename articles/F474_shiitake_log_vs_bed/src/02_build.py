"""data/raw の各年の表（xls・xlsx）から、全国の値と地方別の値を読み出して CSV にする。
年によって列の並びが違うので、見出しの文字で列を決め、決めた列の見出しを毎回確かめる。"""
import pathlib, re, glob, unicodedata
import pandas as pd
import xlrd, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"


def rows(path):
    p = str(path)
    if p.endswith(".xls"):
        b = xlrd.open_workbook(p, logfile=open("/dev/null", "w"))
        sh = b.sheet_by_index(0)
        return [sh.row_values(i) for i in range(sh.nrows)]
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]


def clean(s):
    return re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s))) if s is not None else ""


def num(v):
    if isinstance(v, (int, float)):
        return float(v)
    s = clean(v)
    if s in ("-", "0.0", "0"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return float("nan")  # x（秘匿）・…（不明）


def raw(y, key):
    return next(iter(sorted(glob.glob(str(RAW / f"{y}_{key}.*")))))


def nat_row(r):
    for x in r:
        if any(clean(c) in ("全国", "合計", "計") for c in x[:2]):
            return x
    raise ValueError


def header_text(r, upto):
    """各列の見出しの文字（見出しの行を縦につなぐ）。"""
    w = max(len(x) for x in r)
    return [" ".join(clean(r[i][j]) for i in range(upto) if j < len(r[i]) and clean(r[i][j])) for j in range(w)]


YEARS = list(range(2005, 2026))
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良",
         "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分",
         "宮崎", "鹿児島", "沖縄"]


def pref_of(c):
    s = re.sub(r"^\d+", "", clean(c))
    s = re.sub(r"(都|府|県)$", "", s) if s not in ("京都",) else s
    return s if s in PREFS else None


# ---- しいたけの生産量（乾・生 × 原木・菌床） ----
def shiitake_cols(y, h):
    """列の位置を年の型で決め、見出しの文字を確かめる。"""
    if y <= 2009:      # どんこ・こうしん・山成・乾合計・生原木・生菌床・生合計
        c = {"dry_total": 4, "fresh_log": 5, "fresh_bed": 6, "fresh_total": 7}
        assert "合計" in h[4] and "原木" in h[5] and "菌床" in h[6] and "合計" in h[7], h
    elif y <= 2019:    # どんこ・こうしん・山成・乾原木計・乾菌床・乾計・生原木・生菌床・生計
        c = {"dry_log": 4, "dry_bed": 5, "dry_total": 6, "fresh_log": 7, "fresh_bed": 8, "fresh_total": 9}
        assert "計" in h[4] and "菌床" in h[5] and "乾しいたけ計" in h[6] and "原木" in h[7] and "菌床" in h[8] and "計" in h[9], h
    else:              # (1)・乾計・乾原木小計・どんこ・こうしん・山成・乾菌床・生計・生原木・生菌床
        off = next(j for j, t in enumerate(h) if t.startswith("乾しいたけ"))
        c = {"dry_total": off, "dry_log": off + 1, "dry_bed": off + 5, "fresh_total": off + 6, "fresh_log": off + 7, "fresh_bed": off + 8}
        assert "計" in h[off] and "原木" in h[off + 1] and "菌床" in h[off + 5] and "生しいたけ" in h[off + 6] \
            and "原木" in h[off + 7] and "菌床" in h[off + 8], h
    return c


S, SP = [], []
for y in YEARS:
    r = rows(raw(y, "shiitake"))
    hs = next(i for i, x in enumerate(r) if any(clean(c) in ("都道府県", "県名") for c in x))
    he = next(i for i, x in enumerate(r) if i > hs and (pref_of(x[0]) or any(clean(c) in ("全国", "合計", "計") for c in x[:2])))
    h = header_text(r, he)
    c = shiitake_cols(y, h)
    n = nat_row(r)
    S.append({"year": y, **{k: num(n[j]) for k, j in c.items()}})
    for x in r[he:]:
        p = pref_of(x[0]) or (pref_of(x[1]) if len(x) > 1 else None)
        if p:
            SP.append({"year": y, "pref": p, **{k: num(x[j]) for k, j in c.items()}})
S = pd.DataFrame(S)
SP = pd.DataFrame(SP)
assert SP.groupby("year").pref.nunique().eq(47).all(), SP.groupby("year").pref.nunique()

# ---- 生産者数（原木・菌床） ----
P = []
for y in YEARS:
    r = rows(raw(y, "producers"))
    n = nat_row(r)
    v = [num(c) for c in n if isinstance(c, (int, float)) or clean(c) not in ("", "全国", "合計", "計", "(1)")]
    hs = next(i for i, x in enumerate(r) if any(clean(c) in ("都道府県", "県名") for c in x))
    hdr = " ".join(clean(c) for x in r[hs - 2:hs + 3] for c in x if clean(c))
    if y <= 2019:      # 原木乾・原木生・原木計・菌床生・合計
        assert len(v) == 5 and abs(v[0] + v[1] - v[2]) < 0.5 and abs(v[2] + v[3] - v[4]) < 0.5, (y, v)
        P.append({"year": y, "log_dry": v[0], "log_fresh": v[1], "log_total": v[2], "bed_total": v[3], "total": v[4]})
    else:              # 計・原木小計・原木乾・原木生・菌床（2023年からは 小計・乾・生）
        assert abs(v[1] + v[4] - v[0]) < 0.5 and abs(v[2] + v[3] - v[1]) < 0.5, (y, v)
        P.append({"year": y, "log_dry": v[2], "log_fresh": v[3], "log_total": v[1], "bed_total": v[4], "total": v[0]})
P = pd.DataFrame(P)

# ---- きのこ類の生産量（品目別、全国） ----
ITEMS = ["生しいたけ", "なめこ", "えのきたけ", "ひらたけ", "ぶなしめじ", "まいたけ", "エリンギ", "まつたけ"]
K = []
for y in YEARS:
    r = rows(raw(y, "kinoko"))
    hs = next(i for i, x in enumerate(r) if any(clean(c) in ("都道府県", "県名") for c in x))
    he = next(i for i, x in enumerate(r) if i > hs and (pref_of(x[0]) or any(clean(c) in ("全国", "合計", "計") for c in x[:2])))
    w = max(len(x) for x in r[: he + 1])
    hd = [[clean(r[i][j]) if j < len(r[i]) else "" for j in range(w)] for i in range(hs - 1, he)]
    n = nat_row(r)
    rec = {"year": y}
    for it in ITEMS:
        js = [j for j in range(w) if any(row[j] == it for row in hd)]
        rec[it] = num(n[js[0]])
    # 乾しいたけ：重さ（1つ目）と生換算値（2つ目）
    js = [j for j in range(w) if any(row[j].startswith("乾しいたけ") and "計" not in row[j] for row in hd)]
    rec["乾しいたけ"], rec["乾しいたけ_生換算"] = num(n[js[0]]), num(n[js[1]])
    vals = [num(c) for c in n]
    rec["きのこ類総計"] = max(v for v in vals if v == v)
    jt = [j for j in range(w) if any("総計" in row[j] for row in hd)]
    assert abs(num(n[jt[-1]]) - rec["きのこ類総計"]) < 0.5 if jt else True, (y, jt)
    K.append(rec)
K = pd.DataFrame(K)

# ---- 需給総括表（しいたけの生産・輸入・輸出） ----
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}


def era_year(s):
    s = clean(s)
    m = re.match(r"(昭和|平成|令和)(元|\d+)年?", s)
    return ERA[m.group(1)] + (1 if m.group(2) == "元" else int(m.group(2))) if m else None


B = []
for y in (2007, 2010, 2013, 2016, 2019, 2022, 2025):
    r = rows(raw(y, "balance"))
    hy = next(x for x in r if sum(1 for c in x if era_year(c)) >= 4)
    ycols = [(j, era_year(c)) for j, c in enumerate(hy) if era_year(c)]
    ycols = [(j, yy) for j, yy in ycols if yy >= 2005]
    assert len(ycols) == 3, ycols
    for it in ("乾しいたけ", "生しいたけ"):
        x = next(x for x in r if any(clean(c) == it for c in x[:3]))
        for j, yy in ycols:
            B.append({"year": yy, "item": it, "production": num(x[j]), "imports": num(x[j + 1]),
                      "exports": num(x[j + 2]), "consumption": num(x[j + 3]), "table_year": y})
B = pd.DataFrame(B).sort_values(["item", "year"]).reset_index(drop=True)
assert B.groupby("item").year.apply(lambda s: sorted(s) == YEARS).all()

# ---- 原木伏込量・菌床数（1970〜2025年、2025年版の表） ----
r = rows(raw(2025, "logs_beds"))
L, era = [], None
for x in r:
    if len(x) < 12:
        continue
    a = clean(x[1])
    m = re.match(r"(昭和|平成|令和)(元|\d+)", a)
    if m:
        era = m.group(1); k = 1 if m.group(2) == "元" else int(m.group(2))
    elif isinstance(x[1], (int, float)) and era:
        k = int(x[1])
    else:
        continue
    vals = x[5:12]  # 計（本数・材積）、乾（本数・材積）、生（本数・材積）、菌床数
    L.append({"year": ERA[era] + k, "logs_total_thousand": num(vals[0]), "logs_dry_thousand": num(vals[2]),
              "logs_fresh_thousand": num(vals[4]), "beds_thousand": num(vals[6])})
L = pd.DataFrame(L)
assert L.year.is_monotonic_increasing and L.year.max() == 2025

S.to_csv(D / "shiitake_national.csv", index=False, float_format="%.1f")
SP.to_csv(D / "shiitake_pref.csv", index=False, float_format="%.1f")
P.to_csv(D / "producers_national.csv", index=False, float_format="%.0f")
K.to_csv(D / "kinoko_national.csv", index=False, float_format="%.1f")
B.to_csv(D / "balance_shiitake.csv", index=False, float_format="%.0f")
L.to_csv(D / "logs_beds.csv", index=False, float_format="%.0f")
print(S.round(1).to_string()); print(P.to_string()); print(K.round(0).to_string()); print(B.head(6)); print(L.tail(4))
