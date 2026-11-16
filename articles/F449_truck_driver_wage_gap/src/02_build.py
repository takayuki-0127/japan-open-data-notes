"""data/raw の Excel から、運転者と産業計の年齢階級別の数字を取り出して data/wage_long.csv にする。"""
import gzip, io, pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
COLS = ["age", "tenure", "hours_sched", "hours_ot", "kimatte", "shoteinai", "bonus", "workers"]
AGES = ["～19歳", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳", "50～54歳",
        "55～59歳", "60～64歳", "65～69歳", "70歳～"]


AGESN = {re.sub(r"[\s\u3000]", "", unicodedata.normalize("NFKC", a)): a for a in AGES}


def read(path):
    if path.name.endswith(".gz"):
        return pd.read_excel(io.BytesIO(gzip.open(path).read()), header=None, sheet_name=None, engine="xlrd")
    return pd.read_excel(path, header=None, sheet_name=None, engine="openpyxl")


def norm(s):
    s = unicodedata.normalize("NFKC", str(s))
    return re.sub(r"[\s　]", "", s)


def rows(df):
    """各行を（ラベル, 数字8つ）にする。ラベルは最後の文字のセル、数字はその右の最初の8つ。"""
    out = []
    for r in df.itertuples(index=False):
        vals = list(r)
        li = None
        for i, v in enumerate(vals):
            if isinstance(v, str) and norm(v) and not re.fullmatch(r"[A-Z0-9]+|[-‐－−…*※χX.]+", norm(v)):
                li = i
        if li is None:
            continue
        nums = []
        for v in vals[li + 1:]:
            if isinstance(v, (int, float)) and not pd.isna(v):
                nums.append(float(v))
            elif isinstance(v, str) and re.fullmatch(r"-?[\d.]+", v.strip()):
                nums.append(float(v))
            if len(nums) == 8:
                break
        out.append((norm(vals[li]), nums))
    return out


def block(rs, start_pat, nth=0):
    """start_pat に合う行（nth 番目）と、その下に続く年齢階級の行を返す。"""
    hits = [i for i, (lab, n) in enumerate(rs) if re.search(start_pat, lab) and len(n) == 8]
    if len(hits) <= nth:
        raise ValueError(f"not found: {start_pat}")
    i = hits[nth]
    res = {"計": rs[i][1]}
    for lab, n in rs[i + 1:]:
        if lab in AGESN and len(n) == 8:
            res[AGESN[lab]] = n
        elif lab not in AGESN:
            break
    return res


def to_records(year, who, blk):
    recs = []
    for a, n in blk.items():
        d = dict(zip(COLS, n)); d.update(year=year, who=who, age_class=a)
        recs.append(d)
    return recs


def main():
    recs = []
    for y in range(2009, 2026):
        ind = read(next(RAW.glob(f"wage_{y}_ind1.*")))
        rs = rows(list(ind.values())[0])  # 最初のシートが産業計
        recs += to_records(y, "all_total", block(rs, r"^男女計学歴計$"))
        recs += to_records(y, "all_male", block(rs, r"^男学歴計$"))
        if y <= 2019:
            occ = read(next(RAW.glob(f"wage_{y}_occ2.*")))
            rs = sum((rows(s) for s in occ.values()), [])
            recs += to_records(y, "large_male", block(rs, r"^営業用大型貨物自動車運転者\(男\)$"))
            recs += to_records(y, "other_male", block(rs, r"^営業用普通・小型貨物自動車運転者\(男\)$"))
        else:
            o5 = read(next(RAW.glob(f"wage_{y}_occ5.*")))
            rs = sum((rows(s) for s in o5.values()), [])
            recs += to_records(y, "large_total", block(rs, r"^営業用大型貨物自動車運転者$"))
            recs += to_records(y, "other_total", block(rs, r"^営業用貨物自動車運転者\(大型車を除く\)$"))
            o1 = read(next(RAW.glob(f"wage_{y}_occ1.*")))
            rs = sum((rows(s) for s in o1.values()), [])
            # 第1表は 男女計・男・女 の順に同じ職種が3回出る。2回目が男
            for key, pat in [("large_male", r"^営業用大型貨物自動車運転者$"), ("other_male", r"^営業用貨物自動車運転者\(大型車を除く\)$")]:
                recs += to_records(y, key, {"計": block(rs, pat, nth=1)["計"]})
    df = pd.DataFrame(recs)[["year", "who", "age_class"] + COLS]
    # 確かめ：年齢階級が揃っているか
    chk = df[df.age_class != "計"].groupby(["year", "who"]).size()
    assert chk.min() >= 10, chk[chk < 10]
    df.to_csv(ROOT / "data" / "wage_long.csv", index=False, float_format="%.4f")
    print(df[df.age_class == "計"].pivot(index="year", columns="who", values="shoteinai"))


if __name__ == "__main__":
    main()
