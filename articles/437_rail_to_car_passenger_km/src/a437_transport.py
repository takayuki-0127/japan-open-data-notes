"""A437 人を運ぶ主役は、鉄道から自動車へ、いつ入れ替わったのか
日本の長期統計系列 12-2-a 輸送機関別国内輸送－旅客（1950〜2004年度）。"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：総務省統計局「日本の長期統計系列」12-2-a（国土交通省の輸送統計）をもとに作成"
raw = pd.read_excel(DATA / "raw" / "chouki_12-02-a.xls", header=None)
cols = ["total", "auto", "bus", "car", "private_truck", "rail", "jr", "other_rail", "ship", "air"]
def block(start):
    rows = []
    for i in range(start + 1, start + 56):
        y = 1950 + (i - start - 1)          # 年度は1950年度から1行ずつ（年の欄に注記の記号が入る行がある）
        v = [pd.to_numeric(str(x).replace("a)", "").strip(), errors="coerce") for x in raw.iloc[i, 2:12]]
        rows.append([y] + v)
    return pd.DataFrame(rows, columns=["fy"] + cols)
i_p = raw.index[raw[0].astype(str).str.startswith("輸送人員 (")][0]; i_k = raw.index[raw[0].astype(str).str.startswith("輸送人キロ (")][0]
pax, pkm = block(i_p), block(i_k)
assert pax.fy.tolist() == list(range(1950, 2005)) and pkm.fy.tolist() == list(range(1950, 2005))
pkm.to_csv(DATA / "passenger_km_by_mode_fy1950_2004.csv", index=False); pax.to_csv(DATA / "passengers_by_mode_fy1950_2004.csv", index=False)

def shares(d):
    s = pd.DataFrame({"fy": d.fy}); tot = d[["auto", "rail", "ship", "air"]].fillna(0).sum(axis=1)
    for c in ["auto", "rail", "ship", "air", "bus", "car", "private_truck", "jr", "other_rail"]: s[c] = d[c] / tot * 100
    s["sum4_vs_total"] = tot / d.total
    return s
sk, sp = shares(pkm), shares(pax)
sk.to_csv(RES / "a437_share_passenger_km.csv", index=False); sp.to_csv(RES / "a437_share_passengers.csv", index=False)

def first(s, cond):
    x = s[cond]; return int(x.fy.iloc[0]) if len(x) else None
k = sk.set_index("fy"); p = sp.set_index("fy")
# 1987年度から軽自動車と自家用貨物車が入る。入れない場合の割合（1987年度以降）
alt = pkm.copy(); alt["auto2"] = alt.auto - alt.private_truck.fillna(0); t2 = alt[["auto2", "rail", "ship", "air"]].fillna(0).sum(axis=1)
alt_share = pd.DataFrame({"fy": alt.fy, "auto_excl_private_truck": alt.auto2 / t2 * 100, "rail_excl": alt.rail / t2 * 100}).set_index("fy")
main = {"fy": [1950, 2004],
        "pkm_total": {str(y): float(pkm.set_index("fy").loc[y, "total"]) for y in (1950, 1960, 1970, 1980, 1990, 2004)},
        "share_pkm": {str(y): {c: round(float(k.loc[y, c]), 2) for c in ["auto", "rail", "ship", "air", "bus", "car"]} for y in (1950, 1955, 1960, 1965, 1970, 1971, 1975, 1980, 1986, 1987, 1990, 2000, 2004)},
        "auto_over_rail_pkm_fy": first(sk, sk.auto > sk.rail), "auto_over_rail_passengers_fy": first(sp, sp.auto > sp.rail),
        "car_over_bus_pkm_fy": first(sk, sk.car > sk.bus), "car_over_rail_pkm_fy": first(sk, sk.car > sk.rail),
        "rail_share_max": [int(k.rail.idxmax()), round(float(k.rail.max()), 1)], "rail_share_min": [int(k.rail.idxmin()), round(float(k.rail.min()), 1)],
        "air_share_max": [int(k.air.idxmax()), round(float(k.air.max()), 2)], "air_first_1pct_fy": first(sk, sk.air >= 1), "air_first_5pct_fy": first(sk, sk.air >= 5),
        "bus_share_max": [int(k.bus.idxmax()), round(float(k.bus.max()), 1)],
        "rail_pkm": {str(y): float(pkm.set_index("fy").loc[y, "rail"]) for y in (1950, 1970, 1974, 1986, 1990, 2004)}, "rail_pkm_max": [int(pkm.set_index("fy").rail.idxmax()), float(pkm.rail.max())],
        "auto_pkm": {str(y): float(pkm.set_index("fy").loc[y, "auto"]) for y in (1950, 1960, 1970, 1980, 1986, 1987, 2004)},
        "break_1987": {"auto_share_1986": round(float(k.loc[1986, "auto"]), 1), "auto_share_1987": round(float(k.loc[1987, "auto"]), 1),
                       "auto_share_1987_excl_private_truck": round(float(alt_share.loc[1987, "auto_excl_private_truck"]), 1), "auto_share_2004_excl_private_truck": round(float(alt_share.loc[2004, "auto_excl_private_truck"]), 1)},
        "sum4_vs_total_range": [round(float(sk.sum4_vs_total.min()), 3), round(float(sk.sum4_vs_total.max()), 3)],
        "share_passengers": {str(y): {c: round(float(p.loc[y, c]), 1) for c in ["auto", "rail"]} for y in (1950, 1960, 1964, 1965, 1970, 2004)}}
json.dump(main, open(RES / "a437_main.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(main, ensure_ascii=False))

fig, ax = plt.subplots(figsize=(9, 4.6))
ax.stackplot(sk.fy, sk.rail, sk.bus, sk.car.fillna(0), sk.private_truck.fillna(0), sk.ship.fillna(0), sk.air.fillna(0), colors=[BLUE, LIGHT, ORANGE, "#f5c3ae", GREEN, INK], labels=["鉄道", "バス", "乗用車", "自家用貨物車", "旅客船", "航空"])
ax.axvline(1986.5, color="white", lw=1.2, ls="--"); ax.text(1987.3, 3, "1987年度から\n軽自動車などを含む", fontsize=8, color="white")
ax.set_xlim(1950, 2004); ax.set_ylim(0, 100); ax.set_ylabel("輸送人キロに占める割合（%）"); ax.legend(frameon=False, ncol=6, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.08))
ax.set_title("人を運んだ距離（輸送人キロ）の内訳（1950〜2004年度）"); save(fig, "a437_share_stack.png", SRC, y=-0.08)

fig, ax = plt.subplots(figsize=(9, 4.4))
ax.plot(sk.fy, sk.rail, color=BLUE, lw=2, label="鉄道（人キロ）"); ax.plot(sk.fy, sk.auto, color=ORANGE, lw=2, label="自動車（人キロ）")
ax.plot(sp.fy, sp.rail, color=BLUE, lw=1.4, ls="--", label="鉄道（人数）"); ax.plot(sp.fy, sp.auto, color=ORANGE, lw=1.4, ls="--", label="自動車（人数）")
ax.axhline(50, color=GRAY, lw=0.8, ls=":"); ax.set_xlim(1950, 2004); ax.set_ylim(0, 100); ax.set_ylabel("割合（%）"); ax.legend(frameon=False, ncol=2, fontsize=9)
ax.set_title(f"自動車が鉄道を上回ったのは、人数で{main['auto_over_rail_passengers_fy']}年度、人キロで{main['auto_over_rail_pkm_fy']}年度"); save(fig, "a437_rail_vs_auto.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.4)); q = pkm.set_index("fy")
for c, col, lab in (("rail", BLUE, "鉄道"), ("bus", LIGHT, "バス"), ("car", ORANGE, "乗用車"), ("air", INK, "航空")): ax.plot(q.index, q[c], color=col, lw=2, label=lab)
ax.axvline(1986.5, color=GRAY, lw=0.8, ls=":"); ax.set_xlim(1950, 2004); ax.set_ylabel("輸送人キロ（10億人キロ）"); ax.legend(frameon=False, ncol=4, fontsize=9)
ax.set_title("割合が下がっても、鉄道が運んだ距離は減っていない"); save(fig, "a437_pkm_levels.png", SRC)
