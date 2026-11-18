"""学校基本調査の Excel から、年度×大学科の生徒数（全国）と、都道府県×大学科の生徒数（2010・2025年度）を作る。
大学科の名前は、行・列の見出しの文字で付ける（行の位置では付けない）。照合の結果は data/build_checks.json に書く。"""
import json, re
import pandas as pd
from common import ROOT, sheet_rows, label_and_first, isnum

D = ROOT / "data"
YEARS = [1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025]
GROUPS = ["普通", "農業", "工業", "商業", "水産", "家庭", "看護", "情報", "福祉", "その他専門", "総合学科"]
VOC = ["農業", "工業", "商業", "水産", "家庭", "看護", "情報", "福祉"]


def group_of(L):
    """大学科の「計」の行なら大学科の名前、そうでなければ None。"""
    if L in ("普通科",) or (L.startswith("普通") and L.endswith("計")):
        return "普通"
    if L.startswith("総合学科"):
        return "総合学科"
    if L in ("その他の学科", "その他の学科計", "専門その他計"):
        return "その他専門"
    for g in ["農業", "工業", "商業", "水産", "家庭", "看護", "情報", "福祉"]:
        if L in (f"{g}に関する学科", f"{g}に関する学科計", f"専門{g}計"):
            return g
    return None


def ext(y):
    return "xlsx" if y >= 2015 else "xls"


chk = {}
nat = []
for y in YEARS:
    rows = sheet_rows(f"gakko_{y}_shogakka.{ext(y)}")
    total, vals, pending = None, {}, None
    for r in rows:
        L, v = label_and_first(r)
        if v is None:
            continue
        if total is None and L.startswith("計"):
            total = v
            continue
        if L == "計":           # 計の行が大学科の名前の行より前にある形（1985年度の商業）
            pending, wait = v, 3
            continue
        g = group_of(L)
        if g is None and pending is not None:
            g2 = next((k for k in VOC if L.startswith(f"{k}に関する学科")), None)
            if g2 and g2 not in vals:
                vals[g2] = pending
                pending = None
            else:
                wait -= 1
                if wait == 0:
                    pending = None
            continue
        pending = None
        if g is None:
            continue
        vals[g] = vals.get(g, 0) + v if g == "普通" else v
    rec = {"year": y, "total": int(total), **{g: int(vals.get(g, 0)) for g in GROUPS}}
    rec["sum_check"] = sum(rec[g] for g in GROUPS) - rec["total"]
    nat.append(rec)
nat = pd.DataFrame(nat).set_index("year")
chk["groups_sum_eq_total_all_years"] = bool((nat.sum_check == 0).all())
chk["groups_sum_diff_by_year"] = {int(y): int(v) for y, v in nat.sum_check.items()}
nat.drop(columns="sum_check").to_csv(D / "national_by_course.csv")

# 文部科学省のページの構成比（照合用）
html = (D / "raw" / "mext_gakka_page.html").read_text(encoding="utf-8", errors="replace")
txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", html))
era = {"昭和": 1925, "平成": 1988, "令和": 2018}
ref = []
for m in re.finditer(r"(昭和|平成|令和)(元|\d+)年 \|[ |]*([\d.]+) \|[ |]*([\d.]+) \|[ |]*([\d.]+) \|[ |]*([\d.\-]+) \|", txt):
    yy = era[m.group(1)] + (1 if m.group(2) == "元" else int(m.group(2)))
    ref.append({"year": yy, "general": float(m.group(3)), "vocational": float(m.group(4)), "other_special": float(m.group(5)),
                "integrated": None if m.group(6) == "-" else float(m.group(6))})
ref = pd.DataFrame(ref).drop_duplicates("year").set_index("year")
ref.to_csv(D / "mext_share_table.csv")
chk["mext_share_rows"] = int(len(ref))

# 都道府県別（2010・2025年度）
PREF = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都",
        "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府",
        "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県",
        "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
COLKEY = {"計": "total", "普通科": "普通", "普通": "普通", "農業に関する学科": "農業", "工業に関する学科": "工業", "商業に関する学科": "商業",
          "水産に関する学科": "水産", "家庭に関する学科": "家庭", "看護に関する学科": "看護", "情報に関する学科": "情報",
          "福祉に関する学科": "福祉", "その他の専門教育を施す学科": "その他専門", "総合学科": "総合学科"}


