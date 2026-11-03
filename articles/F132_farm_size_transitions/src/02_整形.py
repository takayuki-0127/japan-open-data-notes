"""02 整形：農林業センサス 構造動態編の「経営耕地面積規模別経営体数の相関表」を、
期間 × 地域 × 前回の規模 × 今回の規模（退出・接続不可を含む）の長い表にする。

出力
- data/transitions_long.csv : period, area, level(全国/地方/都道府県), from, to, n
    from = 前回の規模（または 'entry' = 前回は農業経営体以外, 'unlinked_in' = 接続不可（今回側））
    to   = 今回の規模（または 'exit' = 今回は農業経営体以外, 'unlinked_out' = 接続不可（前回側））
    ※ 2005→2010 は前回側の「退出」と「接続不可」が1列（継続農業経営体以外）なので to='exit_or_unlinked'
- data/stock_2020_2025.csv : 2025年センサス 総括編の規模別経営体数（2020・2025）
規模は元の区分のまま残し、03 で共通の区分にまとめる。
"""
import json, re, csv, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
d = json.load(open(ROOT / "data/raw/f132_census_transitions.json", encoding="utf-8"))


def num(x):
    x = x.replace(",", "").replace(" ", "").replace('"', "").strip()
    if x in ("", "-", "…"):
        return 0
    if x in ("x", "X", "△"):
        return None
    return int(float(x))


def rows(text):
    return list(csv.reader(text.splitlines()))


# 2015・2020（1期間前→今回）。区分：経営耕地なし, 0.3未満, 0.3-1.0, ..., 100以上
CL20 = ["none", "lt0.3", "0.3-1", "1-3", "3-5", "5-10", "10-20", "20-30", "30-50", "50-100", "100+"]
CL15 = ["none", "lt0.3", "0.3-1", "1-3", "3-5", "5-7.5", "7.5-10", "10-20", "20-30", "30-40", "40-50", "50-100", "100+"]
REG = ["北海道", "都府県", "東北", "北陸", "関東・東山", "北関東", "南関東", "東山", "東海", "近畿", "中国", "山陰", "山陽", "四国", "九州", "北九州", "南九州", "沖縄"]

out = []


def parse_new(text, period, CL, skipcol=10):
    R = rows(text)
    K = len(CL)
    sec = None
    idx = 0
    seen = []
    i = 0
    while i < len(R):
        r = R[i]
        m = re.match(r"^\s*\((\d+)\)\s*(\S+)", r[0] if r else "")
        if m:
            sec = (int(m.group(1)), m.group(2))
            seen.append(sec)
            # 次の「継続」行を探す
            j = i + 1
            while not R[j][0].startswith("継続"):
                j += 1
            n0 = sec[0]
            area = sec[1]
            level = "全国" if n0 == 1 else ("地域" if n0 <= 19 else "都道府県")
            if area == "北海道" and n0 == 2:
                level = "地域"
            for a in range(K):
                v = [num(x) for x in R[j + a][skipcol: skipcol + K + 4]]
                for b in range(K):
                    out.append((period, area, level, CL[a], CL[b], v[b]))
                out.append((period, area, level, CL[a], "exit", v[K + 1]))
                out.append((period, area, level, CL[a], "unlinked_out", v[K + 2]))
            # 計の行 j+K, 退出側の行 j+K+1(entry), j+K+2(unlinked_in)
            for lab, off in (("entry", K + 1), ("unlinked_in", K + 2)):
                v = [num(x) for x in R[j + off][skipcol: skipcol + K]]
                for b in range(K):
                    out.append((period, area, level, lab, CL[b], v[b]))
            i = j + K + 3
        i += 1
    return seen


s20 = parse_new(d["2020_kei__001"], "2015-2020", CL20)
s15 = parse_new(d["2015_kei__001"], "2010-2015", CL15)
print("sections", len(s20), len(s15))

# 2005→2010：北海道・都府県・地域（全国の表はないので 北海道＋都府県 を全国とする）
CL10H = ["lt0.3", "0.3-1", "1-3", "3-5", "5-7.5", "7.5-10", "10-15", "15-20", "20-25", "25-30", "30-40", "40-50", "50+"]
CL10F = ["lt0.3", "0.3-0.5", "0.5-1", "1-1.5", "1.5-2", "2-2.5", "2.5-3", "3-4", "4-5", "5-7.5", "7.5-10", "10-15", "15+"]
R = rows(d["2010_kei__Ⅰ_1経営耕地経営体数"])
i = 0
names10 = []
while i < len(R):
    r = R[i]
    if r and r[0].strip() in REG and len(r) > 19 and "単位" in r[-1]:
        area = r[0].strip()
        names10.append(area)
        CL = CL10H if area == "北海道" else CL10F
        K = len(CL)
        j = i + 1
        while not R[j][0].startswith("継続"):
            j += 1
        for a in range(K):
            v = [num(x) for x in R[j + a][5: 5 + K + 3]]
            for b in range(K):
                out.append(("2005-2010", area, "地域", CL[a], CL[b], v[b]))
            out.append(("2005-2010", area, "地域", CL[a], "exit_or_unlinked", v[K + 1]))
        for lab, off in (("entry", K + 1), ("unlinked_in", K + 2)):
            v = [num(x) for x in R[j + off][5: 5 + K]]
            for b in range(K):
                out.append(("2005-2010", area, "地域", lab, CL[b], v[b]))
        i = j + K + 3
    i += 1
print("2010 sections", names10)

with open(ROOT / "data/transitions_long.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["period", "area", "level", "from", "to", "n"])
    w.writerows(out)

# 2025 総括編：規模別経営体数（2025・2020）
R = rows(d["2025_size__Ⅱ3"])
CL25 = ["total", "lt0.3", "0.3-0.5", "0.5-1", "1-1.5", "1.5-2", "2-3", "3-5", "5-10", "10-20", "20-30", "30-50", "50-100", "100-150", "150+", "none"]
st = []
for r in R:
    if len(r) > 35 and re.match(r"^\(\d+\)$", r[2].strip() or "x"):
        area = (r[0] or r[1]).strip()
        n0 = int(r[2].strip()[1:-1])
        v25 = [num(x) for x in r[3:19]]
        v20 = [num(x) for x in r[19:35]]
        for c, a, b in zip(CL25, v20, v25):
            st.append((n0, area, c, a, b))
with open(ROOT / "data/stock_2020_2025.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["no", "area", "class", "n2020", "n2025"])
    w.writerows(st)
print("stock rows", len(st))
