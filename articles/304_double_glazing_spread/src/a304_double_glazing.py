"""304：二重以上のサッシ・複層ガラスの窓（以下「二重窓」）のある住宅は、どれだけ広まったか。
住宅・土地統計調査 時系列統計表 第19表（2003〜2023年、全国・都道府県、総数・持ち家・借家）。
"""
import csv, json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：総務省「住宅・土地統計調査」（令和5年 時系列統計表 第19表）をもとに作成者が加工して作成"
YEARS = [2003, 2008, 2013, 2018, 2023]
COLS = {"total": 4, "solar_heat": 9, "solar_heat_no": 14, "pv": 19, "pv_no": 24, "win_all": 29, "win_some": 34, "win_none": 39}
raw = list(csv.reader(open(DATA / "raw" / "hlts_ts_t19.csv", encoding="utf-8")))
starts = [i for i, r in enumerate(raw) if r and r[0].startswith("##SHEET")] + [len(raw)]
rec = []
for a, b in zip(starts[:-1], starts[1:]):
    tenure = raw[a][0].replace("##SHEET ", "")
    for r in raw[a:b]:
        if len(r) > 44 and r[1].isdigit() and len(r[1]) == 2:         # 全国（00）と都道府県（01〜47）だけ。大都市は使わない
            for k, c in COLS.items():
                for j, y in enumerate(YEARS):
                    v = r[c + j].replace(",", "")
                    rec.append((tenure, r[1], r[2], y, k, float(v) if v not in ("", "-", "…") else np.nan))
L = pd.DataFrame(rec, columns=["tenure", "code", "area", "year", "item", "dwellings"])
L.to_csv(DATA / "energy_equipment_long.csv", index=False)
W = L.pivot_table(index=["tenure", "code", "area", "year"], columns="item", values="dwellings").reset_index()
W["win_any"] = W.win_all + W.win_some
W["answered"] = W.win_all + W.win_some + W.win_none                    # 窓について答えのあった住宅
for k in ("win_all", "win_some", "win_any", "win_none", "pv", "solar_heat"):
    W[k + "_pct"] = W[k] / W.total * 100                               # 分母は総数（不詳を含む）＝公表の割合と同じ
W["win_any_pct_answered"] = W.win_any / W.answered * 100
W["win_all_pct_answered"] = W.win_all / W.answered * 100

nat = W[W.code == "00"].set_index(["tenure", "year"])
out = {"national": {}}
for t in ("総数", "持ち家", "借家"):
    out["national"][t] = {int(y): {k: round(float(nat.loc[(t, y), k]), 2) for k in
                                   ("win_all_pct", "win_some_pct", "win_any_pct", "win_none_pct", "win_any_pct_answered", "win_all_pct_answered", "pv_pct", "solar_heat_pct")} |
                                  {"win_all_man": round(float(nat.loc[(t, y), "win_all"]) / 1e4, 1), "win_any_man": round(float(nat.loc[(t, y), "win_any"]) / 1e4, 1),
                                   "total_man": round(float(nat.loc[(t, y), "total"]) / 1e4, 1), "unknown_pct": round(float(1 - nat.loc[(t, y), "answered"] / nat.loc[(t, y), "total"]) * 100, 2)}
                              for y in YEARS}