def pref_block(rows, start):
    """start 行より後の最初の見出し行（A列が「区分」）から、都道府県×大学科の「計」の列を読む。
    見出しは2〜3段。各段の空きは左の値で埋め、下の段が「計」の列だけを使う。"""
    h = next(i for i in range(start, len(rows)) if str(rows[i][0]).strip() == "区分")
    hs, k = [], h
    while k < len(rows) and str(rows[k][0]).strip() in ("区分", "", "None"):
        hs.append(rows[k]); k += 1
    ncol = max(len(r) for r in hs)
    filled = []
    for r in hs:
        cur, line = None, []
        for j in range(ncol):
            v = r[j] if j < len(r) else None
            if v not in (None, ""):
                cur = re.sub(r"\s+", "", str(v))
            line.append(cur)
        filled.append(line)
    data = {}
    for r in rows[k:k + 60]:
        name = str(r[0]).strip() if r[0] is not None else ""
        if name not in PREF or name in data:
            continue
        rec = {}
        for j in range(1, ncol):
            parts = [f[j] for f in filled if f[j]]
            if len(parts) < 2 or parts[-1] != "計":
                continue
            if parts[0] == "普通":
                key = "普通"
            elif parts[0] == "専門":   # 2025年度の形：専門｜農業｜計
                key = "その他専門" if parts[1] == "その他" else parts[1]
            else:                       # 2010年度の形：農業に関する学科｜計
                key = next((COLKEY[p] for p in parts[:-1][::-1] if p in COLKEY), None)
            if key is None:
                continue
            v = r[j]
            v = float(v) if isnum(v) else 0.0 if v in (None, "", "-", "－") else float(str(v).replace(",", ""))
            if key == "普通":
                # 2022年度以降は普通教育を主とする学科が4つ（普通・学際領域・地域社会・その他）に分かれるので足す
                if (key, parts[-2]) in rec:
                    continue
                rec[(key, parts[-2])] = v
            elif key not in rec:
                rec[key] = v
        flat = {}
        for kk, v in rec.items():
            g = kk[0] if isinstance(kk, tuple) else kk
            flat[g] = flat.get(g, 0) + v
        data[name] = flat
    return pd.DataFrame(data).T.reindex(PREF)


r10 = sheet_rows("gakko_2010_pref_gakka.xls")
blocks = {re.sub(r"\s+", "", str(r[0])): i for i, r in enumerate(r10) if isinstance(r[0], str) and re.sub(r"\s+", "", r[0]) in ("計国立", "計公立", "計私立")}
p10 = sum(pref_block(r10, blocks[b]).fillna(0) for b in ["計国立", "計公立", "計私立"])
r25 = sheet_rows("gakko_2025_pref_gakka.xlsx", 0)
chk["pref2025_sheet_title"] = [str(c) for r in r25[:4] for c in r if c][:2]
p25 = pref_block(r25, 0).fillna(0)
out = []
for y, p in [(2010, p10), (2025, p25)]:
    p = p.reindex(columns=["total"] + GROUPS).fillna(0)
    chk[f"pref{y}_groups_sum_eq_total"] = bool(((p[GROUPS].sum(axis=1) - p.total).abs() < 0.5).all())
    chk[f"pref{y}_sum_eq_national"] = {g: [int(p[g].sum()), int(nat.loc[y, g])] for g in ["total"] + GROUPS if int(p[g].sum()) != int(nat.loc[y, g])}
    q = p.astype(int).reset_index().rename(columns={"index": "pref"})
    q.insert(0, "year", y)
    out.append(q)
pd.concat(out).to_csv(D / "pref_by_course.csv", index=False)
json.dump(chk, open(D / "build_checks.json", "w"), ensure_ascii=False, indent=1)
print(nat)
print(json.dumps(chk, ensure_ascii=False))
assert chk["groups_sum_eq_total_all_years"] and chk["pref2010_groups_sum_eq_total"] and chk["pref2025_groups_sum_eq_total"]
assert not chk["pref2010_sum_eq_national"] and not chk["pref2025_sum_eq_national"]
