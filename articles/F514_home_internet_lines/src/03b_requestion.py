"""問い直し（結果を見てから足した）：2024年の携帯電話回線の割合の跳ね上がり（+20ポイント）は、どの年齢でも同じように起きたのか。
年齢でそろって跳ねたなら、使い方の変化より、選択肢（ホームルーター）が加わった影響を疑う材料になる。
あわせて、固定系を使わない世帯の目安を年齢別に2019年と2025年で比べる。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
sub = pd.read_csv(R / "by_attribute.csv")
d = pd.read_csv(ROOT / "data" / "lines.csv")
AGES = ["20~29歳", "30~39歳", "40~49歳", "50~59歳", "60~69歳", "70~79歳", "80歳以上"]
x = sub[(sub.group == "世帯主年齢") & (sub.category.isin(AGES))]
mob = x.pivot(index="category", columns="year", values="mobile").loc[AGES]
nofix = x.pivot(index="category", columns="year", values="no_fixed").loc[AGES]
hr = d[(d.group == "世帯主年齢") & (d.line == "home_router") & (d.category.isin(AGES))].pivot(index="category", columns="year", values="pct").loc[AGES]
g5 = d[(d.group == "世帯主年齢") & (d.line == "g5") & (d.category.isin(AGES))].pivot(index="category", columns="year", values="pct").loc[AGES]
out = pd.DataFrame({"mobile_2023": mob[2023], "mobile_2024": mob[2024], "jump_2023_2024": (mob[2024] - mob[2023]).round(1),
                    "jump_2019_2023_per_year": ((mob[2023] - mob[2019]) / 4).round(2),
                    "home_router_2024": hr[2024], "g5_2023": g5[2023], "g5_2024": g5[2024],
                    "no_fixed_2019": nofix[2019], "no_fixed_2025": nofix[2025]})
out.to_csv(R / "requestion_by_age.csv")
res = {
    "jump_by_age": {k: float(v) for k, v in out.jump_2023_2024.items()},
    "jump_min": float(out.jump_2023_2024.min()), "jump_max": float(out.jump_2023_2024.max()),
    "home_router_2024_range": [float(out.home_router_2024.min()), float(out.home_router_2024.max())],
    "no_fixed_2019": {k: float(v) for k, v in out.no_fixed_2019.items()},
    "no_fixed_2025": {k: float(v) for k, v in out.no_fixed_2025.items()},
    "ages_no_fixed_down": [k for k in AGES if out.no_fixed_2025[k] < out.no_fixed_2019[k]],
}
(R / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(out)
