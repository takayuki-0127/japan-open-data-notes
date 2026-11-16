"""問い直し：エルニーニョの夏の差は、どの月で出ているのか。始まりの年と終わりかけの年で違うのか。
H2 で北日本と東日本・西日本の差がほとんど同じだったので、地方ではなく「月」と「エルニーニョの段階」で見直す。"""
import json, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RES = os.path.join(HERE, "..", "results")
s = pd.read_csv(os.path.join(DATA, "summer.csv"), index_col=0)
REG = ["北日本", "東日本", "西日本", "沖縄・奄美"]
NPERM = 10000


def detrend_lin(y):
    x = y.index.values.astype(float)
    return y - np.polyval(np.polyfit(x, y.values, 1), x)


def perm_p(a, b, seed):
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a), np.asarray(b)
    obs = a.mean() - b.mean(); pool = np.concatenate([a, b]); na = len(a); cnt = 0
    for _ in range(NPERM):
        rng.shuffle(pool)
        if abs(pool[:na].mean() - pool[na:].mean()) >= abs(obs) - 1e-12:
            cnt += 1
    return (cnt + 1) / (NPERM + 1)


el, la = s["elnino_summer"], s["lanina_summer"]
neu = (el == 0) & (la == 0)

# 1) 月別（15地点の地方平均を4地方で平均したもの）
rows = []
for i, m in enumerate(("t6", "t7", "t8")):
    v = detrend_lin(s[[f"{rg}_{m}" for rg in REG]].mean(axis=1))
    rows.append({"month": {"t6": "6月", "t7": "7月", "t8": "8月"}[m],
                 "diff_el_neu": round(float(v[el == 1].mean() - v[neu].mean()), 3),
                 "p_el": round(perm_p(v[el == 1], v[neu], 200 + i), 3),
                 "diff_la_neu": round(float(v[la == 1].mean() - v[neu].mean()), 3)})
mon = pd.DataFrame(rows)
mon.to_csv(os.path.join(RES, "requestion_month.csv"), index=False)

# 2) 段階：その夏にエルニーニョがあり、前の冬にもあった（続いている・終わりかけ）か、前の冬にはなかった（始まりの年）か
res = detrend_lin(s["jp_jja"])
onset = (el == 1) & (s["elnino_prev_winter"] == 0)
cont = (el == 1) & (s["elnino_prev_winter"] == 1)
after = (el == 0) & (s["elnino_prev_winter"] == 1)  # 前の冬にあって、夏には終わっていた
ph = []
for lab, mask, sd in (("始まりの年の夏", onset, 300), ("前の冬から続く夏", cont, 301), ("前の冬にあり、夏には終わった", after, 302)):
    ph.append({"phase": lab, "n": int(mask.sum()), "years": [int(y) for y in s.index[mask]],
               "mean_resid": round(float(res[mask].mean()), 3),
               "diff_vs_neutral": round(float(res[mask].mean() - res[neu & ~after].mean()), 3),
               "p": round(perm_p(res[mask], res[neu & ~after], sd), 3)})
phd = pd.DataFrame(ph)
phd.drop(columns="years").to_csv(os.path.join(RES, "requestion_phase.csv"), index=False)

out = {"month": rows, "phase": ph, "neutral_ref_n": int((neu & ~after).sum()),
       "neutral_ref_mean": round(float(res[neu & ~after].mean()), 3)}
with open(os.path.join(RES, "requestion.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))
