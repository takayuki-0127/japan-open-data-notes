"""05 問い直し（結果を見てから足した）：円安のとき、相手の通貨での値段を下げたのはどの局面か。
値段を下げた局面では、数量は増えたのか。

為替の換算の分（円ベース÷契約通貨ベースの対数差）に対して、契約通貨ベースの値段がどれだけ下がったかを
「相手の通貨での値下げの割合」＝ −Δln(契約通貨ベース) ÷ Δln(円ベース÷契約通貨ベース) で表す。
1 なら円安の分をすべて相手の通貨での値下げに回した（円の値段は変わらない）、0 なら相手の通貨の値段は据え置き、
マイナスなら相手の通貨でも値上げした。
"""
import json, pathlib
import numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
P, R = ROOT / "data" / "processed", ROOT / "results"
b = pd.read_csv(P / "boj_monthly.csv", index_col=0)
t = pd.read_csv(P / "trade_index.csv", dtype={"period": str})
b["year"] = b.index.str[:4].astype(int)
CATS = {0: "総平均", 4: "はん用・生産用・業務用機器", 5: "電気・電子機器", 6: "輸送用機器", 2: "化学製品", 3: "金属・同製品"}
def code(base, k): return f"PRCG20_{base}00000000" if k == 0 else f"PRCG20_{base}00{k}20001"
def ya(col, y): return b.loc[b.year == y, col].mean()
def q(y):
    r = t[(t.kind == "CY") & (t.area == "WORLD") & (t.period == str(y))]
    return 100.0 if (r.empty and y == 2020) else float(r.Q.iloc[0])
EPIS = [(2012, 2015, "アベノミクスの円安"), (2020, 2025, "2021年からの円安"), (2021, 2024, "2021〜2024年（円安が最も進んだ期間）")]
rows = []
for y0, y1, nm in EPIS:
    for k, cn in CATS.items():
        py = np.log(ya(code(24, k), y1) / ya(code(24, k), y0)); pc = np.log(ya(code(23, k), y1) / ya(code(23, k), y0))
        fx = py - pc
        rows.append(dict(episode=nm, y0=y0, y1=y1, cat=cn, dFX=fx, dPcc=pc, cut_share=-pc / fx if abs(fx) > 1e-9 else np.nan,
                         Pcc_ratio=np.exp(pc), quantity_ratio=q(y1) / q(y0) if k == 0 else np.nan,
                         usdjpy0=ya("FXERM07", y0), usdjpy1=ya("FXERM07", y1)))
ep = pd.DataFrame(rows); ep.to_csv(R / "F_reask_episodes.csv", index=False)
# 年ごと（総平均）：円安の年（為替の分 > +3%）だけ
yr = []
for y in range(2001, 2027):
    if y == 2026:
        m = b[b.index.str[5:7].astype(int) <= 9]
        py = np.log(m.loc[m.year == 2026, code(24, 0)].mean() / m.loc[m.year == 2025, code(24, 0)].mean())
        pc = np.log(m.loc[m.year == 2026, code(23, 0)].mean() / m.loc[m.year == 2025, code(23, 0)].mean())
    else:
        if y - 1 < 2008: continue
        py = np.log(ya(code(24, 0), y) / ya(code(24, 0), y - 1)); pc = np.log(ya(code(23, 0), y) / ya(code(23, 0), y - 1))
    yr.append(dict(year=y, dFX=py - pc, dPcc=pc, cut_share=-pc / (py - pc)))
yr = pd.DataFrame(yr); yr.to_csv(R / "G_reask_yearly.csv", index=False)
wk = yr[yr.dFX > 0.03]
out = dict(episodes=ep.round(4).to_dict(orient="records"), yen_weak_years=wk.round(4).to_dict(orient="records"))
json.dump(out, open(R / "reask.json", "w"), ensure_ascii=False, indent=1)
print(ep.round(3).to_string()); print(wk.round(3).to_string())
