"""積載効率・実車率・実車時の積載率、仮説の判定、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
L = pd.read_csv(ROOT / "data" / "fy_long.csv")
W = L.pivot_table(index=["fy", "era", "group"], columns="var", values="value").reset_index()
W["eff"] = W.tonkm / W.cap_tonkm * 100                     # 積載効率（%）
W["lr"] = W.loaded_ratio                                     # 実車率（%、原単位の表）
W.loc[W.run_km.notna(), "lr_calc"] = W.loaded_km / W.run_km * 100
W["load_when_loaded"] = W.eff / (W.lr / 100)                 # 実車時の積載率（%）
W["cap_t_per_loaded_km"] = W.cap_tonkm / W.loaded_km        # 実車1キロあたりの能力トン（参考）
W = W.sort_values(["fy", "group"]).reset_index(drop=True)
W.round(4).to_csv(R / "fy_metrics.csv", index=False)

def ser(g, col):
    return W[W.group == g].set_index("fy")[col]

bo = W[W.group == "biz_ordinary"].set_index("fy")
sizes = ["biz_lt3", "biz_3to6_5", "biz_6_5to11", "biz_11to16", "biz_16plus"]
C = W[(W.era == "C") & W.group.isin(sizes + ["biz_ordinary", "biz_small", "biz_special", "biz_kei", "own_ordinary", "biz_total"])]
size_tbl = C.pivot_table(index="group", columns="fy", values=["eff", "lr", "load_when_loaded"])
size_mean = C.groupby("group")[["eff", "lr", "load_when_loaded", "tonkm", "cap_tonkm"]].mean()
size_mean["share_tonkm_biz_ordinary"] = C.groupby("group").tonkm.sum() / C[C.group == "biz_ordinary"].tonkm.sum() * 100
size_mean.round(3).to_csv(R / "size_2020_2025_mean.csv")

# 仮説
b = bo.loc[2010:2025]
h1_max = float(b.eff.max()); h1_maxfy = int(b.eff.idxmax())
h2_min = float(b.load_when_loaded.min()); h2_minfy = int(b.load_when_loaded.idxmin())
h3 = float(size_mean.loc["biz_11to16", "eff"] - size_mean.loc["biz_lt3", "eff"]); h3b = float(size_mean.loc["biz_16plus", "eff"] - size_mean.loc["biz_lt3", "eff"])
h4 = float(bo.loc[2019, "eff"] - bo.loc[2010, "eff"])
hyp = {
    "H1": {"max_eff_2010_2025": round(h1_max, 2), "max_fy": h1_maxfy, "result": "支持" if h1_max < 40 else "外れ"},
    "H2": {"min_load_when_loaded": round(h2_min, 2), "min_fy": h2_minfy, "result": "支持" if h2_min >= 55 else "外れ"},
    "H3": {"diff_11to16_minus_lt3": round(h3, 2), "diff_16plus_minus_lt3": round(h3b, 2), "result": "支持" if min(h3, h3b) >= 10 else "外れ"},
    "H4": {"eff_2010": round(float(bo.loc[2010, 'eff']), 2), "eff_2019": round(float(bo.loc[2019, 'eff']), 2), "change": round(h4, 2), "result": "支持" if h4 < 0 else "外れ"},
}

# 分解（対数の差）：積載効率の変化 = 実車率の変化 + 実車時の積載率の変化
def decomp(g, y0, y1):
    s = W[W.group == g].set_index("fy")
    d_eff = np.log(s.loc[y1, "eff"] / s.loc[y0, "eff"]) * 100
    d_lr = np.log(s.loc[y1, "lr"] / s.loc[y0, "lr"]) * 100
    return {"from": y0, "to": y1, "eff0": round(float(s.loc[y0, "eff"]), 2), "eff1": round(float(s.loc[y1, "eff"]), 2),
            "lr0": round(float(s.loc[y0, "lr"]), 2), "lr1": round(float(s.loc[y1, "lr"]), 2),
            "lwl0": round(float(s.loc[y0, "load_when_loaded"]), 2), "lwl1": round(float(s.loc[y1, "load_when_loaded"]), 2),
            "dlog_eff": round(float(d_eff), 2), "dlog_lr": round(float(d_lr), 2), "dlog_lwl": round(float(d_eff - d_lr), 2)}

dec = [decomp("biz_ordinary", a, c) for a, c in [(2010, 2019), (2011, 2019), (2020, 2025), (2023, 2024), (2024, 2025), (2000, 2009)]]
pd.DataFrame(dec).to_csv(R / "decomposition.csv", index=False)

# 頑健性
rob = []
bt = W[W.group == "biz_total"].set_index("fy")
rob.append({"check": "基本：営業用普通車", "eff_range_2010_2025": f"{b.eff.min():.2f}〜{b.eff.max():.2f}", "lwl_range": f"{b.load_when_loaded.min():.2f}〜{b.load_when_loaded.max():.2f}",
            "eff_change_2010_2019": round(h4, 2), "note": ""})
# 営業用の計：実車率は表にないので、車種別の走行キロ（実車キロ÷実車率）を足して求める
own_cols = ["biz_ordinary", "biz_small", "biz_special", "biz_kei"]
pt = W[W.group.isin(own_cols + sizes)].copy()
pt["run_est"] = pt.loaded_km / (pt.lr / 100)
runs = pt[pt.group.isin(own_cols)].groupby("fy").run_est.sum()
bt_lr = bt.loaded_km / runs * 100
bt_lwl = bt.eff / (bt_lr / 100)
rob.append({"check": "範囲を営業用の計に（軽自動車・小型車・特種用途車を含む）", "eff_range_2010_2025": f"{bt.eff.loc[2010:].min():.2f}〜{bt.eff.loc[2010:].max():.2f}",
            "lwl_range": f"{bt_lwl.loc[2010:].min():.2f}〜{bt_lwl.loc[2010:].max():.2f}", "eff_change_2010_2019": round(float(bt.eff.loc[2019] - bt.eff.loc[2010]), 2), "note": ""})
cc = W[(W.era == "C") & W.eff_pub.notna()]
rob.append({"check": "2020年度以降：公表の積載効率と計算の差（最大の絶対値）", "eff_range_2010_2025": "", "lwl_range": "",
            "eff_change_2010_2019": np.nan, "note": f"{(cc.eff - cc.eff_pub).abs().max():.3f} ポイント（{len(cc)} 区分×年度）"})
a = W[(W.group == "biz_ordinary") & (W.era == "A")].set_index("fy")
rob.append({"check": "旧い作り方（2000〜2009年度、走行キロから実車率を計算）", "eff_range_2010_2025": f"{a.eff.min():.2f}〜{a.eff.max():.2f}（2000〜2009）",
            "lwl_range": f"{(a.eff / (a.lr_calc / 100)).min():.2f}〜{(a.eff / (a.lr_calc / 100)).max():.2f}", "eff_change_2010_2019": round(float(a.eff.loc[2009] - a.eff.loc[2000]), 2),
            "note": f"表の実車率と計算の実車率の差 最大 {(a.lr - a.lr_calc).abs().max():.2f} ポイント（2000→2009の変化を掲載）"})
ow = W[W.group == "own_ordinary"].set_index("fy").loc[2010:]
rob.append({"check": "自家用普通車", "eff_range_2010_2025": f"{ow.eff.min():.2f}〜{ow.eff.max():.2f}", "lwl_range": f"{ow.load_when_loaded.min():.2f}〜{ow.load_when_loaded.max():.2f}",
            "eff_change_2010_2019": round(float(ow.eff.loc[2019] - ow.eff.loc[2010]), 2), "note": ""})
rob.append({"check": "（計画外）H4 の始点を2011年度に（2010年度は作り方の変更の年で、2011年3月の東北・北海道の一部を含まない）",
            "eff_range_2010_2025": "", "lwl_range": "", "eff_change_2010_2019": round(float(bo.loc[2019, "eff"] - bo.loc[2011, "eff"]), 2), "note": "2011→2019年度の変化"})
robdf = pd.DataFrame(rob); robdf.to_csv(R / "robustness.csv", index=False)

series = {g: {int(y): {k: round(float(v), 2) for k, v in r.items()} for y, r in W[W.group == g].set_index("fy")[["eff", "lr", "load_when_loaded"]].iterrows()}
          for g in ["biz_ordinary", "biz_total", "own_ordinary"]}
main = {
    "hypotheses": hyp,
    "biz_ordinary": series["biz_ordinary"],
    "biz_total_eff": {int(y): round(float(v), 2) for y, v in bt.eff.items()},
    "biz_total_lr_est": {int(y): round(float(v), 2) for y, v in bt_lr.loc[2010:].items()},
    "own_ordinary": series["own_ordinary"],
    "size_mean_2020_2025": {g: {k: round(float(v), 2) for k, v in r.items()} for g, r in size_mean.iterrows()},
    "size_by_year_eff": {g: {int(y): round(float(v), 2) for y, v in W[W.group == g].set_index("fy").eff.items()} for g in sizes},
    "size_by_year_lr": {g: {int(y): round(float(v), 2) for y, v in W[W.group == g].set_index("fy").lr.items()} for g in sizes},
    "decomposition": dec,
    "pub_vs_calc_maxabs": round(float((cc.eff - cc.eff_pub).abs().max()), 3),
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: main[k] for k in ["hypotheses", "biz_ordinary", "biz_total_eff", "size_mean_2020_2025", "decomposition"]}, ensure_ascii=False))
print(robdf.to_string())
