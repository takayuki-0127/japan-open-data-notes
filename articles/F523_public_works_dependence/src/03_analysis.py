"""主な分析：公共工事の出来高÷県内総生産を県ごと・年度ごとに。地方圏と三大都市圏、水準と変化の相関、災害復旧の割合。仮説と頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "pref_year.csv", dtype={"code": str})
METRO = ["埼玉県", "千葉県", "東京都", "神奈川県", "岐阜県", "愛知県", "三重県", "京都府", "大阪府", "兵庫県", "奈良県"]
QUAKE = ["岩手県", "宮城県", "福島県"]
d["area"] = np.where(d.pref.isin(METRO), "三大都市圏", "地方圏")
d["ratio"] = 100 * d.public / d.gdp                      # 公共工事÷県内総生産（%）
d["ratio_exdis"] = 100 * (d.public - d.disaster) / d.gdp  # 災害復旧を除く
d["share_total"] = 100 * d.public / d.total              # 建設の出来高に占める公共の割合
d["disaster_share"] = 100 * d.disaster / d.public4
d.to_csv(R / "pref_year_ratio.csv", index=False, float_format="%.4f")
Y = [1996, 2005, 2015, 2023]


def r(x, k=2):
    return round(float(x), k)


nat = d.groupby("year")[["public", "gdp", "total", "disaster", "public4"]].sum()
nat["ratio"] = 100 * nat.public / nat.gdp
nat["share_total"] = 100 * nat.public / nat.total
nat["disaster_share"] = 100 * nat.disaster / nat.public4
nat.round(3).to_csv(R / "national.csv")
ar = d.groupby(["year", "area"]).agg(median=("ratio", "median"), share_median=("share_total", "median"), exdis_median=("ratio_exdis", "median")).round(3)
ar.to_csv(R / "by_area.csv")
w = d.pivot(index=["code", "pref"], columns="year", values="ratio").reset_index()
w.columns = ["code", "pref"] + [f"r{y}" for y in Y]
w["chg"] = w.r2023 - w.r1996
w.to_csv(R / "pref_wide.csv", index=False, float_format="%.3f")


def gap(y, col="median"):
    return float(ar.loc[(y, "地方圏"), col] - ar.loc[(y, "三大都市圏"), col])


rc = stats.pearsonr(w.r1996, w.chg)[0]
dec = 1 - nat.loc[2023, "ratio"] / nat.loc[1996, "ratio"]
g96, g23 = gap(1996), gap(2023)
hyp = {
    "H1": {"nat_1996": r(nat.loc[1996, "ratio"]), "nat_2023": r(nat.loc[2023, "ratio"]), "decline_pct": r(100 * dec, 1), "verdict": "支持" if dec >= 1 / 3 else "外れ"},
    "H2": {"gap_1996": r(g96), "gap_2023": r(g23), "shrink_pct": r(100 * (1 - g23 / g96), 1), "verdict": "支持" if g23 <= 0.7 * g96 else "外れ"},
    "H3": {"r_level_change": r(rc, 3), "verdict": "支持" if rc <= -0.5 else "外れ"},
    "H4": {"disaster_share_1996": r(nat.loc[1996, "disaster_share"]), "disaster_share_2023": r(nat.loc[2023, "disaster_share"]),
           "verdict": "支持" if nat.loc[2023, "disaster_share"] > nat.loc[1996, "disaster_share"] else "外れ"},
}
nq = w[~w.pref.isin(QUAKE)]
rob = [
    {"check": "本線：地方圏と三大都市圏の中央値の差（pt）1996→2023", "v_start": r(g96), "v_end": r(g23)},
    {"check": "建設の出来高に占める公共の割合で（中央値の差、pt）", "v_start": r(gap(1996, "share_median")), "v_end": r(gap(2023, "share_median"))},
    {"check": "災害復旧を除く（中央値の差、pt）", "v_start": r(gap(1996, "exdis_median")), "v_end": r(gap(2023, "exdis_median"))},
    {"check": "起点を2005年度に（中央値の差、pt）2005→2023", "v_start": r(gap(2005)), "v_end": r(g23)},
    {"check": "水準と変化の相関：本線（47県）", "v_start": r(rc, 3), "v_end": None},
    {"check": "水準と変化の相関：岩手・宮城・福島を除く", "v_start": r(stats.pearsonr(nq.r1996, nq.chg)[0], 3), "v_end": None},
    {"check": "水準と変化の相関：順位（スピアマン）", "v_start": r(stats.spearmanr(w.r1996, w.chg)[0], 3), "v_end": None},
    {"check": "県ごとの割合のばらつき（標準偏差、pt）", "v_start": r(w.r1996.std()), "v_end": r(w.r2023.std())},
    {"check": "全国：建設の出来高に占める公共の割合（%）", "v_start": r(nat.loc[1996, "share_total"]), "v_end": r(nat.loc[2023, "share_total"])},
]
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
up = w[w.chg > 0]
main = {"national_ratio": {str(y): r(nat.loc[y, "ratio"]) for y in Y}, "national_share_total": {str(y): r(nat.loc[y, "share_total"], 1) for y in Y},
        "national_public_trillion": {str(y): r(nat.loc[y, "public"] / 1e6, 1) for y in Y},
        "area_median": {f"{y}_{a}": r(ar.loc[(y, a), "median"]) for y in Y for a in ["地方圏", "三大都市圏"]},
        "n_up_1996_2023": int(len(up)), "up_prefs": up.pref.tolist(),
        "median_ratio": {str(y): r(w[f"r{y}"].median()) for y in Y},
        "max_1996": r(w.r1996.max()), "max_2023": r(w.r2023.max()), "min_1996": r(w.r1996.min()), "min_2023": r(w.r2023.min()),
        "slope_level_change": r(np.polyfit(w.r1996, w.chg, 1)[0], 3),
        "hypotheses": hyp}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(nat.round(2).to_string()); print(ar.to_string()); print(json.dumps(main, ensure_ascii=False, indent=1)); print(pd.DataFrame(rob).to_string())
print(w.round(1).to_string())
