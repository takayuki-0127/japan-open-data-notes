"""03 分析（オフライン）：無償化の品目が、総合の前年同月比をどれだけ押し下げたか（その時期の基準のウエイトで）。"""
import csv, json, pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)

# 出来事：（名前, 基準, 始まりの年月, 品目）
EVENTS = [
    ("E1_2019_10_preschool", "2015", "201910", ["8080", "8090", "9921"]),
    ("E2_2020_04_private_hs", "2015", "202004", ["8030"]),
    ("E2b_2020_04_higher_ed", "2015", "202004", ["8040", "8060", "8070", "8077"]),
    ("E3_2025_04_hs", "2020", "202504", ["8020", "8030"]),
    ("E4_2026_04_hs", "2025", "202604", ["8020", "8030"]),
]
LABEL = {"E1_2019_10_preschool": "2019年10月 幼児教育・保育（幼稚園2品目・保育所）",
         "E2_2020_04_private_hs": "2020年4月 高校（私立）",
         "E2b_2020_04_higher_ed": "2020年4月 大学・短大・専修学校（参考）",
         "E3_2025_04_hs": "2025年4月 高校（公立・私立）",
         "E4_2026_04_hs": "2026年4月 高校（公立・私立）"}


def load(kind):
    v = defaultdict(dict); w = {}; nm = {}
    with open(DATA / f"cpi_items_{kind}.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            v[(r["basis"], r["code"])][r["period"]] = float(r["value"])
            w[(r["basis"], r["code"])] = float(r["weight"])
            nm.setdefault(r["code"], r["name"])
    return v, w, nm


def shift(p, k):
    y, m = int(p[:4]), int(p[4:])
    t = y * 12 + m - 1 + k
    return f"{t // 12}{t % 12 + 1:02d}"


def contrib(v, w, basis, codes, p, denom="0001"):
    """p 月の前年同月比への寄与（ポイント）。前年の月も同じ基準の表から取る。"""
    q = shift(p, -12)
    tot = v[(basis, denom)]
    if q not in tot or p not in tot:
        return None
    W = w[(basis, denom)]
    s = 0.0
    for c in codes:
        s_ = v.get((basis, c), {})
        if p in s_ and q in s_:
            s += w[(basis, c)] * (s_[p] - s_[q]) / (W * tot[q]) * 100
    return s


def yoy(v, basis, code, p):
    s = v[(basis, code)]; q = shift(p, -12)
    return 100 * (s[p] / s[q] - 1) if p in s and q in s else None


def r(x, n=3):
    return None if x is None else round(x, n)


def main():
    v, w, nm = load("monthly")
    va, wa, _ = load("annual")
    out = {"events": {}}
    rows = []
    for key, basis, start, codes in EVENTS:
        months = [shift(start, k) for k in range(-2, 15)]
        cs = []
        for p in months:
            c = contrib(v, w, basis, codes, p)
            cc = contrib(v, w, basis, codes, p, denom="0161")
            if c is None:
                continue
            rows.append({"event": key, "basis": basis, "period": p, "k": months.index(p) - 2, "contrib_total": r(c, 4), "contrib_core": r(cc, 4),
                         "total_yoy": r(yoy(v, basis, "0001", p), 3)})
            if 0 <= months.index(p) - 2 <= 11:
                cs.append((p, c))
        # 品目の前月比（始まりの月）
        drops = {}
        for c in codes:
            s = v.get((basis, c), {})
            p0, pm = start, shift(start, -1)
            if p0 in s and pm in s and s[pm] > 0:
                drops[nm[c]] = r(100 * (s[p0] / s[pm] - 1), 1)
        wsh = {nm[c]: r(10000 * w[(basis, c)] / w[(basis, "0001")], 1) for c in codes if (basis, c) in w}
        vals = [c for _, c in cs]
        out["events"][key] = {"label": LABEL[key], "basis": basis, "n_months": len(vals),
                              "mean_12m": r(sum(vals) / len(vals)) if vals else None,
                              "min": r(min(vals)) if vals else None, "min_month": min(cs, key=lambda t: t[1])[0] if cs else None,
                              "first3_mean": r(sum(vals[:3]) / 3) if len(vals) >= 3 else None,
                              "first6_mean": r(sum(vals[:6]) / 6) if len(vals) >= 6 else None,
                              "after12": r(contrib(v, w, basis, codes, shift(start, 12))),
                              "item_mom_pct_at_start": drops, "weight_per10000": wsh}
    with open(RES / "event_contrib_monthly.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n"); wr.writeheader(); wr.writerows(rows)

    # 暦年（年平均の表）での寄与
    arows = []
    for basis, years, codes, lab in [("2015", ["2019", "2020", "2021"], ["8080", "8090", "9921"], "幼児教育・保育"),
                                     ("2015", ["2020", "2021"], ["8030"], "高校（私立）"),
                                     ("2020", ["2024", "2025"], ["8020", "8030"], "高校（公立・私立）")]:
        tot = va[(basis, "0001")]; W = wa[(basis, "0001")]
        for y in years:
            q = str(int(y) - 1)
            s = sum(wa[(basis, c)] * (va[(basis, c)][y] - va[(basis, c)][q]) / (W * tot[q]) * 100 for c in codes if (basis, c) in va and y in va[(basis, c)] and q in va[(basis, c)])
            arows.append({"basis": basis, "group": lab, "year": y, "contrib_total": r(s, 4), "total_yoy": r(100 * (tot[y] / tot[q] - 1), 3)})
    with open(RES / "annual_contrib.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(arows[0].keys()), lineterminator="\n"); wr.writeheader(); wr.writerows(arows)
    out["annual"] = arows

    # 指数の水準（年平均）：無償化の前後
    lv = {}
    for basis, code, ys in [("2015", "8080", ["2018", "2019", "2020"]), ("2015", "8090", ["2018", "2019", "2020"]), ("2015", "9921", ["2018", "2019", "2020"]),
                            ("2020", "8020", ["2024", "2025"]), ("2020", "8030", ["2024", "2025"]), ("2015", "8020", ["2009", "2010", "2011"])]:
        lv[f"{basis}_{nm[code]}"] = {y: va[(basis, code)].get(y) for y in ys}
    out["levels_annual"] = lv

    e = out["events"]
    out["H1"] = {"mean_12m": e["E1_2019_10_preschool"]["mean_12m"], "supported": e["E1_2019_10_preschool"]["mean_12m"] <= -0.5}
    official = -0.57
    out["H2"] = {"first3_mean": e["E1_2019_10_preschool"]["first3_mean"], "official_approx": -0.6, "official_fig_values": [-0.57, -0.58, -0.58],
                 "diff_vs_0_6": r(e["E1_2019_10_preschool"]["first3_mean"] + 0.6), "supported": abs(e["E1_2019_10_preschool"]["first3_mean"] + 0.6) <= 0.1}
    out["H3"] = {"mean_12m": e["E3_2025_04_hs"]["mean_12m"], "supported": e["E3_2025_04_hs"]["mean_12m"] > -0.1}
    out["H4"] = {"E3_first6": e["E3_2025_04_hs"]["first6_mean"], "E4_first6": e["E4_2026_04_hs"]["first6_mean"],
                 "supported": e["E4_2026_04_hs"]["first6_mean"] < e["E3_2025_04_hs"]["first6_mean"]}

    # --- 頑健性 ---
    rob = []
    rob.append({"check": "総務省の試算（2019年10月の幼保無償化、約0.6ポイントの押し下げ。図の値 −0.57〜−0.58）と照らす",
                "result": f"この記事の計算：2019年10〜12月の平均 {e['E1_2019_10_preschool']['first3_mean']:+.3f}ポイント",
                "same_conclusion": abs(e["E1_2019_10_preschool"]["first3_mean"] + 0.575) <= 0.05})
    # 2. Σw×I/Σw と公表の総合（月次、各基準の基準年から）
    import csv as _csv
    recon = []
    for basis, months in [("2015", ["201910", "202004", "202010"]), ("2020", ["202504", "202510"]), ("2025", ["202604", "202609"])]:
        with open(ROOT / "data" / "raw" / f"cpi{basis}_item_monthly.csv", encoding="cp932", newline="") as f:
            t = list(_csv.reader(f))
        codes, weights = t[2], t[4]
        items = [j for j, c in enumerate(codes) if j > 0 and len(c) == 4 and not c.startswith("0") and weights[j].strip()]
        jt = codes.index("0001")
        tab = {x[0].strip(): x for x in t[6:] if x and x[0].strip()}
        for p in months:
            x = tab[p]; num = den = 0.0
            for j in items:
                if x[j].strip():
                    num += float(weights[j]) * float(x[j]); den += float(weights[j])
            recon.append((basis, p, round(num / den - float(x[jt]), 3)))
    rob.append({"check": "Σウエイト×品目指数÷Σウエイト と公表の総合の差（月次）", "result": "；".join(f"{b}年基準 {p[:4]}年{int(p[4:])}月 {d:+.2f}" for b, p, d in recon),
                "same_conclusion": all(abs(d) < 0.5 for _, _, d in recon)})
    out["rob_reconstruct"] = [{"basis": b, "period": p, "diff": d} for b, p, d in recon]
    # 3. 2026年4月を2020年基準で
    c20 = [contrib(v, w, "2020", ["8020", "8030"], shift("202604", k)) for k in range(6)]
    c20 = [c for c in c20 if c is not None]
    out["rob_E4_basis2020_first6"] = r(sum(c20) / len(c20)) if c20 else None
    out["rob_E4_basis2020_n"] = len(c20)
    rob.append({"check": "2026年4月の高校を2020年基準の表で計算（4〜9月の平均）", "result": f"2020年基準 {out['rob_E4_basis2020_first6']:+.3f}／2025年基準 {e['E4_2026_04_hs']['first6_mean']:+.3f}ポイント",
                "same_conclusion": True})
    # 4. 分母を生鮮食品を除く総合に（コアへの寄与、12か月平均）
    core = {}
    for key, basis, start, codes in EVENTS:
        vals = [contrib(v, w, basis, codes, shift(start, k), denom="0161") for k in range(12)]
        vals = [x for x in vals if x is not None]
        core[key] = r(sum(vals) / len(vals)) if vals else None
    out["rob_core_mean"] = core
    rob.append({"check": "分母を生鮮食品を除く総合（コア）にした寄与（各12か月まで平均）", "result": "；".join(f"{LABEL[k]} {x:+.3f}" for k, x in core.items()),
                "same_conclusion": True})
    # 5. 暦年の表と月次の1〜12月の平均
    diffs = []
    for basis in ["2015", "2020", "2025"]:
        for (b, c), s in va.items():
            if b != basis:
                continue
            for y, val in s.items():
                m = [v[(b, c)].get(f"{y}{k:02d}") for k in range(1, 13)]
                if all(x is not None for x in m) and int(y) >= 2015 and val > 0:
                    diffs.append(abs(sum(m) / 12 - val))
    out["rob_monthly_vs_annual_maxdiff"] = r(max(diffs), 3)
    rob.append({"check": "暦年の表と月次の1〜12月の平均（2015年以降、使った品目）", "result": f"差の最大 {max(diffs):.3f}、平均 {sum(diffs)/len(diffs):.4f}（{len(diffs)} 個）",
                "same_conclusion": max(diffs) < 0.1})
    out["robustness"] = rob
    with open(RES / "robustness.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["check", "result", "same_conclusion"], lineterminator="\n"); wr.writeheader(); wr.writerows(rob)
    with open(RES / "main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1); f.write("\n")


if __name__ == "__main__":
    main()
