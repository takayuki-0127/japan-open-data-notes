"""養殖の割合（量・金額）の推移、割合の変化の分解、1kg あたり産出額、海面養殖の品目群、仮説の判定、頑健性。乱数は使わない。"""
import json, pathlib, sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, share_decomp

RES = ROOT / "results"; D = ROOT / "data"
V = pd.read_csv(D / "volume_sector.csv").set_index("year")
L = pd.read_csv(D / "volume_long.csv").set_index("year")
M = pd.read_csv(D / "value_long.csv").set_index("year")
END = int(V.index.max())

# 推移
ser = pd.DataFrame(index=M.index)
ser["vol_total_t"] = V.total; ser["vol_fish_t"] = V.mf_total + V["if"]; ser["vol_aqua_t"] = V.ma + V.ia
ser["vol_mf_t"] = V.mf_total; ser["vol_ma_t"] = V.ma; ser["vol_if_t"] = V["if"]; ser["vol_ia_t"] = V.ia
ser["val_total_oku"] = M.total / 1e8; ser["val_fish_oku"] = (M.mf + M["if"]) / 1e8; ser["val_aqua_oku"] = (M.ma + M.ia) / 1e8
ser["vol_share_aqua"] = 100 * ser.vol_aqua_t / ser.vol_total_t
ser["val_share_aqua"] = 100 * (M.ma + M.ia) / M.total
ser["vol_share_marine_aqua"] = 100 * V.ma / V.marine_total
ser["val_share_marine_aqua"] = 100 * M.ma / (M.mf + M.ma)
ser["yen_per_kg_fish"] = (M.mf + M["if"]) / ((V.mf_total + V["if"]) * 1000)
ser["yen_per_kg_aqua"] = (M.ma + M.ia) / ((V.ma + V.ia) * 1000)
ser.round(4).to_csv(RES / "national_series.csv")

y_peak = int(V.total.idxmax())
aq = V.ma + V.ia
y_aq_peak = int(aq.idxmax())
y_val_peak = int(M.total.idxmax())

AQ_V = ["ma", "ia"]; FI_V = ["mf_enyo", "mf_okiai", "mf_engan", "if"]
LAB = {"ma": "海面養殖業", "ia": "内水面養殖業", "mf_enyo": "海面漁業・遠洋", "mf_okiai": "海面漁業・沖合", "mf_engan": "海面漁業・沿岸", "if": "内水面漁業", "mf": "海面漁業"}


def vol_dec(a, b, avg=0, aqc=AQ_V, fic=FI_V, frame=None):
    F = V if frame is None else frame
    g = lambda y, cols: F.loc[max(y - avg, F.index.min()):min(y + avg, F.index.max()), cols].mean().to_numpy(float)
    a0, c0, a1, c1 = g(a, aqc), g(a, fic), g(b, aqc), g(b, fic)
    ca, cc = share_decomp(a0, c0, a1, c1)
    s0 = 100 * a0.sum() / (a0.sum() + c0.sum()); s1 = 100 * a1.sum() / (a1.sum() + c1.sum())
    out = {"from": a, "to": b, "s_from": s0, "s_to": s1, "change": s1 - s0, "aqua_part": float(ca.sum()), "fish_part": float(cc.sum()),
           "resid": float(s1 - s0 - ca.sum() - cc.sum())}
    out.update({c: float(v) for c, v in zip(aqc + fic, list(ca) + list(cc))})
    return out


def val_dec(a, b, avg=0, aqc=("ma", "ia"), fic=("mf", "if")):
    aqc, fic = list(aqc), list(fic)
    g = lambda y, cols: M.loc[max(y - avg, M.index.min()):min(y + avg, M.index.max()), cols].mean().to_numpy(float)
    a0, c0, a1, c1 = g(a, aqc), g(a, fic), g(b, aqc), g(b, fic)
    ca, cc = share_decomp(a0, c0, a1, c1)
    s0 = 100 * a0.sum() / (a0.sum() + c0.sum()); s1 = 100 * a1.sum() / (a1.sum() + c1.sum())
    out = {"from": a, "to": b, "s_from": s0, "s_to": s1, "change": s1 - s0, "aqua_part": float(ca.sum()), "fish_part": float(cc.sum()),
           "resid": float(s1 - s0 - ca.sum() - cc.sum())}
    out.update({c: float(v) for c, v in zip(aqc + fic, list(ca) + list(cc))})
    return out


