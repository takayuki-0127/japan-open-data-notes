"""F269 02 整形：フォローアップ調査のテキストから表を起こす。

出力（data/processed/）
- industry_passthrough.csv : 回×業種（発注企業の業種）の転嫁率（コスト全般・原材料費・エネルギー費・労務費）
- industry_negotiation.csv : 回×業種の価格交渉の平均点（2024年3月〜2026年3月）
- tier.csv                 : 回×取引段階（1次〜4次以上）の回答分布と転嫁率
- tankan.csv               : 短観の販売価格DI・仕入価格DI（四半期、規模×業種）
業種名は回によって表記が少し違うので、そろえてから保存する（NAME_MAP）。
"""
import json, os, re, unicodedata
import pandas as pd
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw"); OUT = os.path.join(BASE, "data", "processed")
os.makedirs(OUT, exist_ok=True)

def pages(r):
    t = open(os.path.join(RAW, "txt", f"fu_{r}.txt"), encoding="utf-8").read()
    t = unicodedata.normalize("NFKC", t)
    return t.split("\f")

def find_page(pg, key):
    for i, p in enumerate(pg):
        head = " ".join(l.strip() for l in p.split("\n") if l.strip())[:80]
        if key in head:
            return i
    raise KeyError(key)

NAME_MAP = {"不動産・物品賃貸": "不動産業・物品賃貸業", "不動産業・物品賃貸": "不動産業・物品賃貸業",
            "運輸・郵便(トラック運送業除く)": "運輸・郵便(トラック運送除く)",
            "機械製造業": "機械製造", "食品製造業": "食品製造"}
def norm(n):
    n = re.sub(r"\s+", "", n)
    n = re.sub(r"^\d+位", "", n)  # 「②業種別」の②（NFKC で 2）と順位がつながった行
    return NAME_MAP.get(n, n)

AR = r"[↑↓→ー]*"
NUM = r"(\d+\.\d)%"
rows = []
# --- 2023年3月・9月（202309 の業種別の比較の表：左が3月、右が9月）
pg = pages("202309"); p = pg[find_page(pg, "価格転嫁 業種別")]
pat = re.compile(r"(?:(\d+)位|1(?=全体))\s*([^\d↑↓→%\s][^\d↑↓→%]*?)\s+" + AR + NUM + r"\s+" + AR + NUM + r"\s+" + AR + NUM + r"\s+" + AR + NUM)
for line in p.split("\n"):
    ms = list(pat.finditer(line))
    for k, m in enumerate(ms):
        rnd = "2023-03" if (len(ms) == 2 and k == 0) or (len(ms) == 1 and m.start() < 40) else "2023-09"
        name = norm(m.group(2))
        rows.append(dict(round=rnd, industry=name, total=float(m.group(3)), material=float(m.group(4)),
                         energy=float(m.group(5)), labor=float(m.group(6))))
# 「その他」の行は 45.0％ のように全角％なので NFKC 後も拾われる → 業種の比較では除く
# --- 2024年9月〜2026年3月（転嫁の業種別ランキング：今回と（前回））
pat2 = re.compile(r"^\s*(?:(\d+)位\s+|ー\s+|1(?=全体))?(.+?)\s+" + AR + r"\s*" + NUM + r"\s*(?:\((\d+\.\d)%\)|ー)\s+" + AR + r"\s*" + NUM + r"\s*(?:\((\d+\.\d)%\)|ー)\s+" + AR + r"\s*" + NUM + r"\s*(?:\((\d+\.\d)%\)|ー)\s+" + AR + r"\s*" + NUM + r"\s*(?:\((\d+\.\d)%\)|ー)")
PREV = {"202409": "2024-03", "202503": "2024-09", "202509": "2025-03", "202603": "2025-09"}
CUR = {"202409": "2024-09", "202503": "2025-03", "202509": "2025-09", "202603": "2026-03"}
for r in ["202409", "202503", "202509", "202603"]:
    pg = pages(r); p = pg[find_page(pg, "価格転嫁の実施状況の業種別ランキング 【発注企業")]
    n = 0
    for line in p.split("\n"):
        line2 = re.sub(r"^\s*[業種別]\s+", " ", line)
        m = pat2.search(line2)
        if not m:
            continue
        name = norm(m.group(2)); n += 1
        if name == "その他":
            continue
        rows.append(dict(round=CUR[r], industry=name, total=float(m.group(3)), material=float(m.group(5)),
                         energy=float(m.group(7)), labor=float(m.group(9))))
        if r == "202409" and m.group(4):
            rows.append(dict(round=PREV[r], industry=name, total=float(m.group(4)), material=float(m.group(6)),
                             energy=float(m.group(8)), labor=float(m.group(10))))
    print(r, "industry rows", n)
ind = pd.DataFrame(rows)
ind = ind[ind.industry != "その他"].drop_duplicates(["round", "industry"])
ind.to_csv(os.path.join(OUT, "industry_passthrough.csv"), index=False)
print(ind.groupby("round").size())

