"""PDF（data/raw）から表を読み取り、data/ の CSV に書く。pdftotext（poppler-utils）を使う。
ネットにはつながない。run_all.sh からは呼ばない（読み取った CSV を同梱しているので、02 以降はこの CSV から流れる）。
表の値は、行の位置ではなく、見出しの文字（国名・都道府県名・「YYYY年」）で読み取る。"""
import pathlib, re, subprocess, csv

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "data"
YEARS = range(2014, 2026)
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良",
         "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分",
         "宮崎", "鹿児島", "沖縄"]
NAME_FIX = {"アメリカ": "アメリカ合衆国", "イギリス": "英国"}


def text(pdf):
    r = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, check=True)
    return r.stdout.decode("utf-8").splitlines()


def num(s):
    return int(s.replace(",", ""))


def section(lines, start_pat, after=0, last=False):
    """見出し（目次の行は除く）から「内は」の行までを返す。"""
    idx = [i for i, l in enumerate(lines) if re.search(start_pat, l) and "…" not in l and "...." not in l and i >= after]
    if not idx:
        raise ValueError(start_pat)
    s = idx[-1] if last else idx[0]
    e = next(i for i in range(s + 1, len(lines)) if "内は" in lines[i] or re.match(r"^\s*計\s+[\d,]+人\s+100", lines[i]))
    return s, lines[s:e + 1]


def country_pairs(block):
    """「国名 人数人 (前年)」の組を読む（1行に2組まで）。"""
    out = []
    for l in block:
        for m in re.finditer(r"([^\s\d(（)）%％,]+)\s+([\d,]+)人\s*\(([\d,]+)\)", l):
            name = NAME_FIX.get(m.group(1), m.group(1))
            out.append((name, num(m.group(2)), num(m.group(3))))
    return out


def jls_rows(block):
    out = []
    for l in block:
        m = re.match(r"^\s*([^\s\d]+)\s+([\d,]+)人\s+[\d.]+％", l)
        if m:
            out.append((NAME_FIX.get(m.group(1), m.group(1)), num(m.group(2))))
    return out


def pref_rows(block):
    out = {}
    for p in PREFS:
        pat = r"\s?".join(p) + r"\s+([\d,]+)\s+\(([\d,]+)\)"
        ms = [m for l in block for m in re.finditer(pat, l)]
        if len(ms) != 1:
            raise ValueError(f"{p}: {len(ms)}")
        out[p] = (num(ms[0].group(1)), num(ms[0].group(2)))
    return out


rows_all, rows_he, rows_jls, rows_pref = [], [], [], []
for y in YEARS:
    L = text(RAW / f"jasso_{y}.pdf")
    # 1) 高等教育機関＋日本語教育機関の国別
    s1, b = section(L, r"^\s*(４．|１-５ )出身国（地域）別留学生数")
    for name, cur, prev in country_pairs(b):
        rows_all.append({"survey_year": y, "country": name, "n": cur, "n_prev": prev})
    # 2) 高等教育機関の国別（（１）または (1) の表）
    s2, b = section(L, r"^\s*(（１）|\(1\) )出身国（地域）別留学生数", after=s1 + 5)
    for name, cur, prev in country_pairs(b):
        rows_he.append({"survey_year": y, "country": name, "n": cur, "n_prev": prev})
    # 3) 日本語教育機関の国別（最後に出てくる国別の表）
    s3, b = section(L, r"^\s*(２．|３-２ )出身国（地域）別留学生数", after=s2 + 5, last=True)
    for name, cur in jls_rows(b):
        rows_jls.append({"survey_year": y, "country": name, "n": cur})
    # 4) 地方別・都道府県別（高等教育機関＋日本語教育機関、事務局本部の所在地での集計）
    s4, b = section(L, r"^\s*(８．|１-９ )地方別・都道府県別留学生数")
    for p, (cur, prev) in pref_rows(b).items():
        rows_pref.append({"survey_year": y, "basis": "本部", "pref": p, "n": cur, "n_prev": prev})
    if y >= 2022:
        s5, b = section(L, r"^\s*\(2\)\s*留学生が学んでいる校舎所在地", after=s4)
        for p, (cur, prev) in pref_rows(b).items():
            rows_pref.append({"survey_year": y, "basis": "校舎", "pref": p, "n": cur, "n_prev": prev})

# 5) 在学段階別の推移（1983〜2025年）
L = text(RAW / "jasso_2025_suii_stage.pdf")
stage = {}
for l in L:
    for m in re.finditer(r"(\d{4})年((?:\s+[\d,]+人)+)", l):
        vals = [num(v) for v in re.findall(r"([\d,]+)人", m.group(2))]
        stage.setdefault(int(m.group(1)), vals)
rows_stage = []
for y in sorted(stage):
    v = stage[y]
    r = {"year": y, "total": v[0], "grad": v[1], "ug_jc_tech": v[2], "senshu": v[3],
         "prep": v[4] if len(v) > 4 else 0, "jls": v[5] if len(v) > 5 else None}
    rows_stage.append(r)


def write(name, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


write("extract_country_all.csv", rows_all)
write("extract_country_he.csv", rows_he)
write("extract_country_jls.csv", rows_jls)
write("extract_pref.csv", rows_pref)
write("extract_stage.csv", rows_stage)
print(len(rows_all), len(rows_he), len(rows_jls), len(rows_pref), len(rows_stage))
