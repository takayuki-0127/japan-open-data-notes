"""仮説 H1〜H4 と頑健性。結果は results/main.json と表 CSV に書く。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"; R.mkdir(exist_ok=True)
pe = pd.read_csv(D / "ports_foreign_entries.csv")
sl = pd.read_csv(D / "ports_special_landing.csv")
pf = pd.read_csv(D / "port_prefecture.csv")
fn = pd.read_csv(D / "funa_by_nationality.csv")
REG = {"北海道・東北": "北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県",
       "関東": "茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県",
       "中部": "新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県",
       "近畿": "三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県",
       "中国・四国": "鳥取県 島根県 鳥取県・島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県",
       "九州": "福岡県 佐賀県 佐賀県・長崎県 長崎県 熊本県 大分県 宮崎県 鹿児島県",
       "沖縄": "沖縄県"}
P2R = {p: r for r, ps in REG.items() for p in ps.split()}
pf["region"] = pf.pref.map(P2R)
assert pf.region.notna().all(), pf[pf.region.isna()]

sea_e = pe[pe.air == 0].groupby("year").foreign_entries.sum()
air_e = pe[pe.air == 1].groupby("year").foreign_entries.sum()
s = sl[sl.air == 0].groupby("year")[["kikochi", "tsuka", "funa", "crew"]].sum()
yr = pd.DataFrame({"sea_entries": sea_e, "kikochi": s.kikochi, "tsuka": s.tsuka, "funa": s.funa, "crew": s.crew, "air_entries": air_e})
yr["special_tourist"] = yr.kikochi + yr.tsuka + yr.funa
yr["sea_total"] = yr.sea_entries + yr.special_tourist
yr.astype(int).to_csv(R / "series_by_year.csv")


def ratio(a, b):
    return float(a) / float(b)


def r3(x):
    return round(float(x), 3)


main = {"source": "法務省「出入国管理統計」年報 港別の表", "years": [int(y) for y in yr.index]}
main["series"] = {int(y): {k: int(v) for k, v in row.items()} for y, row in yr.iterrows()}
peak_y = int(yr.sea_total.idxmax())
main["peak"] = {"year": peak_y, "sea_total": int(yr.sea_total.max())}

# H1
r25 = ratio(yr.loc[2025, "sea_total"], yr.loc[2019, "sea_total"])
main["H1"] = {"sea_total_2019": int(yr.loc[2019, "sea_total"]), "sea_total_2025": int(yr.loc[2025, "sea_total"]),
              "ratio_2025_2019": r3(r25), "change_pct": round((r25 - 1) * 100, 1), "result": "当たり" if r25 <= 0.9 else "外れ"}
# H2
ra = ratio(air_e[2025], air_e[2019])
main["H2"] = {"air_ratio": r3(ra), "sea_ratio": r3(r25), "diff": r3(ra - r25), "result": "当たり" if ra - r25 >= 0.3 else "外れ"}
main["parts"] = {k: {"2019": int(yr.loc[2019, k]), "2025": int(yr.loc[2025, k]), "ratio": r3(ratio(yr.loc[2025, k], yr.loc[2019, k]))}
                 for k in ["sea_entries", "special_tourist", "funa"]}

# 地方別
pe2 = pe[pe.air == 0].merge(pf[["port", "region"]], on="port", how="left")
sl2 = sl[sl.air == 0].merge(pf[["port", "region"]], on="port", how="left")
sl2["special_tourist"] = sl2.kikochi + sl2.tsuka + sl2.funa
unk_e = pe2[pe2.region.isna()].groupby("year").foreign_entries.sum()
main["unmapped_sea_entries_max"] = int(unk_e.max()) if len(unk_e) else 0
ge = pe2.groupby(["region", "year"]).foreign_entries.sum().unstack(fill_value=0)
gs = sl2.groupby(["region", "year"]).special_tourist.sum().unstack(fill_value=0)
gf = sl2.groupby(["region", "year"]).funa.sum().unstack(fill_value=0)
order = list(REG)
reg = pd.DataFrame(index=order)
for y in (2018, 2019, 2024, 2025):
    reg[f"entries_{y}"] = ge[y].reindex(order).fillna(0)
    reg[f"special_{y}"] = gs[y].reindex(order).fillna(0)
    reg[f"total_{y}"] = reg[f"entries_{y}"] + reg[f"special_{y}"]
    reg[f"funa_{y}"] = gf[y].reindex(order).fillna(0)
reg["ratio_2025_2019"] = reg.total_2025 / reg.total_2019
reg["ratio_2025_2018"] = reg.total_2025 / reg.total_2018
reg["ratio_2024_2019"] = reg.total_2024 / reg.total_2019
reg.index.name = "region"
reg.round(3).to_csv(R / "by_region.csv")
main["by_region"] = {r: {"total_2019": int(reg.loc[r, "total_2019"]), "total_2025": int(reg.loc[r, "total_2025"]),
                         "entries_2019": int(reg.loc[r, "entries_2019"]), "entries_2025": int(reg.loc[r, "entries_2025"]),
                         "special_2019": int(reg.loc[r, "special_2019"]), "special_2025": int(reg.loc[r, "special_2025"]),
                         "ratio_2025_2019": r3(reg.loc[r, "ratio_2025_2019"])} for r in order}
main["H3"] = {"okinawa": r3(reg.loc["沖縄", "ratio_2025_2019"]), "kyushu": r3(reg.loc["九州", "ratio_2025_2019"]),
              "result": "当たり" if reg.loc["沖縄", "ratio_2025_2019"] < reg.loc["九州", "ratio_2025_2019"] else "外れ"}
k19 = (reg.loc[["九州", "沖縄"], "funa_2019"].sum()) / reg.funa_2019.sum()
k25 = (reg.loc[["九州", "沖縄"], "funa_2025"].sum()) / reg.funa_2025.sum()
main["H4"] = {"kyushu_okinawa_share_2019": r3(k19), "kyushu_okinawa_share_2025": r3(k25), "result": "当たり" if k25 < k19 else "外れ"}

# 船舶観光上陸の国籍
nat = fn[fn.nationality.isin(["総数", "中国", "台湾", "中国〔香港〕", "韓国", "米国"])].pivot(index="year", columns="nationality", values="funa").fillna(0)
nat.astype(int).to_csv(R / "funa_nationality.csv")
main["funa_nationality"] = {int(y): {k: int(v) for k, v in row.items()} for y, row in nat.loc[[2016, 2019, 2024, 2025]].iterrows()}
main["funa_china_share"] = {int(y): r3(nat.loc[y, "中国"] / nat.loc[y, "総数"]) for y in (2016, 2017, 2018, 2019, 2024, 2025)}

# 頑健性
rob = {}
rob["R1_base_2018"] = {"sea_ratio": r3(ratio(yr.loc[2025, "sea_total"], yr.loc[2018, "sea_total"])), "air_ratio": r3(ratio(air_e[2025], air_e[2018])),
                       "okinawa": r3(reg.loc["沖縄", "ratio_2025_2018"]), "kyushu": r3(reg.loc["九州", "ratio_2025_2018"])}
rob["R2_end_2024"] = {"sea_ratio": r3(ratio(yr.loc[2024, "sea_total"], yr.loc[2019, "sea_total"])), "air_ratio": r3(ratio(air_e[2024], air_e[2019])),
                      "okinawa": r3(reg.loc["沖縄", "ratio_2024_2019"]), "kyushu": r3(reg.loc["九州", "ratio_2024_2019"])}
wc = yr.sea_total + yr.crew
rob["R3_with_crew"] = {"ratio_2025_2019": r3(ratio(wc[2025], wc[2019])), "crew_ratio": r3(ratio(yr.loc[2025, "crew"], yr.loc[2019, "crew"]))}
rob["R4_funa_only"] = {"ratio_2025_2019": r3(ratio(yr.loc[2025, "funa"], yr.loc[2019, "funa"])),
                       "okinawa": r3(reg.loc["沖縄", "funa_2025"] / reg.loc["沖縄", "funa_2019"]), "kyushu": r3(reg.loc["九州", "funa_2025"] / reg.loc["九州", "funa_2019"])}
# 5. 九州から対馬の2港（比田勝・厳原。韓国とのフェリーの港）を除く
TS = ["比田勝", "厳原"]
def ky(y, excl):
    e = pe2[(pe2.region == "九州") & (pe2.year == y) & (~pe2.port.isin(excl))].foreign_entries.sum()
    t = sl2[(sl2.region == "九州") & (sl2.year == y) & (~sl2.port.isin(excl))].special_tourist.sum()
    return e + t
rob["R5_kyushu_without_tsushima"] = {"ratio_2025_2019": r3(ky(2025, TS) / ky(2019, TS)), "ratio_2025_2018": r3(ky(2025, TS) / ky(2018, TS)),
                                     "tsushima_2018": int(ky(2018, []) - ky(2018, TS)), "tsushima_2019": int(ky(2019, []) - ky(2019, TS)),
                                     "tsushima_2025": int(ky(2025, []) - ky(2025, TS))}
rob["R6_seaports_entries_only"] = {"ratio_2025_2019": main["parts"]["sea_entries"]["ratio"], "ratio_2025_2018": r3(ratio(yr.loc[2025, "sea_entries"], yr.loc[2018, "sea_entries"]))}
main["robustness"] = rob
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print({k: main[k]["result"] for k in ["H1", "H2", "H3", "H4"]})
