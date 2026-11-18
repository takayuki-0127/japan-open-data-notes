"""学科別の推移、職業学科の減少の分解、総合学科との比較、地方別、仮説の判定、頑健性。結果は results/ に書く。"""
import json
import pandas as pd
from common import ROOT

D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
VOC = ["農業", "工業", "商業", "水産", "家庭", "看護", "情報", "福祉"]
G = ["普通", "農業", "工業", "商業", "水産", "家庭", "看護", "情報", "福祉", "その他専門", "総合学科"]
REGION = {"北海道": ["北海道"], "東北": ["青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県"],
          "関東": ["茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県"],
          "中部": ["新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県"],
          "近畿": ["三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県"],
          "中国": ["鳥取県", "島根県", "岡山県", "広島県", "山口県"], "四国": ["徳島県", "香川県", "愛媛県", "高知県"],
          "九州沖縄": ["福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]}


def r1(x, n=1):
    return round(float(x), n)


nat = pd.read_csv(D / "national_by_course.csv").set_index("year")
nat["職業学科"] = nat[VOC].sum(axis=1)
nat["農工商"] = nat[["農業", "工業", "商業"]].sum(axis=1)
nat["普通科以外"] = nat.total - nat["普通"]
share = (100 * nat[G + ["職業学科", "農工商", "普通科以外"]].div(nat.total, axis=0)).round(3)
out = nat.join(share.add_suffix("_pct"))
idx = (100 * nat[G + ["職業学科", "total"]] / nat.loc[1985, G + ["職業学科", "total"]]).round(2)
out = out.join(idx.add_suffix("_idx1985"))
out.to_csv(R / "by_year.csv")


def decomp(col, y0, y1):
    """人数の変化 = 全体の人数の効果 + 割合の効果（2つの年の平均を重みにする対称な形）。"""
    N0, N1 = nat.loc[y0, "total"], nat.loc[y1, "total"]
    s0, s1 = nat.loc[y0, col] / N0, nat.loc[y1, col] / N1
    size = (N1 - N0) * (s0 + s1) / 2
    shr = (s1 - s0) * (N0 + N1) / 2
    return {"change": int(nat.loc[y1, col] - nat.loc[y0, col]), "size_effect": int(round(size)), "share_effect": int(round(shr)),
            "share_from_pct": r1(100 * s0), "share_to_pct": r1(100 * s1), "pct_change": r1(100 * (nat.loc[y1, col] / nat.loc[y0, col] - 1))}


m = {"years": [int(nat.index.min()), int(nat.index.max())]}
m["total"] = {int(y): int(v) for y, v in nat.total.items()}
m["voc"] = {int(y): int(v) for y, v in nat["職業学科"].items()}
m["voc_share_pct"] = {int(y): float(share.loc[y, "職業学科"]) for y in nat.index}
m["total_change_1985_2025_pct"] = r1(100 * (nat.loc[2025, "total"] / nat.loc[1985, "total"] - 1))
m["decomp_voc_1985_2025"] = decomp("職業学科", 1985, 2025)
m["by_course"] = {g: {"n1985": int(nat.loc[1985, g]), "n1995": int(nat.loc[1995, g]), "n2010": int(nat.loc[2010, g]),
                      "n2025": int(nat.loc[2025, g]),
                      "pct_1985_2025": r1(100 * (nat.loc[2025, g] / nat.loc[1985, g] - 1)) if nat.loc[1985, g] else None,
                      "share1985_pct": r1(share.loc[1985, g]), "share2025_pct": r1(share.loc[2025, g])} for g in G}
m["integrated_increase_1995_2025"] = int(nat.loc[2025, "総合学科"] - nat.loc[1995, "総合学科"])
m["integrated_peak_year"] = int(nat["総合学科"].idxmax())
m["integrated_peak"] = int(nat["総合学科"].max())
m["voc_decrease_1995_2025"] = int(nat.loc[1995, "職業学科"] - nat.loc[2025, "職業学科"])
m["integrated_over_voc_decrease_pct"] = r1(100 * m["integrated_increase_1995_2025"] / m["voc_decrease_1995_2025"])
m["general_share_pct"] = {int(y): float(share.loc[y, "普通"]) for y in nat.index}

# 文部科学省のページの構成比との照合
ref = pd.read_csv(D / "mext_share_table.csv").set_index("year")
cmp = []
for y in nat.index:
    if y in ref.index:
        cmp.append({"year": int(y), "voc_own": r1(share.loc[y, "職業学科"]), "voc_mext": float(ref.loc[y, "vocational"]),
                    "general_own": r1(share.loc[y, "普通"]), "general_mext": float(ref.loc[y, "general"]),
                    "other_own": r1(share.loc[y, "その他専門"]), "other_mext": float(ref.loc[y, "other_special"]),
                    "integ_own": r1(share.loc[y, "総合学科"]), "integ_mext": 0.0 if pd.isna(ref.loc[y, "integrated"]) else float(ref.loc[y, "integrated"])})
cmp = pd.DataFrame(cmp)
cmp["max_abs_diff"] = cmp.apply(lambda r: max(abs(r.voc_own - r.voc_mext), abs(r.general_own - r.general_mext),
                                              abs(r.other_own - r.other_mext), abs(r.integ_own - r.integ_mext)), axis=1).round(2)
cmp.to_csv(R / "check_vs_mext.csv", index=False)
m["mext_check_max_abs_diff"] = float(cmp.max_abs_diff.max())
m["mext_check_years"] = [int(y) for y in cmp.year]
m["mext_voc_share_1955"] = float(ref.loc[1955, "vocational"])

# 地方別（北から南）
pf = pd.read_csv(D / "pref_by_course.csv")
pf["職業学科"] = pf[VOC].sum(axis=1)
pf["農工商"] = pf[["農業", "工業", "商業"]].sum(axis=1)
inv = {p: r for r, ps in REGION.items() for p in ps}
pf["region"] = pf.pref.map(inv)
rows = []
for reg in REGION:
    rec = {"region": reg}
    for y in [2010, 2025]:
        s = pf[(pf.region == reg) & (pf.year == y)]
        rec[f"total_{y}"] = int(s.total.sum())
        rec[f"voc_{y}"] = int(s["職業学科"].sum())
        rec[f"voc_share_{y}_pct"] = r1(100 * s["職業学科"].sum() / s.total.sum())
        rec[f"nks_share_{y}_pct"] = r1(100 * s["農工商"].sum() / s.total.sum())
        rec[f"integ_share_{y}_pct"] = r1(100 * s["総合学科"].sum() / s.total.sum())
        rec[f"voc_share_{y}_prefmean_pct"] = r1((100 * s["職業学科"] / s.total).mean())
    rec["voc_change_pct"] = r1(100 * (rec["voc_2025"] / rec["voc_2010"] - 1))
    rec["share_change_pt"] = r1(rec["voc_share_2025_pct"] - rec["voc_share_2010_pct"])
    rows.append(rec)
regdf = pd.DataFrame(rows)
regdf.to_csv(R / "by_region.csv", index=False)
m["region"] = {r["region"]: {k: v for k, v in r.items() if k != "region"} for r in rows}
m["voc_share_2010_pct"] = r1(share.loc[2010, "職業学科"])
m["voc_share_2025_pct"] = r1(share.loc[2025, "職業学科"])
nat_pref = {int(y): int(pf[pf.year == y].total.sum()) for y in [2010, 2025]}
m["pref_total_eq_national"] = all(nat_pref[y] == int(nat.loc[y, "total"]) for y in nat_pref)

# 仮説
d = m["decomp_voc_1985_2025"]
c = m["by_course"]
h = {
    "H1": {"rule": "職業学科 1985→2025 で −50%以上", "value": d["pct_change"], "verdict": "支持" if d["pct_change"] <= -50 else "外れ"},
    "H2": {"rule": "割合の効果（の大きさ）＞全体の人数の効果", "value": [d["share_effect"], d["size_effect"]],
           "verdict": "支持" if abs(d["share_effect"]) > abs(d["size_effect"]) else "外れ"},
    "H3": {"rule": "商業の減少率 ＞ 工業の減少率", "value": [c["商業"]["pct_1985_2025"], c["工業"]["pct_1985_2025"]],
           "verdict": "支持" if c["商業"]["pct_1985_2025"] < c["工業"]["pct_1985_2025"] else "外れ"},
    "H4": {"rule": "総合学科の増加（1995→2025）＜ 職業学科の減少の半分", "value": m["integrated_over_voc_decrease_pct"],
           "verdict": "支持" if m["integrated_over_voc_decrease_pct"] < 50 else "外れ"},
    "H5": {"rule": "どの地方も職業学科の割合が2010→2025年度で下がった", "value": {r["region"]: r["share_change_pt"] for r in rows},
           "verdict": "支持" if all(r["share_change_pt"] < 0 for r in rows) else "外れ"},
}
m["hypotheses"] = h

# 頑健性
rob = []
for y0 in [1985, 1995, 2010]:
    dd = decomp("職業学科", y0, 2025)
    rob.append({"check": f"職業学科（8学科）、{y0}→2025年度", **dd})
for y0 in [1985, 1995]:
    dd = decomp("農工商", y0, 2025)
    rob.append({"check": f"農業・工業・商業の3学科だけ、{y0}→2025年度", **dd})
dd = decomp("普通科以外", 1985, 2025)
rob.append({"check": "普通科以外（その他の専門学科・総合学科を含む）、1985→2025年度", **dd})
robdf = pd.DataFrame(rob)
robdf.to_csv(R / "robustness.csv", index=False)
m["robustness"] = rob
m["region_prefmean_all_down"] = bool(all(r["voc_share_2025_prefmean_pct"] < r["voc_share_2010_prefmean_pct"] for r in rows))
json.dump(m, open(R / "main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: m[k] for k in ["voc", "voc_share_pct", "decomp_voc_1985_2025", "integrated_over_voc_decrease_pct",
                                    "integrated_peak_year", "mext_check_max_abs_diff", "hypotheses", "total_change_1985_2025_pct"]},
                 ensure_ascii=False, indent=1))
print(pd.DataFrame(m["by_course"]).T.to_string())
print(regdf.to_string())
print(robdf.to_string())
print(cmp.to_string())
