"""主な分析：テレビとインターネット広告の売上の比、逆転の年（実数と調整済み指数）、媒体の割合、景気の悪い年の落ち込み、仮説、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "annual.csv")
MEDIA = ["newspaper", "magazine", "tv", "radio", "outdoor", "transit", "insert_dm", "overseas", "sp_pr", "internet", "other"]


def r(x, k=1):
    return round(float(x), k)


def tables(pt):
    x = d[d.period_type == pt]
    return x.pivot(index="year", columns="item", values="value"), x.pivot(index="year", columns="item", values="growth")


def chain(g, item, base):
    s = 1 + g[item] / 100
    idx = pd.Series(np.nan, index=g.index); idx[base] = 100.0
    for y in g.index[g.index > base]:
        idx[y] = idx[y - 1] * s[y]
    return idx


v, g = tables("年")
share = v[MEDIA + ["four_media"]].div(v.total, axis=0) * 100
share.round(3).to_csv(R / "share_by_year.csv")
ratio = (v.internet / v.tv)
first_cross = int(ratio[ratio > 1].index.min())
# 指数でつないだ比：2006年の実数の比 × 指数の比
B = 2006
idx = pd.DataFrame({k: chain(g, k, B) for k in ["total", "tv", "internet", "newspaper", "four_media", "sp_pr"]}).loc[B:]
idx.round(3).to_csv(R / "index_2006_100.csv")
ratio_idx = ratio[B] * idx.internet / idx.tv
cross_idx = [int(y) for y in ratio_idx.index if ratio_idx[y] > 1]
t = pd.DataFrame({"tv": v.tv, "internet": v.internet, "ratio_internet_tv": ratio.round(4), "ratio_from_index": ratio_idx.round(4),
                  "tv_growth": g.tv, "internet_growth": g.internet, "total_growth": g.total})
t.to_csv(R / "tv_internet.csv")

Y1 = int(v.index.max())
hyp = {
    "H1": {"first_year_internet_over_tv": first_cross, "verdict": "支持" if first_cross else "外れ"},
    "H2": {"first_year": first_cross, "dentsu_year": 2019, "verdict": "支持" if 2018 <= first_cross <= 2020 else "外れ"},
    "H3": {"g2009": {"tv": float(g.tv[2009]), "internet": float(g.internet[2009])}, "g2020": {"tv": float(g.tv[2020]), "internet": float(g.internet[2020])},
           "verdict": "支持" if (g.internet[2009] > g.tv[2009] and g.internet[2020] > g.tv[2020]) else "外れ"},
    "H4": {"tv_share_2000": r(share.tv[2000]), "tv_share_last": r(share.tv[Y1]), "verdict": "支持" if share.tv[Y1] <= share.tv[2000] / 2 else "外れ"},
}

# 頑健性
vf, gf = tables("年度")
rf = vf.internet / vf.tv
rob = [{"check": "本線：年（実数の比）", "first_cross": first_cross, "ratio_last": r(ratio[Y1], 3)},
       {"check": "年度（4月〜3月、実数の比）", "first_cross": int(rf[rf > 1].index.min()), "ratio_last": r(rf[int(vf.index.max())], 3)},
       {"check": "調整済みの伸びでつないだ比（2006年基点）", "first_cross": min(cross_idx) if cross_idx else None, "ratio_last": r(ratio_idx[Y1], 3)},
       {"check": "インターネット ÷ 4媒体合計 が 0.5 を超えた年", "first_cross": int((v.internet / v.four_media)[(v.internet / v.four_media) > 0.5].index.min()),
        "ratio_last": r(v.internet[Y1] / v.four_media[Y1], 3)}]
sdv = g.loc[2007:Y1, ["tv", "internet", "newspaper", "total"]].std()
rob.append({"check": "前年比の標準偏差（2007〜2024年、ポイント）", "first_cross": None,
            "ratio_last": f"テレビ{sdv.tv:.1f}・インターネット{sdv.internet:.1f}・新聞{sdv.newspaper:.1f}・合計{sdv.total:.1f}"})
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)

main = {
    "year_last": Y1,
    "tv": {str(y): r(v.tv[y] / 1e6, 3) for y in [2000, 2006, 2019, 2020, 2021, 2022, Y1]},
    "internet": {str(y): r(v.internet[y] / 1e6, 3) for y in [2006, 2019, 2020, 2021, 2022, Y1]},
    "total": {str(y): r(v.total[y] / 1e6, 3) for y in [1990, 2000, 2007, 2019, Y1]},
    "ratio": {str(y): r(ratio[y], 3) for y in [2006, 2019, 2020, 2021, 2022, Y1]},
    "ratio_from_index": {str(y): r(ratio_idx[y], 3) for y in [2019, 2020, 2021, 2022, Y1]},
    "share_last": {k: r(share[k][Y1]) for k in MEDIA},
    "share_2006": {k: r(share[k][2006]) for k in MEDIA},
    "share_2000_tv": r(share.tv[2000]), "share_2000_newspaper": r(share.newspaper[2000]),
    "growth": {str(y): {"tv": float(g.tv[y]), "internet": float(g.internet[y]), "total": float(g.total[y])} for y in [2009, 2020, 2021]},
    "index_last": {k: r(idx[k][Y1]) for k in idx.columns},
    "hypotheses": hyp,
    "note": "広告業の企業の売上（百万円、ここでは兆円に換算）。広告主の広告費全体ではない。",
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(hyp, ensure_ascii=False)); print(t.loc[2015:].to_string()); print(pd.read_csv(R / "robustness.csv").to_string())