vmain = vol_dec(y_peak, END)
mmain = val_dec(y_peak, END)
dec = [{"measure": "量", "part": LAB[k], "side": "養殖" if k in AQ_V else "漁業", "contrib_pt": round(vmain[k], 4)} for k in AQ_V + FI_V]
dec += [{"measure": "金額", "part": LAB[k], "side": "養殖" if k in ("ma", "ia") else "漁業", "contrib_pt": round(mmain[k], 4)} for k in ["ma", "ia", "mf", "if"]]
pd.DataFrame(dec).to_csv(RES / f"decomp_{y_peak}_{END}.csv", index=False)

# 海面養殖の品目群（金額、2004→END）
GRP = {"魚類": ["ma_fish"], "貝類": ["ma_shell"], "海藻類": ["ma_seaweed"], "真珠": ["ma_pearl"], "その他（くるまえび・ほや類など）": ["ma_kuruma", "ma_hoya", "ma_otherani"]}
B0 = 2004
grp = []
for g_, cols in GRP.items():
    v0 = M.loc[B0, cols].sum() / 1e8; v1 = M.loc[END, cols].sum() / 1e8
    q0 = L.loc[B0, cols].sum() if g_ != "真珠" else np.nan; q1 = L.loc[END, cols].sum() if g_ != "真珠" else np.nan
    grp.append({"group": g_, "val_from_oku": round(v0, 1), "val_to_oku": round(v1, 1), "val_change_oku": round(v1 - v0, 1),
                "vol_from_t": q0, "vol_to_t": q1})
grp = pd.DataFrame(grp)
grp["share_of_change"] = (grp.val_change_oku / grp.val_change_oku.sum()).round(4)
grp.to_csv(RES / f"marine_aqua_groups_{B0}_{END}.csv", index=False)
# 品目（金額）
items = {}
for k, lab in [("ma_fish_buri", "ぶり類"), ("ma_fish_madai", "まだい"), ("ma_fish_ginzake", "ぎんざけ"), ("ma_fish_maguro", "くろまぐろ"),
               ("ma_shell_hotate", "ほたてがい"), ("ma_shell_kaki", "かき類"), ("ma_nori", "のり類"), ("ma_pearl", "真珠")]:
    items[lab] = {"from_oku": round(M.loc[B0, k] / 1e8, 1), "to_oku": round(M.loc[END, k] / 1e8, 1)}
pd.DataFrame(items).T.to_csv(RES / f"marine_aqua_items_{B0}_{END}.csv")

# 仮説
s_peak = float(ser.loc[y_peak, "vol_share_aqua"]); s_end = float(ser.loc[END, "vol_share_aqua"])
m_end = float(ser.loc[END, "val_share_aqua"])
aq_decl = float(aq[END] / aq[y_aq_peak] - 1)
top = grp.loc[grp.val_change_oku.idxmax(), "group"]
hyp = {"H1": {"from": s_peak, "to": s_end, "diff": s_end - s_peak, "verdict": "支持" if s_end - s_peak >= 10 else "外れ"},
       "H2": {"val_share": m_end, "vol_share": s_end, "diff": m_end - s_end, "verdict": "支持" if m_end - s_end >= 10 else "外れ"},
       "H3": {"aqua_peak_year": y_aq_peak, "peak_t": float(aq[y_aq_peak]), "end_t": float(aq[END]), "change": aq_decl, "verdict": "支持" if aq_decl <= -0.2 else "外れ"},
       "H4": {"top_group": top, "verdict": "支持" if top == "魚類" else "外れ"}}

