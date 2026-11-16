"""03 分析：府県の中の乗合バスの輸送人員の変化、人口と1人あたりへの分け方、感染症の時期の落ち込みと戻り"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
METRO = ["埼玉", "千葉", "東京", "神奈川", "岐阜", "愛知", "三重", "京都", "大阪", "兵庫", "奈良"]


def load(var="within", pop="gen_p", drop=()):
    d = pd.read_csv(ROOT / "data" / "panel.csv")
    d = d[(d.pref != "全国") & (~d.pref.isin(drop))].copy()
    d["area"] = np.where(d.pref.isin(METRO), "三大都市圏", "地方圏")
    d["v"] = d[var]; d["pop"] = d[pop]
    return d


def area_series(d):
    a = d.groupby(["area", "year"])[["v", "pop"]].sum().reset_index()
    t = d.groupby("year")[["v", "pop"]].sum().reset_index().assign(area="全国")
    return pd.concat([a, t], ignore_index=True)


def decomp(a, y0, y1):
    out = {}
    for ar, g in a.groupby("area"):
        g = g.set_index("year")
        v0, v1, p0, p1 = g.v[y0], g.v[y1], g["pop"][y0], g["pop"][y1]
        lv = np.log(v1 / v0); lp = np.log(p1 / p0)
        out[ar] = dict(chg=float(100 * (v1 / v0 - 1)), pop_chg=float(100 * (p1 / p0 - 1)),
                       percap_chg=float(100 * ((v1 / p1) / (v0 / p0) - 1)),
                       share_pop=float(lp / lv) if lv != 0 else np.nan,
                       percap0=float(v0 / p0), percap1=float(v1 / p1))
    return out


def summarize(d, label, y0=2000, y1=2019):
    a = area_series(d)
    dc = decomp(a, y0, y1)
    g = a.set_index(["area", "year"]).v
    rec = {ar: dict(drop2020=float(100 * (g[ar, 2020] / g[ar, 2019] - 1)), rec2024=float(100 * g[ar, 2024] / g[ar, 2019]))
           for ar in ["三大都市圏", "地方圏", "全国"]}
    return dict(label=label, y0=y0, y1=y1,
                local_chg=dc["地方圏"]["chg"], local_share_pop=dc["地方圏"]["share_pop"], local_percap=dc["地方圏"]["percap_chg"],
                local_pop=dc["地方圏"]["pop_chg"],
                metro_chg=dc["三大都市圏"]["chg"], metro_percap=dc["三大都市圏"]["percap_chg"], metro_pop=dc["三大都市圏"]["pop_chg"],
                local_2024=rec["地方圏"]["rec2024"], metro_2024=rec["三大都市圏"]["rec2024"],
                local_2020=rec["地方圏"]["drop2020"], metro_2020=rec["三大都市圏"]["drop2020"]), a, dc


def main():
    d = load()
    m, a, dc = summarize(d, "基本（府県の中の移動、一般世帯人員、2000→2019年度）")
    a["percap"] = a.v / a["pop"]
    a.round(4).to_csv(RES / "area_series.csv", index=False)
    # 府県ごと
    p = d.pivot(index="pref", columns="year", values="v")
    pp = d.pivot(index="pref", columns="year", values="pop")
    pr = pd.DataFrame({"area": d.drop_duplicates("pref").set_index("pref").area,
                       "chg_00_19": 100 * (p[2019] / p[2000] - 1), "pop_chg_00_19": 100 * (pp[2019] / pp[2000] - 1),
                       "percap_2019": p[2019] / pp[2019], "rec_2024": 100 * p[2024] / p[2019]})
    pr.round(4).to_csv(RES / "pref_change.csv")
    rob = [m]
    rob.append(summarize(load("from_total"), "府県から出る合計（府県の外へ行く分も含む）")[0])
    rob.append(summarize(d, "2000→2009年度", 2000, 2009)[0])
    rob.append(summarize(d, "2010→2019年度", 2010, 2019)[0])
    rob.append(summarize(load(drop=("東京", "大阪")), "東京都・大阪府を除く")[0])
    rob.append(summarize(load(pop="total_p"), "人口を総人口で")[0])
    R = pd.DataFrame(rob)
    R.round(4).to_csv(RES / "robustness.csv", index=False)
    # 問い直し：府県ごとの人口の変化と、1人あたりの利用の変化の関係（地方圏）
    L = pr[pr.area == "地方圏"].copy()
    L["percap_chg"] = 100 * ((1 + L.chg_00_19 / 100) / (1 + L.pop_chg_00_19 / 100) - 1)
    rho = float(L[["pop_chg_00_19", "percap_chg"]].corr(method="spearman").iloc[0, 1])
    out = dict(main=m, decomp=dc, n_local_down=int((L.chg_00_19 < 0).sum()), n_local=int(len(L)),
               local_chg_median=float(L.chg_00_19.median()), rho_pop_percap=rho,
               n_local_percap_down=int((L.percap_chg < 0).sum()),
               national_2000=float(a[(a.area == "全国") & (a.year == 2000)].v.iloc[0]),
               national_2019=float(a[(a.area == "全国") & (a.year == 2019)].v.iloc[0]),
               national_2024=float(a[(a.area == "全国") & (a.year == 2024)].v.iloc[0]))
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(R.round(2).to_string())


if __name__ == "__main__":
    main()
