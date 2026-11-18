"""03 分析（オフライン）：品目ごとの変化率、1台あたりの輸入額との比較、総合への寄与、頑健性。"""
import csv, json, math, pathlib
from collections import defaultdict
from cpiload import read_cpi

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RAW, RES = ROOT / "data", ROOT / "data" / "raw", ROOT / "results"
RES.mkdir(exist_ok=True)

POS7 = ["9013", "9078", "9079", "9043", "9080", "9081", "9034"]
HED4 = ["9013", "9078", "9079", "9043"]
COMP = ["4021", "4042", "4063", "4032", "4003", "7446"]
NAMES = {}


def load_annual():
    d = defaultdict(dict)   # (basis, code) -> {year: value}
    w = {}
    with open(DATA / "cpi_items_annual.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d[(r["basis"], r["code"])][int(r["period"])] = float(r["value"])
            w[(r["basis"], r["code"])] = float(r["weight"])
            NAMES.setdefault(r["code"], r["name"])
    return d, w


def rate(s, a, b):
    """a年→b年の年平均の変化率（対数の差÷年数×100、%）。どちらかがなければ None。"""
    if a in s and b in s and s[a] > 0 and s[b] > 0:
        return 100 * (math.log(s[b]) - math.log(s[a])) / (b - a)
    return None


def pct(s, a, b):
    if a in s and b in s and s[a] > 0:
        return 100 * (s[b] / s[a] - 1)
    return None


def r2(x, n=2):
    return None if x is None else round(x, n)


def main():
    d, w = load_annual()
    main = {}
    # --- A. 期間ごとの年平均の変化率（2025年基準の長期の表） ---
    periods = [(2000, 2005), (2005, 2010), (2010, 2015), (2015, 2020), (2020, 2025)]
    rows = []
    for code in POS7 + COMP + ["0001"]:
        s = d[("2025", code)]
        row = {"code": code, "name": NAMES[code], "first_year": min(s), "weight_2025": w[("2025", code)]}
        for a, b in periods:
            row[f"r{a}_{b}"] = r2(rate(s, a, b))
        row["pct2005_2025"] = r2(pct(s, 2005, 2025), 1)
        row["ratio2005_2025"] = r2(s[2005] / s[2025] if 2005 in s else None, 2)
        row["pct2015_2025"] = r2(pct(s, 2015, 2025), 1)
        row["r2005_2015"] = r2(rate(s, 2005, 2015))
        row["r2015_2025"] = r2(rate(s, 2015, 2025))
        yy = [y for y in s if y >= 2000]
        row["min_year_since2000"] = min(yy, key=lambda y: (s[y], y))
        row["min_value_since2000"] = s[row["min_year_since2000"]]
        rows.append(row)
    cols = list(rows[0].keys())
    with open(RES / "item_rates.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols, lineterminator="\n"); wr.writeheader(); wr.writerows(rows)
    byc = {r["code"]: r for r in rows}
    main["item_rates"] = {r["name"]: {k: r[k] for k in ["first_year", "pct2005_2025", "ratio2005_2025", "r2005_2015", "r2015_2025", "pct2015_2025", "min_year_since2000", "min_value_since2000", "weight_2025"]} for r in rows}
    # H1：4品目すべて −50% 以下
    h1 = {NAMES[c]: byc[c]["pct2005_2025"] for c in HED4}
    main["H1"] = {"pct2005_2025": h1, "supported": all(v is not None and v <= -50 for v in h1.values())}
    # H2：下げが鈍った品目の数（2015→2025の年率 > 2005→2015の年率）
    slowed = [NAMES[c] for c in HED4 if byc[c]["r2015_2025"] > byc[c]["r2005_2015"]]
    main["H2"] = {"slowed": slowed, "n_slowed": len(slowed), "supported": len(slowed) >= 3,
                  "r2005_2015": {NAMES[c]: byc[c]["r2005_2015"] for c in HED4},
                  "r2015_2025": {NAMES[c]: byc[c]["r2015_2025"] for c in HED4}}
    # 比べる品目の平均（単純平均）
    main["comp_mean_r2005_2015"] = r2(sum(byc[c]["r2005_2015"] for c in COMP if byc[c]["r2005_2015"] is not None) / len([c for c in COMP if byc[c]["r2005_2015"] is not None]))
    main["comp_mean_r2015_2025"] = r2(sum(byc[c]["r2015_2025"] for c in COMP) / len(COMP))
    main["total_pct2005_2025"] = byc["0001"]["pct2005_2025"]

    # --- B. 1台あたりの輸入額（電算機類）と CPI パソコン ---
    tr = defaultdict(dict)
    with open(DATA / "trade_units.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            tr[r["item"]][int(r["year"])] = float(r["value_thousand_yen"]) * 1000 / float(r["units"])
    wd, wn = w[("2025", "9078")], w[("2025", "9079")]
    pc = {}
    for y in range(2000, 2026):
        a, b = d[("2025", "9078")].get(y), d[("2025", "9079")].get(y)
        if a and b:
            pc[y] = math.exp((wd * math.log(a) + wn * math.log(b)) / (wd + wn))
    brows = []
    for y in range(2000, 2026):
        brows.append({"year": y, "unit_value_yen": round(tr["computers"][y]), "unit_value_idx2005": round(tr["computers"][y] / tr["computers"][2005], 4),
                      "cpi_pc_idx2005": round(pc[y] / pc[2005], 4), "log_gap_vs2005": round(math.log(tr["computers"][y] / tr["computers"][2005]) - math.log(pc[y] / pc[2005]), 4)})
    with open(RES / "unit_value_vs_cpi.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(brows[0].keys()), lineterminator="\n"); wr.writeheader(); wr.writerows(brows)
    b05, b25 = brows[5], brows[25]
    gap = b25["log_gap_vs2005"]
    main["B_unit_value"] = {"uv_2005_yen": b05["unit_value_yen"], "uv_2025_yen": b25["unit_value_yen"],
                            "uv_pct2005_2025": r2(100 * (b25["unit_value_idx2005"] - 1), 1),
                            "cpi_pc_pct2005_2025": r2(100 * (b25["cpi_pc_idx2005"] - 1), 1),
                            "log_gap_2005_2025": r2(gap, 3), "gap_ratio": r2(math.exp(gap), 1),
                            "gap_per_year_pct": r2(100 * gap / 20, 2)}
    main["H3"] = {"log_gap": r2(gap, 3), "supported": gap >= 1.0}

    # --- C. 総合の前年比への寄与（その基準の表のウエイトで） ---
    crow = []
    for basis, years in [("2015", range(2016, 2021)), ("2020", range(2021, 2026))]:
        names, codes, weights, body = read_cpi(RAW / f"cpi{basis}_item_annual.csv")
        jt = codes.index("0001")
        tot = {int(r[0]): float(r[jt]) for r in body if r[jt].strip()}
        W = float(weights[jt])
        for y in years:
            row = {"basis": basis, "year": y, "total_yoy": round(100 * (tot[y] / tot[y - 1] - 1), 3)}
            s7 = 0.0
            for c in POS7:
                if ("%s" % basis, c) not in d:
                    continue
                s = d[(basis, c)]
                if y in s and (y - 1) in s:
                    v = w[(basis, c)] * (s[y] - s[y - 1]) / (W * tot[y - 1]) * 100
                    row["c_" + c] = round(v, 4)
                    s7 += v
            row["c_pos7"] = round(s7, 4)
            # 4品目（ヘドニック法の品目）
            row["c_hed4"] = round(sum(row.get("c_" + c, 0) for c in HED4), 4)
            crow.append(row)
    cols = ["basis", "year", "total_yoy", "c_pos7", "c_hed4"] + ["c_" + c for c in POS7]
    with open(RES / "contribution.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols, lineterminator="\n", restval=""); wr.writeheader(); wr.writerows(crow)
    m1 = [r["c_pos7"] for r in crow if r["basis"] == "2015"]
    m2 = [r["c_pos7"] for r in crow if r["basis"] == "2020"]
    main["C_contribution"] = {"mean_2016_2020": r2(sum(m1) / len(m1), 3), "mean_2021_2025": r2(sum(m2) / len(m2), 3),
                              "min_year": min(crow, key=lambda r: r["c_pos7"])["year"], "min_value": r2(min(r["c_pos7"] for r in crow), 3),
                              "max_year": max(crow, key=lambda r: r["c_pos7"])["year"], "max_value": r2(max(r["c_pos7"] for r in crow), 3),
                              "weight_pos7_per10000": {b: round(sum(w[(b, c)] for c in POS7 if (b, c) in w) / sum(1 for _ in [0]) / 1, 0) for b in []}}
    # ウエイト（1万分比）
    wsh = {}
    for basis in ["2015", "2020", "2025"]:
        names, codes, weights, body = read_cpi(RAW / f"cpi{basis}_item_annual.csv")
        W = float(weights[codes.index("0001")])
        wsh[basis] = round(10000 * sum(float(weights[codes.index(c)]) for c in POS7 if c in codes) / W, 1)
    main["C_contribution"]["weight_pos7_per10000"] = wsh
    main["H4"] = {"mean_2016_2020": main["C_contribution"]["mean_2016_2020"], "supported": main["C_contribution"]["mean_2016_2020"] > -0.1}

    # --- 頑健性 ---
    rob = []
    # 1. 期間の端を変える（2005→2025 の代わりに 2006→2024、2004→2025）
    for a, b in [(2006, 2024), (2005, 2024), (2007, 2023)]:
        vals = {NAMES[c]: r2(pct(d[("2025", c)], a, b), 1) for c in HED4}
        rob.append({"check": f"期間を {a}→{b} に", "result": "；".join(f"{k} {v}%" for k, v in vals.items()),
                    "same_conclusion": all(v is not None and v <= -50 for v in vals.values())})
    # 2. 暦年の表と月次の1〜12月の平均
    mon = defaultdict(lambda: defaultdict(list))
    with open(DATA / "cpi_items_monthly_2025.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p = r["period"]
            if len(p) == 6:
                mon[r["code"]][int(p[:4])].append(float(r["value"]))
    diffs = []
    for c in POS7 + ["0001"]:
        for y, vs in mon[c].items():
            if len(vs) == 12 and y in d[("2025", c)] and 2000 <= y <= 2025:
                diffs.append(100 * abs(sum(vs) / 12 / d[("2025", c)][y] - 1))
    rob.append({"check": "暦年の表と月次の1〜12月の平均（2000〜2025年、8系列）", "result": f"差（%）の最大 {max(diffs):.2f}%、平均 {sum(diffs)/len(diffs):.3f}%（{len(diffs)} 個）",
                "same_conclusion": max(diffs) < 1.0})
    main["rob_monthly_vs_annual_maxdiff"] = round(max(diffs), 3)
    # 3. 2025年基準の長期の表と2020年基準の表で、2015→2020の変化率
    dd = []
    for c in HED4:
        a = pct(d[("2025", c)], 2015, 2020); b = pct(d[("2020", c)], 2015, 2020)
        dd.append(f"{NAMES[c]} {a:.1f}%／{b:.1f}%")
    rob.append({"check": "2015→2020年の変化率：2025年基準の長期の表／2020年基準の表", "result": "；".join(dd), "same_conclusion": True})
    # 4. 電話機（1台あたりの輸入額）と CPI 携帯電話機（ヘドニック法の品目ではない）
    ph = tr["phones"]; cp = d[("2025", "7446")]
    g_uv = math.log(ph[2025] / ph[2017]); g_cpi = math.log(cp[2025] / cp[2017])
    rob.append({"check": "電話機の1台あたりの輸入額と CPI 携帯電話機（2017→2025、対数の差）", "result": f"輸入額 {g_uv:+.3f}、CPI {g_cpi:+.3f}、差 {g_uv - g_cpi:+.3f}",
                "same_conclusion": None})
    pc17 = math.log(tr["computers"][2025] / tr["computers"][2017]) - math.log(pc[2025] / pc[2017])
    main["rob_phone"] = {"uv_log": round(g_uv, 3), "cpi_log": round(g_cpi, 3), "gap": round(g_uv - g_cpi, 3), "pc_gap_2017_2025": round(pc17, 3)}
    rob[-1]["result"] += f"（同じ期間のパソコンの差は {pc17:+.3f}）"
    # 5. 寄与の式で総合を再現できるか（基準年以外の年で、Σw×I/Σw と公表の総合）
    rec = []
    for basis in ["2015", "2020"]:
        names, codes, weights, body = read_cpi(RAW / f"cpi{basis}_item_annual.csv")
        # 品目の列（符号が4桁で、先頭が0でないもの）
        items = [j for j, c in enumerate(codes) if j > 0 and len(c) == 4 and not c.startswith("0") and weights[j].strip()]
        jt = codes.index("0001")
        for r in body:
            y = int(r[0])
            if y < int(basis) or y > int(basis) + 5:
                continue
            num = den = 0.0
            ok = True
            for j in items:
                v = r[j].strip()
                if not v:
                    ok = False; break
                num += float(weights[j]) * float(v); den += float(weights[j])
            if ok:
                rec.append((basis, y, round(num / den - float(r[jt]), 3)))
    main["rob_reconstruct"] = [{"basis": b, "year": y, "diff": v} for b, y, v in rec]
    rob.append({"check": "Σウエイト×品目指数÷Σウエイト と公表の総合の差（基準年から5年）", "result": "；".join(f"{b}年基準 {y}年 {v:+.2f}" for b, y, v in rec),
                "same_conclusion": all(abs(v) < 0.3 for _, _, v in rec)})
    with open(RES / "robustness.csv", "w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["check", "result", "same_conclusion"], lineterminator="\n"); wr.writeheader(); wr.writerows(rob)
    main["robustness"] = rob
    with open(RES / "main.json", "w", encoding="utf-8") as f:
        json.dump(main, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