# 公表の割合（％）と、自分で割った値が合うか（全国・総数・すべての窓）
pub = {2003: 8.2, 2008: 10.6, 2013: 12.8, 2018: 14.7, 2023: 16.8}
out["check_published_all_windows"] = {y: [pub[y], round(out["national"]["総数"][y]["win_all_pct"], 1)] for y in YEARS}
# 5年ごとの増え方（ポイント）
tot = out["national"]["総数"]
out["step_pt_win_any"] = {f"{a}-{b}": round(tot[b]["win_any_pct"] - tot[a]["win_any_pct"], 2) for a, b in zip(YEARS[:-1], YEARS[1:])}
out["step_pt_win_all"] = {f"{a}-{b}": round(tot[b]["win_all_pct"] - tot[a]["win_all_pct"], 2) for a, b in zip(YEARS[:-1], YEARS[1:])}
# 増えた二重窓の住宅（すべて＋一部）を、持ち家と借家に分ける
d_any = {t: nat.loc[(t, 2023), "win_any"] - nat.loc[(t, 2003), "win_any"] for t in ("総数", "持ち家", "借家")}
out["increase_2003_2023_man"] = {t: round(float(v) / 1e4, 1) for t, v in d_any.items()}
out["increase_share_owner_pct"] = round(float(d_any["持ち家"] / (d_any["持ち家"] + d_any["借家"]) * 100), 1)
# 全体の割合の上がり方を、「持ち家・借家の中の変化」と「持ち家と借家の割合の変化」に分ける（総数は所有の関係不詳を含むので、持ち家＋借家で計算）
def ss(y0, y1):
    s0 = {t: nat.loc[(t, y0), "total"] for t in ("持ち家", "借家")}; s1 = {t: nat.loc[(t, y1), "total"] for t in ("持ち家", "借家")}
    w0 = {t: s0[t] / sum(s0.values()) for t in s0}; w1 = {t: s1[t] / sum(s1.values()) for t in s1}
    r0 = {t: nat.loc[(t, y0), "win_any"] / s0[t] for t in s0}; r1 = {t: nat.loc[(t, y1), "win_any"] / s1[t] for t in s1}
    within = sum((r1[t] - r0[t]) * (w0[t] + w1[t]) / 2 for t in s0); mix = sum((w1[t] - w0[t]) * (r0[t] + r1[t]) / 2 for t in s0)
    return {"total_pt": round(float(sum(r1[t] * w1[t] for t in s0) - sum(r0[t] * w0[t] for t in s0)) * 100, 2), "within_pt": round(float(within) * 100, 2), "mix_pt": round(float(mix) * 100, 2),
            "owner_share_y0": round(float(w0["持ち家"]) * 100, 1), "owner_share_y1": round(float(w1["持ち家"]) * 100, 1)}
out["shift_share_2003_2023"] = ss(2003, 2023)

# 都道府県のばらつき（名前を並べた順位は作らない。分布と、地方ごとのまとまりだけを見る）
P = W[(W.code != "00") & (W.tenure == "総数")].copy()
BLOCK = {"北海道・東北": range(1, 8), "関東": range(8, 15), "中部": range(15, 24), "近畿": range(24, 31), "中国・四国": range(31, 40), "九州・沖縄": range(40, 48)}
P["block"] = P.code.astype(int).map({c: b for b, r in BLOCK.items() for c in r})
q = P.groupby("year").win_any_pct.quantile([0, 0.25, 0.5, 0.75, 1]).unstack().round(1)
q.columns = ["min", "q25", "median", "q75", "max"]; q.to_csv(RES / "prefecture_spread.csv")
out["prefecture_spread_win_any_pct"] = {int(y): {k: float(v) for k, v in r.items()} for y, r in q.iterrows()}
bl = P.groupby(["block", "year"])[["win_any", "win_all", "total"]].sum().reset_index()
bl["win_any_pct"] = bl.win_any / bl.total * 100; bl["win_all_pct"] = bl.win_all / bl.total * 100
bl.round(2).to_csv(RES / "block_share.csv", index=False)
out["block_win_any_pct"] = {b: {int(y): round(float(v), 1) for y, v in g.set_index("year").win_any_pct.items()} for b, g in bl.groupby("block")}
out["block_win_all_pct"] = {b: {int(y): round(float(v), 1) for y, v in g.set_index("year").win_all_pct.items()} for b, g in bl.groupby("block")}
# 2003年に割合が低かった県ほど、その後の伸び（ポイント）は大きかったか
p03 = P[P.year == 2003].set_index("code").win_any_pct; p23 = P[P.year == 2023].set_index("code").win_any_pct
out["corr_level2003_vs_gain"] = round(float(np.corrcoef(p03, p23 - p03)[0, 1]), 3)
out["gain_pt_quantiles"] = {k: round(float(v), 1) for k, v in (p23 - p03).quantile([0, 0.25, 0.5, 0.75, 1]).items()}
out["n_pref_over_50pct"] = {int(y): int((P[P.year == y].win_any_pct >= 50).sum()) for y in YEARS}
out["n_pref_under_20pct"] = {int(y): int((P[P.year == y].win_any_pct < 20).sum()) for y in YEARS}
# 確かめ：分母を「窓について答えのあった住宅」にした場合／すべての窓だけで見た場合
out["robust"] = {"win_any_pct_answered": {y: tot[y]["win_any_pct_answered"] for y in YEARS}, "win_all_pct": {y: tot[y]["win_all_pct"] for y in YEARS},
                 "unknown_pct": {y: tot[y]["unknown_pct"] for y in YEARS}}
