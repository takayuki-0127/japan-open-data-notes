"""水準未満の割合、世帯人員の構成で分解、借家、地方別、頑健性、問い直し。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
SZ = ["1人", "2人", "3人", "4人", "5人", "6人以上"]
REGIONS = [("北海道", [1]), ("東北", range(2, 8)), ("関東", range(8, 15)), ("中部", range(15, 24)),
           ("近畿", range(24, 31)), ("中国", range(31, 36)), ("四国", range(36, 40)), ("九州・沖縄", range(40, 48))]
KANTO = list(range(8, 15))


def r(x, k=2):
    return None if x is None or pd.isna(x) else round(float(x), k)


def share(df, unknown_in_denominator=False):
    den = df.total if unknown_in_denominator else (df.above + df.below)
    return 100 * df.below / den


def decompose(nat, y0, y1, cells=("総数",)):
    """cells：所有の関係の区分。('総数',) なら世帯人員6区分、('持ち家','借家') なら12区分。"""
    def tab(y):
        s = nat[(nat.year == y) & nat.tenure.isin(cells) & nat["size"].isin(SZ)].copy()
        s["n"] = s.above + s.below
        s["rate"] = s.below / s.n
        s["w"] = s.n / s.n.sum()
        return s.set_index(["tenure", "size"])
    a, b = tab(y0), tab(y1)
    comp = ((b.w - a.w) * a.rate).sum() * 100
    within = (b.w * (b.rate - a.rate)).sum() * 100
    return dict(total=r((b.w * b.rate).sum() * 100 - (a.w * a.rate).sum() * 100, 3), composition=r(comp, 3), within=r(within, 3))


def main():
    nat = pd.read_csv(DATA / "national.csv")
    pref = pd.read_csv(DATA / "pref.csv")
    nat["share"] = share(nat)
    nat["share_all"] = share(nat, True)
    nat.round(4).to_csv(RES / "national_shares.csv", index=False)
    out = {}
    T = nat[nat["size"] == "総数"].pivot(index="year", columns="tenure", values="share")
    out["share_by_tenure"] = {int(y): {t: r(v) for t, v in row.items()} for y, row in T.iterrows()}
    out["below_count"] = {int(y): r(v, 0) for y, v in nat[(nat.tenure == "総数") & (nat["size"] == "総数")].set_index("year").below.items()}
    S = nat[(nat.tenure == "総数") & nat["size"].isin(SZ)].pivot(index="year", columns="size", values="share")[SZ]
    out["share_by_size"] = {int(y): {s: r(v) for s, v in row.items()} for y, row in S.iterrows()}
    comp = nat[(nat.tenure == "総数") & nat["size"].isin(SZ)].copy()
    comp["n"] = comp.above + comp.below
    comp["w"] = comp.n / comp.groupby("year").n.transform("sum") * 100
    out["size_composition"] = {int(y): {s: r(v, 1) for s, v in g.set_index("size").w.items()} for y, g in comp.groupby("year")}
    d = decompose(nat, 2008, 2023)
    out["decomposition_2008_2023"] = d

    # 地方別
    pref["share"] = share(pref)
    reg = {}
    for name, nos in REGIONS:
        reg[name] = {}
        for y in (2008, 2013, 2018, 2023):
            s = pref[(pref.year == y) & pref.pref.isin(list(nos))]
            reg[name][y] = 100 * s.below.sum() / (s.above.sum() + s.below.sum())
    R = pd.DataFrame(reg).T
    R.round(3).to_csv(RES / "region_shares.csv")
    out["regions"] = {a: {int(y): r(v) for y, v in row.items()} for a, row in R.iterrows()}
    top08, top23 = R[2008].idxmax(), R[2023].idxmax()
    # 合計の確かめ
    chk = {int(y): r(100 * (g.total.sum() / nat[(nat.year == y) & (nat.tenure == "総数") & (nat["size"] == "総数")].total.iloc[0] - 1), 3) for y, g in pref.groupby("year")}
    out["pref_sum_vs_national_pct"] = chk

    # 頑健性
    rob = []
    for y0, y1 in [(2008, 2023), (2013, 2023), (2008, 2018)]:
        dd = decompose(nat, y0, y1)
        rob.append(dict(check=f"1 期間 {y0}→{y1}年（6区分）", total=dd["total"], composition=dd["composition"], within=dd["within"],
                        rent_change=r(T.loc[y1, "借家"] - T.loc[y0, "借家"])))
    dd = decompose(nat, 2008, 2023, cells=("持ち家", "借家"))
    rob.append(dict(check="2 所有の関係×世帯人員の12区分（2008→2023年）", total=dd["total"], composition=dd["composition"], within=dd["within"], rent_change=None))
    Ta = nat[nat["size"] == "総数"].pivot(index="year", columns="tenure", values="share_all")
    rob.append(dict(check="3 分母に不詳を入れる（2008→2023年、全体の割合の変化）", total=r(Ta.loc[2023, "総数"] - Ta.loc[2008, "総数"], 3),
                    composition=None, within=None, rent_change=r(Ta.loc[2023, "借家"] - Ta.loc[2008, "借家"])))
    P = pref.pivot(index="pref", columns="year", values="share")
    k_med = {y: r(P.loc[KANTO, y].median()) for y in (2008, 2023)}
    o_med = {y: r(P.loc[[i for i in P.index if i not in KANTO], y].median()) for y in (2008, 2023)}
    rob.append(dict(check="4 関東の1都6県の中央値／ほかの県の中央値（2008年、2023年）", total=f"{k_med[2008]}／{o_med[2008]}、{k_med[2023]}／{o_med[2023]}",
                    composition=None, within=None, rent_change=None))
    n_pref_down = int((P[2023] < P[2008]).sum())
    rob.append(dict(check="5 都道府県で数える（2008→2023年に割合が下がった県の数／47）", total=n_pref_down, composition=None, within=None, rent_change=None))
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rob.astype(object).where(rob.notna(), None).to_dict(orient="records")

    # 問い直し：水準未満の世帯のうち、借家の1人世帯の割合
    rq = {}
    for y in (2008, 2013, 2018, 2023):
        s = nat[nat.year == y]
        tot = s[(s.tenure == "総数") & (s["size"] == "総数")].below.iloc[0]
        r1 = s[(s.tenure == "借家") & (s["size"] == "1人")].below.iloc[0]
        a1 = s[(s.tenure == "総数") & (s["size"] == "1人")].below.iloc[0]
        rq[y] = dict(rent_single=r(100 * r1 / tot, 1), all_single=r(100 * a1 / tot, 1), rent_single_count=r(r1, 0),
                     rent_single_rate=r(s[(s.tenure == "借家") & (s["size"] == "1人")].share.iloc[0]),
                     rent_single_households=r(s[(s.tenure == "借家") & (s["size"] == "1人")][["above", "below"]].sum(axis=1).iloc[0], 0))
    out["requestion"] = rq
    pd.DataFrame(rq).T.to_csv(RES / "requestion_rent_single.csv")

    out["hypotheses"] = {
        "H1": dict(value=r(T.loc[2023, "総数"] - T.loc[2008, "総数"], 3), verdict="支持" if abs(T.loc[2023, "総数"] - T.loc[2008, "総数"]) <= 1 else "外れ"),
        "H2": dict(value=[d["within"], d["composition"]], verdict="支持" if (d["within"] < 0 and d["composition"] > 0 and d["composition"] >= 0.3 * abs(d["within"])) else "外れ"),
        "H3": dict(value=r(T.loc[2023, "借家"] - T.loc[2008, "借家"]), verdict="支持" if T.loc[2023, "借家"] - T.loc[2008, "借家"] <= -1 else "外れ"),
        "H4": dict(value=[top08, top23], verdict="支持" if top08 == "関東" and top23 == "関東" else "外れ"),
    }
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
