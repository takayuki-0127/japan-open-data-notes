"""問い直し（結果を見てから足した）：年齢が分からない人は、国籍（日本人かどうか）も分からないことが多いのか。
2025年の原数値で、年齢「不詳」を「日本人と分かっている人」と「それ以外（外国人と、日本人かどうか不詳の人）」に分ける。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
det = pd.read_csv(ROOT / "data" / "age_2025_2020_detail.csv")
x = det[(det.year == 2025) & (det.version == "original") & (det.sex == "総数")]
a = x[x.nationality == "国籍総数"].set_index("pref_code"); j = x[x.nationality == "うち日本人"].set_index("pref_code")
REGION = {1: "北海道", **{c: "東北" for c in range(2, 8)}, **{c: "関東" for c in range(8, 15)}, **{c: "中部" for c in range(15, 24)},
          **{c: "近畿" for c in range(24, 31)}, **{c: "中国" for c in range(31, 36)}, **{c: "四国" for c in range(36, 40)},
          **{c: "九州・沖縄" for c in range(40, 48)}}
df = pd.DataFrame({"pref": a.pref, "total": a.total, "unknown": a.unknown, "jp_total": j.total, "jp_unknown": j.unknown})
df["other_total"] = df.total - df.jp_total; df["other_unknown"] = df.unknown - df.jp_unknown
df["region"] = [REGION.get(c, "全国") for c in df.index]
df.reset_index().to_csv(R / "requestion_nationality_2025.csv", index=False, float_format="%.1f", lineterminator="\n")
n = df.loc[0]
reg = df[df.index > 0].groupby("region")[["total", "unknown", "jp_total", "jp_unknown", "other_total", "other_unknown"]].sum()
reg = reg.reindex(["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"])
reg["share_other_in_unknown"] = 100 * reg.other_unknown / reg.unknown
reg["jp_rate"] = 100 * reg.jp_unknown / reg.jp_total
reg.reset_index().to_csv(R / "requestion_nationality_region_2025.csv", index=False, float_format="%.5f", lineterminator="\n")
m = json.load(open(R / "main.json", encoding="utf-8"))
m["requestion"] = {
    "unknown_all": float(n.unknown), "unknown_jp": float(n.jp_unknown), "unknown_other": float(n.other_unknown),
    "other_total": float(n.other_total), "share_other_in_unknown": float(100 * n.other_unknown / n.unknown),
    "rate_jp": float(100 * n.jp_unknown / n.jp_total), "rate_other": float(100 * n.other_unknown / n.other_total),
    "share_other_in_population": float(100 * n.other_total / n.total),
    "region_share_other_in_unknown": {k: float(v) for k, v in reg.share_other_in_unknown.items()},
    "region_jp_rate": {k: float(v) for k, v in reg.jp_rate.items()},
}
json.dump(m, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(m["requestion"], ensure_ascii=False, indent=1))
