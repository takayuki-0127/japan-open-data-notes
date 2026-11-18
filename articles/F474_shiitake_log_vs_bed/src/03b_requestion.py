"""問い直し（結果を見てから足した）：原木の生産はどの地方に残っているのか。
都道府県の値を地方（北から南の順）に足し、2005年と2025年で比べる。秘匿（x）の県は0として足さず、足せた割合も出す。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
SP = pd.read_csv(D / "shiitake_pref.csv")
S = pd.read_csv(D / "shiitake_national.csv").set_index("year")
REG = [("北海道", ["北海道"]), ("東北", ["青森", "岩手", "宮城", "秋田", "山形", "福島"]),
       ("関東", ["茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川"]),
       ("中部", ["新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知"]),
       ("近畿", ["三重", "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山"]),
       ("中国", ["鳥取", "島根", "岡山", "広島", "山口"]), ("四国", ["徳島", "香川", "愛媛", "高知"]),
       ("九州・沖縄", ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"])]
m = {p: g for g, ps in REG for p in ps}
assert len(m) == 47
SP["region"] = SP.pref.map(m)
rows = []
for y in (2005, 2025):
    s = SP[SP.year == y]
    for g, _ in REG:
        x = s[s.region == g]
        rows.append({"year": y, "region": g, "order": [q for q, _ in REG].index(g) + 1,
                     "fresh_log": x.fresh_log.sum(min_count=1), "fresh_bed": x.fresh_bed.sum(min_count=1),
                     "dry_total": x.dry_total.sum(min_count=1), "n_secret_fresh_log": int(x.fresh_log.isna().sum())})
G = pd.DataFrame(rows)
for c in ["fresh_log", "fresh_bed", "dry_total"]:
    G[f"{c}_share_of_national_pct"] = G.apply(lambda z: z[c] / S.loc[z.year, c.replace("dry_total", "dry_total")] * 100, axis=1)
G["log_share_within_region_pct"] = G.fresh_log / (G.fresh_log + G.fresh_bed) * 100
G["log_change_pct"] = None
for g, _ in REG:
    a, b = G[(G.region == g) & (G.year == 2005)].fresh_log.iloc[0], G[(G.region == g) & (G.year == 2025)].fresh_log.iloc[0]
    G.loc[(G.region == g) & (G.year == 2025), "log_change_pct"] = (b / a - 1) * 100
G = G.sort_values(["year", "order"]).reset_index(drop=True)
G.round(2).to_csv(R / "requestion_regions.csv", index=False)
cov = {y: {c: round(float(SP[SP.year == y][c].sum() / S.loc[y, c] * 100), 1) for c in ["fresh_log", "fresh_bed", "dry_total"]} for y in (2005, 2025)}
g25 = G[G.year == 2025].set_index("region"); g05 = G[G.year == 2005].set_index("region")
out = {"coverage_pct": cov,
       "kyushu_dry_share": {"2005": round(float(g05.loc["九州・沖縄", "dry_total_share_of_national_pct"]), 1), "2025": round(float(g25.loc["九州・沖縄", "dry_total_share_of_national_pct"]), 1)},
       "log_share_within_region_2025": {g: round(float(g25.loc[g, "log_share_within_region_pct"]), 1) for g, _ in REG},
       "log_share_within_region_2005": {g: round(float(g05.loc[g, "log_share_within_region_pct"]), 1) for g, _ in REG},
       "fresh_log_share_of_national_2025": {g: round(float(g25.loc[g, "fresh_log_share_of_national_pct"]), 1) for g, _ in REG},
       "fresh_log_share_of_national_2005": {g: round(float(g05.loc[g, "fresh_log_share_of_national_pct"]), 1) for g, _ in REG},
       "fresh_log_change_pct": {g: round(float(g25.loc[g, "log_change_pct"]), 1) for g, _ in REG}}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(G[["year", "region", "fresh_log", "fresh_bed", "dry_total", "n_secret_fresh_log", "fresh_log_share_of_national_pct", "dry_total_share_of_national_pct", "log_share_within_region_pct", "log_change_pct"]].round(1).to_string())
print(json.dumps(cov))