# --- 価格交渉の平均点（発注企業の業種ごと。202409・202503 は「前回 今回」、202509・202603 は「今回 (前回)」の並び）
neg = []
ORDER = {"202409": "prev_cur", "202503": "prev_cur", "202509": "cur_prev", "202603": "cur_prev"}
for r in ["202409", "202503", "202509", "202603"]:
    pg = pages(r); p = pg[find_page(pg, "価格交渉の実施状況の業種別ランキング")]
    lines = [l[:60] for l in p.split("\n")]
    pending = None
    for line in lines:
        m = re.match(r"^\s*(?:(\d+)位\s+|ー\s+)?([^\d\s(ー•※][^\d]*?)\s*[↑↓→ー]*\s+(\d\.\d\d)\s+(?:\((\d\.\d\d)\)|(\d\.\d\d)|ー)?", line)
        m2 = re.match(r"^\s*(\d+)位\s+(\d\.\d\d)\s+(\d\.\d\d)", line)
        m3 = re.match(r"^\s+([^\d\s(•※][^\d\s]*?)[↑↓→]+\s", line)
        if m2:
            if not pending:
                continue
            name, a, b = pending, float(m2.group(2)), float(m2.group(3)); pending = None
        elif m:
            name = m.group(2); a = float(m.group(3)); b = m.group(4) or m.group(5); b = float(b) if b else None
        elif m3:
            pending = m3.group(1); continue
        else:
            continue
        name = norm(re.sub(r"[↑↓→]+$", "", name.strip()))
        if name == "その他":
            continue
        if ORDER[r] == "prev_cur":
            prev, cur = (a, b) if b is not None else (None, a)
        else:
            cur, prev = a, b
        if cur is not None:
            neg.append(dict(round=CUR[r], industry=name, score=cur, src=r))
        if prev is not None:
            neg.append(dict(round=PREV[r], industry=name, score=prev, src=r + "_prev"))
neg = pd.DataFrame(neg)
# 同じ回・業種が2つの版にあるときは、その回の版（src に _prev がつかない方）を使う
neg["is_prev"] = neg.src.str.endswith("_prev")
neg = neg.sort_values("is_prev").drop_duplicates(["round", "industry"]).drop(columns="is_prev").sort_values(["round", "industry"])
neg.to_csv(os.path.join(OUT, "industry_negotiation.csv"), index=False)
print(neg.groupby("round").size())

# --- 取引段階（1次〜4次以上）
tr = []
TIERS = ["1次請け", "2次請け", "3次請け", "4次請け以上"]
for r in ["202409", "202503", "202509", "202603"]:
    pg = pages(r); i = [k for k, p in enumerate(pg) if "受注側企業の取引段階と価格転嫁率" in p or ("1次請け" in p and "4次請け以上" in p and "転嫁率" in p)][-1]
    lines = pg[i].split("\n")
    for t in TIERS:
        k = next(j for j, l in enumerate(lines) if l.strip().startswith(t))
        vals = [float(x) for x in re.findall(r"(\d+\.\d)%", lines[k])]
        # マイナスの割合が次の行以降に1つだけ出る版がある
        if len(vals) == 6:
            dist, rate = vals[:5], vals[5]
            minus = None
            for l in lines[k + 1:k + 5]:
                mm = re.findall(r"^\s+(\d+\.\d)%\s*(?:▲|$)", l)
                if mm:
                    minus = float(mm[0]); break
        elif len(vals) == 7:
            dist, minus, rate = vals[:5], vals[5], vals[6]
        else:
            raise ValueError((r, t, vals))
        tr.append(dict(round=CUR[r], tier=t, full=dist[0], p7_9=dist[1], p4_6=dist[2], p1_3=dist[3], zero=dist[4],
                       minus=minus, rate=rate))
tr = pd.DataFrame(tr)
tr["dist_sum"] = tr[["full", "p7_9", "p4_6", "p1_3", "zero", "minus"]].sum(axis=1)
tr.to_csv(os.path.join(OUT, "tier.csv"), index=False)
print(tr)

# --- 短観
d = json.load(open(os.path.join(RAW, "boj_tankan_prices.json"), encoding="utf-8"))["RESULTSET"]
SIZE = {"00": "全規模", "01": "大企業", "02": "中堅企業", "03": "中小企業"}
IND = {"0": "全産業", "1": "製造業", "2": "非製造業"}
tk = []
for s in d:
    c = s["SERIES_CODE"]; item = "販売価格" if c[8:12] == "0614" else "仕入価格"
    for dt, v in zip(s["VALUES"]["SURVEY_DATES"], s["VALUES"]["VALUES"]):
        if v is None:
            continue
        y, q = int(str(dt)[:4]), int(str(dt)[4:])
        tk.append(dict(year=y, q=q, item=item, size=SIZE[c[15:17]], industry=IND[c[5]], di=v))
tk = pd.DataFrame(tk).sort_values(["item", "size", "industry", "year", "q"])
tk.to_csv(os.path.join(OUT, "tankan.csv"), index=False)
print(tk.groupby(["item", "size", "industry"]).size().head(), tk.year.max(), tk[tk.year == tk.year.max()].q.max())
