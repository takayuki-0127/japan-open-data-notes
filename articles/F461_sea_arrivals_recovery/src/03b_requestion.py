"""問い直し：海港の「ふつうの入国」は2019年より増えた。増えたのは誰で、どの港か。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"
n = pd.read_csv(D / "sea_entries_by_nationality.csv")
npo = pd.read_csv(D / "sea_entries_nat_port.csv")
pf = pd.read_csv(D / "port_prefecture.csv")
G = ["総数", "韓国", "台湾", "中国", "北アメリカ", "ヨーロッパ", "オセアニア"]
t = n[n.nationality.isin(G)].pivot(index="nationality", columns="year", values="sea").reindex(G)
t["diff_2019_2025"] = t[2025] - t[2019]
t.astype(int).to_csv(R / "requestion_sea_entries_nationality.csv")
west = ["北アメリカ", "ヨーロッパ", "オセアニア"]
out = {"question": "海港のふつうの入国（フェリーなど）が2019年より増えたのは誰で、どの港か"}
out["by_nationality"] = {g: {str(y): int(t.loc[g, y]) for y in (2013, 2019, 2025)} for g in G}
out["west_2019"] = int(t.loc[west, 2019].sum()); out["west_2025"] = int(t.loc[west, 2025].sum())
out["total_diff"] = int(t.loc["総数", "diff_2019_2025"])
out["west_share_of_diff"] = round(float(t.loc[west, "diff_2019_2025"].sum() / t.loc["総数", "diff_2019_2025"]), 3)
# 欧米豪（北アメリカ・ヨーロッパ・オセアニア）の海港の入国：港別（県の北から南の順は port_prefecture の県で並べる）
w = npo[npo.nationality.isin(["米国", "ヨーロッパ", "オセアニア"])].groupby(["port", "year"]).sea_entries.sum().unstack(fill_value=0)
w["diff"] = w.get(2025, 0) - w.get(2019, 0)
big = w[(w[2019] >= 2000) | (w[2025] >= 2000)].copy()
big = big.join(pf.set_index("port").pref)
big[[2019, 2025, "diff", "pref"]].to_csv(R / "requestion_west_ports.csv")
out["west_ports_2019_2025"] = {p: {"2019": int(r[2019]), "2025": int(r[2025]), "pref": r.pref} for p, r in big.iterrows()}
# 韓国：対馬（比田勝・厳原）と博多・下関
k = npo[npo.nationality == "韓国"].groupby(["port", "year"]).sea_entries.sum().unstack(fill_value=0)
out["korea_ports"] = {p: {str(y): int(k.loc[p, y]) for y in (2013, 2019, 2025)} for p in ["比田勝", "厳原", "博多", "関門(下関)", "大阪"]}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print("requestion ok")