# 頑健性
rob = []
def addv(name, r, m=None):
    rob.append({"check": name, "from": r["from"], "to": r["to"], "vol_s_from": round(r["s_from"], 2), "vol_s_to": round(r["s_to"], 2),
                "vol_change": round(r["change"], 2), "vol_aqua_part": round(r["aqua_part"], 2), "vol_fish_part": round(r["fish_part"], 2),
                "val_s_from": round(m["s_from"], 2) if m else None, "val_s_to": round(m["s_to"], 2) if m else None,
                "val_change": round(m["change"], 2) if m else None, "val_aqua_part": round(m["aqua_part"], 2) if m else None,
                "val_fish_part": round(m["fish_part"], 2) if m else None, "resid": r["resid"]})
addv("本計算", vmain, mmain)
addv("3年平均（前後1年）", vol_dec(y_peak, END, avg=1), val_dec(y_peak, END, avg=1))
addv("海面だけ（内水面を除く）", vol_dec(y_peak, END, aqc=["ma"], fic=["mf_enyo", "mf_okiai", "mf_engan"]), val_dec(y_peak, END, aqc=["ma"], fic=["mf"]))
# 海藻類を除く（量）：養殖から海藻類、海面漁業の沿岸から海藻類（表3）を引く
VS = V.copy()
VS["ma"] = V.ma - L.loc[V.index, "ma_seaweed"]
VS["mf_engan"] = V.mf_engan - L.loc[V.index, "mf_seaweed"]
addv("海藻類を除く（量）", vol_dec(y_peak, END, frame=VS))
addv("起点1990年", vol_dec(1990, END), val_dec(1990, END))
addv("起点2004年", vol_dec(2004, END), val_dec(2004, END))
robdf = pd.DataFrame(rob); robdf.to_csv(RES / "robustness.csv", index=False)

out = {"end": END, "y_peak_total_vol": y_peak, "y_peak_aqua_vol": y_aq_peak, "y_peak_total_val": y_val_peak,
       "vol": {str(y): {k: float(ser.loc[y, k]) for k in ["vol_total_t", "vol_fish_t", "vol_aqua_t", "vol_mf_t", "vol_ma_t", "vol_if_t", "vol_ia_t", "vol_share_aqua", "vol_share_marine_aqua"]} for y in [y_peak, y_aq_peak, 1990, 2004, END]},
       "val": {str(y): {k: float(ser.loc[y, k]) for k in ["val_total_oku", "val_fish_oku", "val_aqua_oku", "val_share_aqua", "val_share_marine_aqua", "yen_per_kg_fish", "yen_per_kg_aqua"]} for y in [y_peak, y_val_peak, 1990, 2004, END]},
       "val_share_1960": float(ser.loc[1960, "val_share_aqua"]),
       "vol_share_max": {"year": int(ser.vol_share_aqua.idxmax()), "value": float(ser.vol_share_aqua.max())},
       "val_share_max": {"year": int(ser.val_share_aqua.idxmax()), "value": float(ser.val_share_aqua.max())},
       "vol_decomp": vmain, "val_decomp": mmain, "hypotheses": hyp, "groups": grp.to_dict("records"), "items": items, "robustness": rob}
def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list): return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)): return None if np.isnan(o) else float(o)
    if isinstance(o, np.integer): return int(o)
    return o
json.dump(clean(out), open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, allow_nan=False)
print(json.dumps({k: out[k] for k in ["y_peak_total_vol", "y_peak_aqua_vol", "y_peak_total_val", "vol_share_max", "val_share_max"]}, ensure_ascii=False))
print(json.dumps(out["vol"], ensure_ascii=False)); print(json.dumps(out["val"], ensure_ascii=False))
print(pd.DataFrame(dec)); print(grp); print(json.dumps(items, ensure_ascii=False))
pd.set_option("display.width", 250); print(robdf.drop(columns="resid"))
print({h: v["verdict"] for h, v in hyp.items()}, hyp["H3"])
