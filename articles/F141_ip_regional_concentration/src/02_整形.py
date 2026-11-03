"""特許行政年次報告書（2010・2013・2016・2019・2022・2025年版）の都道府県別の表を、
年 × 都道府県 × 系列 の縦長の表にする。
入力: data/raw/jpo_nenji_pref_tables.json（01_取得 で集めた CSV 本文）
出力: data/pref_ip_long.csv
"""
import json, re, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFS = ["北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県",
 "埼玉県","千葉県","東京都","神奈川県","新潟県","富山県","石川県","福井県","山梨県","長野県",
 "岐阜県","静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県",
 "鳥取県","島根県","岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県",
 "佐賀県","長崎県","熊本県","大分県","宮崎県","鹿児島県","沖縄県"]
STEM = {p: (p if p == "北海道" else p[:-1]) for p in PREFS}

def pref_of(cell):
    s = re.sub(r"\s|　", "", cell)
    if not s:
        return None
    for p in PREFS:
        if s == p or s == STEM[p]:
            return p
    return None

def num(c):
    c = c.strip().replace(",", "").replace('"', "")
    if c == "" or c.endswith("%") or c in ("-", "－"):
        return None
    try:
        return float(c)
    except ValueError:
        return None

def years_of(text):
    for line in text.splitlines()[:6]:
        ys = [int(y) for y in re.findall(r"(20\d\d)年", line)]
        if ys:
            out = []
            for y in ys:
                if y not in out:
                    out.append(y)
            return out
    raise ValueError("no years")

def rows(text):
    return list(csv.reader(text.splitlines()))

SERIES_APP = ["特許出願", "実用新案出願", "意匠出願", "商標出願"]

def parse(ed, kind, idx, text):
    ys = years_of(text)
    newfmt = int(ed) >= 2022
    out = []
    for r in rows(text):
        p = None
        for j, c in enumerate(r[:2]):
            p = pref_of(c)
            if p:
                vals = r[j + 1:]
                break
        if not p:
            continue
        if newfmt:
            nums = [num(c) for c in vals]
            if kind == "app" and idx == 0:
                # 出願件数, 外国語書面 の組（出願件数が先）
                v = [nums[0], nums[2], nums[4]]
            else:
                v = [x for x in nums if x is not None][:3]
        else:
            nums = [num(c) for c in vals]
            if kind == "app" and idx == 0:
                # 外国語書面, 出願件数 の組（外国語書面が先）。空欄があるので位置で取る
                nn = [x for x in nums if x is not None]
                if len(nn) >= 6:
                    v = [nn[1], nn[3], nn[5]]
                else:
                    v = [nn[0], nn[2], nn[4]]
            else:
                v = [x for x in nums if x is not None][:3]
        if len(v) != 3:
            raise ValueError((ed, kind, idx, p, r))
        name = {"app": SERIES_APP[idx], "reg": "特許登録", "inv": "特許の発明者数"}[kind]
        for y, x in zip(ys, v):
            out.append((y, p, name, x, ed))
    got = {o[1] for o in out}
    assert len(got) == 47, (ed, kind, idx, len(got), set(PREFS) - got)
    return out

def main():
    d = json.loads((ROOT / "data/raw/jpo_nenji_pref_tables.json").read_text(encoding="utf-8"))
    recs = []
    for ed in sorted(d):
        for kind, lst in d[ed].items():
            for i, x in enumerate(lst):
                recs += parse(ed, kind, i, x["t"])
    with open(ROOT / "data/pref_ip_long.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "pref", "series", "count", "edition"])
        for r in sorted(recs):
            w.writerow([r[0], r[1], r[2], int(r[3]), r[4]])
    print(len(recs), "rows")

if __name__ == "__main__":
    main()
