"""分析用の表を作る。

flows.csv      : 2010〜2025年の都道府県間移動者数（日本人）
demog.csv      : 2012〜2023年の都道府県の日本人人口・出生数・死亡数（SSDSE-B）
pop_shares.csv : 2025年国勢調査と社人研2023年推計（2050年）の都道府県別人口
"""
import pandas as pd
from common import RAW, DATA

panel = pd.read_csv(RAW / "f33_panel.csv")
flows = panel.loc[panel.year >= 2010, ["year", "o", "d", "flow", "o_name", "d_name"]]
flows.to_csv(DATA / "flows.csv", index=False)
names = (panel[["o", "o_name"]].drop_duplicates().sort_values("o")
         .rename(columns={"o": "code", "o_name": "pref"}))

ss = pd.read_csv(RAW / "SSDSE-B-2026.csv", encoding="cp932", header=0)
ss = ss.iloc[1:]  # 2行目が日本語の見出し
ss = ss.rename(columns={"SSDSE-B-2026": "year", "Prefecture": "pref",
                        "A1102": "jp_pop", "A1101": "pop", "A4101": "births", "A4200": "deaths"})
ss = ss[["year", "pref", "pop", "jp_pop", "births", "deaths"]]
for c in ["year", "pop", "jp_pop", "births", "deaths"]:
    ss[c] = pd.to_numeric(ss[c])
ss = ss.merge(names, on="pref", how="inner")
assert ss.pref.nunique() == 47, ss.pref.nunique()
ss.sort_values(["year", "code"]).to_csv(DATA / "demog.csv", index=False)

def pref_tot(df, year):
    q = df[(df.year == year) & (df.code % 1000 == 0) & (df.code > 0) & (df.kind.astype(str) == "a")]
    ages = [c for c in df.columns if c.startswith("a") and c[1:].isdigit()]
    t = q.groupby("pref")[ages].sum().sum(axis=1)
    return t

ip = pd.read_csv(RAW / "ipss2023_pop.csv")
cs = pd.read_csv(RAW / "census2025_pop.csv")
out = pd.DataFrame({"census2025": pref_tot(cs, 2025), "ipss2020": pref_tot(ip, 2020),
                    "ipss2050": pref_tot(ip, 2050)}).reset_index().rename(columns={"index": "pref"})
out = names.merge(out, on="pref", how="left")
assert out.isna().sum().sum() == 0
out.to_csv(DATA / "pop_shares.csv", index=False)
print(len(flows), ss.shape, out.census2025.sum(), out.ipss2050.sum())