json.dump(out, open(RES / "a304_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

# 図1：全国の割合（すべての窓・一部の窓）
fig, ax = plt.subplots(figsize=(8, 4.2))
a = [tot[y]["win_all_pct"] for y in YEARS]; s = [tot[y]["win_some_pct"] for y in YEARS]; x = np.arange(5)
ax.bar(x, a, color=BLUE, label="すべての窓にある"); ax.bar(x, s, bottom=a, color=LIGHT, label="一部の窓にある")
for i in range(5):
    ax.text(i, a[i] / 2, f"{a[i]:.1f}", ha="center", va="center", color="white", fontsize=10)
    ax.text(i, a[i] + s[i] / 2, f"{s[i]:.1f}", ha="center", va="center", fontsize=10)
    ax.text(i, a[i] + s[i] + 0.8, f"計 {a[i] + s[i]:.1f}%", ha="center", fontsize=10)
ax.set_xticks(x); ax.set_xticklabels([f"{y}年" for y in YEARS]); ax.set_ylabel("住宅に占める割合（%）"); ax.set_ylim(0, 40)
ax.set_title("二重以上のサッシ・複層ガラスの窓がある住宅の割合（全国）"); ax.legend(frameon=False, loc="upper left")
save(fig, "a304_national.png", SRC)

# 図2：持ち家と借家
fig, ax = plt.subplots(figsize=(8, 4.2))
for t, c in (("持ち家", BLUE), ("借家", ORANGE)):
    v = [out["national"][t][y]["win_any_pct"] for y in YEARS]; v2 = [out["national"][t][y]["win_all_pct"] for y in YEARS]
    ax.plot(YEARS, v, color=c, marker="o", lw=2, label=f"{t}（すべて＋一部）"); ax.plot(YEARS, v2, color=c, marker="o", lw=1.5, ls="--", label=f"{t}（すべての窓）")
    ax.text(2023.4, v[-1], f"{v[-1]:.1f}%", color=c, va="center", fontsize=10); ax.text(2023.4, v2[-1], f"{v2[-1]:.1f}%", color=c, va="center", fontsize=10)
ax.set_xticks(YEARS); ax.set_xlim(2002, 2026.5); ax.set_ylim(0, 50); ax.set_ylabel("住宅に占める割合（%）")
ax.set_title("持ち家と借家で比べる"); ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "a304_tenure.png", SRC)

# 図3：地方ごと（6つのまとまり）
fig, ax = plt.subplots(figsize=(8, 4.2))
order = list(BLOCK); cols = [BLUE, GRAY, GREEN, ORANGE, "#8a5cc2", "#c9a227"]
for b, c in zip(order, cols):
    g = bl[bl.block == b]; ax.plot(g.year, g.win_any_pct, color=c, marker="o", lw=2, label=b)
    ax.text(2023.4, g.win_any_pct.iloc[-1], f"{g.win_any_pct.iloc[-1]:.0f}%", color=c, va="center", fontsize=9)
ax.set_xticks(YEARS); ax.set_xlim(2002, 2025.5); ax.set_ylim(0, 75); ax.set_ylabel("住宅に占める割合（%、すべて＋一部）")
ax.set_title("地方ごとの割合"); ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper left")
save(fig, "a304_blocks.png", SRC)
