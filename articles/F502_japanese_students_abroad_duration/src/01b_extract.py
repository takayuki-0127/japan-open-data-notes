"""PDF（data/raw）から「地域別・留学期間別日本人留学生数」の表を読み取り、data/extract_region_period.csv に書く。
pdftotext（poppler-utils）を使う。ネットにはつながない。run_all.sh からは呼ばない
（読み取った CSV を同梱しているので、02 以降はこの CSV から流れる）。
表の値は、行の位置ではなく、行の見出し（地域名）と、表の前にある見出しの文字（協定あり・なし・合計）で読み取る。
括弧の中の数（前年度の値）は別の列（prev）に入れる。"""
import pathlib, re, subprocess, csv

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "data"
YEARS = range(2009, 2025)
# 表の見出しの言い方が年で違うので、同じ地域にそろえる
NAME = {  # 「不明」（地域の記入なし）は「無記入」にまとめる
"アジア": "アジア", "中東": "中東", "中近東": "中東", "アフリカ": "アフリカ", "大洋州": "大洋州", "オセアニア": "大洋州",
        "北米": "北米", "中南米": "中南米", "欧州": "欧州", "ヨーロッパ": "欧州", "その他": "その他", "無記入": "無記入", "不明": "無記入", "計": "計"}
P5 = ["m_lt1", "m1_3", "m3_6", "m6_12", "y1plus"]
P6 = P5 + ["unknown"]


def text(pdf):
    r = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, check=True)
    return r.stdout.decode("utf-8").splitlines()


def kind_of(lines, i):
    """表の見出しの前を遡り、いちばん近い「…留学状況」の行で、合計・協定あり・協定なしを決める。"""
    for l in reversed(lines[max(0, i - 40):i]):
        if "留学状況" not in l or "...." in l or "…" in l:
            continue
        if "合計" in l or "協定" not in l:
            return "total"
        if "基づかない" in l:
            return "nashi"
        return "ari"
    raise ValueError("見出しがない")


def parse_row(l):
    m = re.match(r"^\s*([^\d\s(（]+)\s+(.*)$", l)
    if not m or m.group(1) not in NAME:
        return None
    body = m.group(2)
    prev = [int(x.replace(",", "")) for x in re.findall(r"\(\s*([\d,]+)\s*\)", body)]
    cur = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", re.sub(r"\(\s*[\d,]+\s*\)", " ", body))]
    return NAME[m.group(1)], cur, prev


def main():
    rows = []
    for y in YEARS:
        lines = text(RAW / f"jasso_nippon_{y}.pdf")
        starts = [i for i, l in enumerate(lines) if re.search(r"地域別[・･]留学期間別", l) and "...." not in l and "…" not in l]
        seen = set()
        for s in starts:
            kind = kind_of(lines, s)
            if kind in seen:
                raise ValueError((y, kind))
            seen.add(kind)
            for l in lines[s + 1:s + 60]:
                r = parse_row(l)
                if r is None:
                    continue
                name, cur, prev = r
                cols = P6 if len(cur) == 7 else P5 if len(cur) == 6 else None
                if cols is None:
                    raise ValueError((y, kind, l))
                rec = {"year": y, "kind": kind, "region": name, **dict(zip(cols, cur[:-1])), "total": cur[-1]}
                if prev:
                    pc = P6 if len(prev) == 7 else P5
                    rec.update({f"prev_{k}": v for k, v in zip(pc, prev[:-1])})
                    rec["prev_total"] = prev[-1]
                rows.append(rec)
                if name == "計":
                    break
    keys = ["year", "kind", "region"] + P6 + ["total"] + [f"prev_{k}" for k in P6] + ["prev_total"]
    with open(OUT / "extract_region_period.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # 2024年度版の「日本人学生留学状況の推移」（協定あり・なし・合計）
    lines = text(RAW / "jasso_nippon_2024.pdf")
    s = [i for i, l in enumerate(lines) if "日本人学生留学状況の推移" in l and "...." not in l][0]
    out = []
    for l in lines[s:s + 40]:
        m = re.match(r"^\s*(\d{4})年度\s+([\d,]+)\s+([\d,]+|-)\s+([\d,]+)\s*$", l)
        if m:
            f = lambda v: None if v == "-" else int(v.replace(",", ""))
            out.append({"year": int(m.group(1)), "ari": f(m.group(2)), "nashi": f(m.group(3)), "total": f(m.group(4))})
    with open(OUT / "extract_series_2024.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["year", "ari", "nashi", "total"])
        w.writeheader()
        w.writerows(out)

    # 文部科学省の公表資料：海外の機関が把握する日本人留学者数（主に長期）の「合計」の行（その年と前年）
    long = []
    for fn, yr in [("mext_2024-05-24_release.pdf", 2021), ("mext_2025-04-30_release.pdf", 2022), ("mext_2026-05-29_release.pdf", 2023)]:
        lines = text(RAW / fn)
        s = [i for i, l in enumerate(lines) if re.search(r"海外の機関が把握", l)][0]
        hit = None
        for l in lines[s:]:
            m = re.match(r"^\s*合計\s+([\d,]+)\s+([\d,]+)\s+", l)
            if m:
                hit = (int(m.group(1).replace(",", "")), int(m.group(2).replace(",", "")))
                break
        long.append({"release": fn, "year": yr, "n": hit[0], "n_prev": hit[1]})
    with open(OUT / "extract_long_mext.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["release", "year", "n", "n_prev"])
        w.writeheader()
        w.writerows(long)
    print(len(rows), "rows;", len(out), "series;", long)


if __name__ == "__main__":
    main()
