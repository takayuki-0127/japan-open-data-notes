"""主な分析：業務の種類ごとの売上の割合、調整済みの前年比でつないだ指数、仮説、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "annual.csv")
SHARE_ITEMS = ["custom", "custom_si", "products", "products_game", "processing", "sys_mgmt", "other"]
LABEL = {"custom": "受注ソフトウェア", "custom_si": "うちSI", "products": "ソフトウェアプロダクツ", "products_game": "うちゲームソフト",
         "processing": "計算事務等情報処理", "sys_mgmt": "システム等管理運営受託", "other": "その他（キーパンチ・情報提供など）",
         "custom_ex_si": "受注ソフト（SIを除く）", "products_ex_game": "プロダクツ（ゲームを除く）", "total": "売上高合計"}


def r(x, k=1):
    return round(float(x), k)


def tables(ptype):
    x = d[d.period_type == ptype]
    v = x.pivot(index="year", columns="item", values="value")
    g = x.pivot(index="year", columns="item", values="growth")
    v["other"] = v["total"] - v[["software_total", "processing", "sys_mgmt"]].sum(axis=1) - v["keypunch"].fillna(0)
    v["custom_ex_si"] = v["custom"] - v["custom_si"]
    v["products_ex_game"] = v["products"] - v["products_game"]
    share = v.div(v["total"], axis=0) * 100
    return v, g, share


def chain(g, item, base=2000):
    s = (1 + g[item] / 100)
    idx = pd.Series(np.nan, index=g.index)
    idx[base] = 100.0
    for y in g.index[g.index > base]:
        idx[y] = idx[y - 1] * s[y]
    for y in sorted(g.index[g.index < base], reverse=True):
        idx[y] = idx[y + 1] / s[y + 1]
    return idx


def cagr(g, item, y0, y1):
    s = (1 + g[item].loc[y0 + 1:y1] / 100)
    return r((s.prod() ** (1 / (y1 - y0)) - 1) * 100, 2)


v, g, share = tables("年")
sh = share.loc[1994:, ["custom", "custom_si", "products", "products_game", "processing", "sys_mgmt", "other", "custom_ex_si", "products_ex_game"]].round(2)
sh.to_csv(R / "share_by_year.csv")
idx = pd.DataFrame({k: chain(g, k) for k in ["total", "custom", "custom_si", "products", "products_game", "processing", "sys_mgmt", "software_total"]}).loc[2000:].round(2)
idx.to_csv(R / "index_2000_100.csv")

Y0, Y1 = 2000, int(v.index.max())
hyp = {
    "H1": {"custom_2000": r(share.custom[Y0]), "custom_last": r(share.custom[Y1]),
           "verdict": "支持" if share.custom[Y1] < share.custom[Y0] else "外れ"},
    "H2": {"products_2000": r(share.products[Y0]), "products_last": r(share.products[Y1]),
           "verdict": "支持" if share.products[Y1] > share.products[Y0] else "外れ"},
    "H3": {"sys_mgmt_2000": r(share.sys_mgmt[Y0]), "sys_mgmt_last": r(share.sys_mgmt[Y1]),
           "verdict": "支持" if share.sys_mgmt[Y1] > share.sys_mgmt[Y0] else "外れ"},
    "H4": {"cagr_custom_2014_last": cagr(g, "custom", 2014, Y1), "cagr_total_2014_last": cagr(g, "total", 2014, Y1),
           "verdict": "支持" if cagr(g, "custom", 2014, Y1) < cagr(g, "total", 2014, Y1) else "外れ"},
}

# 頑健性
rob = []
vf, gf, shf = tables("年度")
Yf = int(vf.index.max())
for item in ["custom", "products", "sys_mgmt", "custom_ex_si", "products_ex_game", "processing"]:
    rob.append({"item": LABEL[item],
                "share_2000": r(share[item][Y0]), "share_last": r(share[item][Y1]),
                "share_fy2000": r(shf[item][Y0]), "share_fy_last": r(shf[item][Yf]),
                "share_2009": r(share[item][2009]), "share_2009_last": r(share[item][Y1]),
                "cagr_2000_last": cagr(g, item, Y0, Y1) if item in g else None,
                "cagr_2009_last": cagr(g, item, 2009, Y1) if item in g else None})
# 指数から割合を計算し直す（2000年の割合 × 指数の比）
idx_share = {k: r(share[k][Y0] * idx[k][Y1] / idx["total"][Y1]) for k in ["custom", "products", "sys_mgmt", "processing", "custom_si", "products_game"]}
rb = pd.DataFrame(rob)
inv = {v_: k for k, v_ in LABEL.items()}
rb["share_last_from_index"] = [idx_share.get(inv[x]) for x in rb["item"]]
rb.to_csv(R / "robustness.csv", index=False)

main = {
    "years": [Y0, Y1], "last_fy": Yf,
    "total_2000_trillion": r(v.total[Y0] / 1e6, 2), "total_last_trillion": r(v.total[Y1] / 1e6, 2),
    "custom_last_trillion": r(v.custom[Y1] / 1e6, 2), "si_last_trillion": r(v.custom_si[Y1] / 1e6, 2),
    "products_last_trillion": r(v.products[Y1] / 1e6, 2), "sys_mgmt_last_trillion": r(v.sys_mgmt[Y1] / 1e6, 2),
    "share_2000": {k: r(share[k][Y0]) for k in SHARE_ITEMS},
    "share_last": {k: r(share[k][Y1]) for k in SHARE_ITEMS},
    "share_custom_min": {"year": int(share.custom.loc[2000:].idxmin()), "value": r(share.custom.loc[2000:].min())},
    "share_custom_max": {"year": int(share.custom.loc[2000:].idxmax()), "value": r(share.custom.loc[2000:].max())},
    "share_si_in_custom_2000": r(100 * v.custom_si[Y0] / v.custom[Y0]), "share_si_in_custom_last": r(100 * v.custom_si[Y1] / v.custom[Y1]),
    "share_custom_1994": r(share.custom[1994]), "share_products_1994": r(share.products[1994]),
    "index_last": {k: r(idx[k][Y1]) for k in idx.columns},
    "cagr_2000_last": {k: cagr(g, k, Y0, Y1) for k in ["total", "custom", "custom_si", "products", "products_game", "processing", "sys_mgmt"]},
    "cagr_2014_last": {k: cagr(g, k, 2014, Y1) for k in ["total", "custom", "custom_si", "products", "products_game", "processing", "sys_mgmt"]},
    "share_from_index_last": idx_share,
    "hypotheses": hyp,
    "note": "割合は同じ年の実数の比。伸びは調整済みの前年比（不連続を調整したもの）をつないだもの。",
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
