"""割合・構造別の寄与・地方別・頑健性・問い直しを計算し、results/ に書く（オフライン）。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
REGIONS = [("北海道", [1]), ("東北", range(2, 8)), ("関東", range(8, 15)), ("中部", range(15, 24)),
           ("近畿", range(24, 31)), ("中国", range(31, 36)), ("四国", range(36, 40)), ("九州・沖縄", range(40, 48))]
RNAME = [r for r, _ in REGIONS]
REG_OF = {p: r for r, ps in REGIONS for p in ps}
TYPES = [("couple_child", "夫婦と未婚の子のみ"), ("single_parent", "ひとり親と未婚の子のみ"), ("three_gen", "三世代"), ("other", "その他（単独を含む）")]


def r1(x):
    return round(float(x), 1)


def main():
    RES.mkdir(exist_ok=True)
    N = pd.read_csv(ROOT / "data" / "national.csv").set_index("year")
    S = pd.read_csv(ROOT / "data" / "structure.csv").set_index("year")
    P = pd.read_csv(ROOT / "data" / "pref.csv")
    out = {}
    N["share"] = 100 * N.child / N.total
    N["share_c3plus"] = 100 * (N.c3 + N.c4) / N.total
    N.round(2).to_csv(RES / "national.csv")
    out["share"] = {str(y): r1(N.share[y]) for y in (1975, 1986, 1990, 2000, 2010, 2013, 2019, 2023, 2024, 2025)}
    out["count"] = {str(y): int(N.child[y]) for y in (1975, 1986, 2000, 2013, 2025)}
    out["total"] = {str(y): int(N.total[y]) for y in (1975, 1986, 2000, 2013, 2025)}
    out["years_below_20"] = int(N[N.share < 20].index.min())
    # 構造別（2013→2025、千世帯）：「その他の世帯」は単独世帯を含めて第155表と同じ扱いにする
    S["other"] = S.other + S.single
    d = S.loc[2025] - S.loc[2013]
    out["structure"] = {k: dict(label=lab, n2013=int(S.loc[2013, k]), n2025=int(S.loc[2025, k]), diff=int(d[k]), share_of_change=r1(100 * d[k] / d.total),
                                pct=r1(100 * (S.loc[2025, k] / S.loc[2013, k] - 1)), mix2013=r1(100 * S.loc[2013, k] / S.loc[2013, "total"]),
                                mix2025=r1(100 * S.loc[2025, k] / S.loc[2025, "total"])) for k, lab in TYPES}
    out["structure_total"] = dict(n2013=int(S.loc[2013, "total"]), n2025=int(S.loc[2025, "total"]), diff=int(d.total))
    pd.DataFrame(out["structure"]).T.to_csv(RES / "structure_2013_2025.csv")
    # 地方別
    Pp = P[P.pref > 0].copy(); Pp["region"] = Pp.pref.map(REG_OF)
    R = Pp.groupby(["year", "region"])[["households", "child", "couple_child", "single_parent", "three_gen", "other", "census_households", "census_u18"]].sum(min_count=1).reset_index()
    R["share"] = 100 * R.child / R.households
    R["three_gen_share_of_households"] = 100 * R.three_gen / R.households
    R["census_share"] = 100 * R.census_u18 / R.census_households
    W = R.pivot(index="region", columns="year", values="share").reindex(RNAME)
    W["diff"] = W[2025] - W[2013]
    T = R.pivot(index="region", columns="year", values="three_gen_share_of_households").reindex(RNAME)
    C = R[R.year == 2025].set_index("region").census_share.reindex(RNAME)
    tab = pd.DataFrame({"share2013": W[2013], "share2025": W[2025], "diff": W["diff"], "three_gen2013": T[2013], "three_gen2025": T[2025], "census2025": C})
    tab.round(2).to_csv(RES / "region.csv")
    out["region"] = {k: {c: r1(v) for c, v in row.items()} for k, row in tab.iterrows()}
    nat = P[P.pref == 0].set_index("year")
    out["pref_sum_check"] = {str(y): [int(Pp[Pp.year == y].child.sum()), int(nat.child[y])] for y in (2013, 2025)}
    out["census_national_2025"] = r1(100 * nat.census_u18[2025] / nat.census_households[2025])
    rng13, rng25 = W[2013].max() - W[2013].min(), W[2025].max() - W[2025].min()
    rngc = C.max() - C.min()
    h1 = N.share[2025] / N.share[1986]
    h2 = out["structure"]["three_gen"]["share_of_change"]
    out["hypotheses"] = {
        "H1": dict(value=[r1(N.share[1986]), r1(N.share[2025])], verdict="支持" if h1 <= 0.5 else "外れ"),
        "H2": dict(value=h2, verdict="支持" if h2 >= 30 else "外れ"),
        "H3": dict(value=r1(W["diff"].max()), verdict="支持" if (W["diff"] <= -3).all() else "外れ"),
        "H4": dict(value=[r1(rng13), r1(rng25)], verdict="支持" if rng25 < rng13 else "外れ"),
    }
    # 頑健性
    rb = []
    rb.append(dict(check="0 主：国民生活基礎調査（2013→2025年）", result=f"全国 {nat.child[2013]/nat.households[2013]*100:.1f}%→{nat.child[2025]/nat.households[2025]*100:.1f}%、8地方の差（最大−最小）{rng13:.1f}→{rng25:.1f}ポイント"))
    rb.append(dict(check="1 2025年を国勢調査（18歳未満世帯員のいる一般世帯）で", result=f"全国 {out['census_national_2025']:.1f}%、8地方の差 {rngc:.1f}ポイント（国民生活基礎調査は {rng25:.1f}）"))
    rb.append(dict(check="2 児童の定義の変更（2024年）の前後", result=f"2019→2023年 {N.share[2023]-N.share[2019]:+.1f}ポイント（4年）、2023→2025年 {N.share[2025]-N.share[2023]:+.1f}ポイント（2年）。2023→2024年 {N.share[2024]-N.share[2023]:+.1f}"))
    tg = S.loc[2025, "three_gen"] + S.loc[2025, "other"] - S.loc[2013, "three_gen"] - S.loc[2013, "other"]
    rb.append(dict(check="3 H2 を三世代＋その他（単独を含む）で", result=f"減少のうち {100*tg/d.total:.1f}%"))
    rb.append(dict(check="4 世帯総数を1986年のままにした場合の2025年の割合", result=f"{100*N.child[2025]/N.total[1986]:.1f}%（実際は {N.share[2025]:.1f}%）"))
    pd.DataFrame(rb).to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rb
    # 問い直し：割合の低下（1986→2025年）を、児童のいる世帯の減少と世帯総数の増加に分ける
    fixed = 100 * N.child[2025] / N.total[1986]
    out["requestion"] = dict(share1986=r1(N.share[1986]), share2025=r1(N.share[2025]), fixed_denominator=r1(fixed),
                             numerator_pt=r1(fixed - N.share[1986]), denominator_pt=r1(N.share[2025] - fixed),
                             child_pct=r1(100 * (N.child[2025] / N.child[1986] - 1)), total_pct=r1(100 * (N.total[2025] / N.total[1986] - 1)),
                             nochild_diff=int(N.nochild[2025] - N.nochild[1986]))
    # 逆の順（世帯総数の増加を先に）でも
    fixed2 = 100 * N.child[1986] / N.total[2025]
    out["requestion"]["denominator_first_pt"] = r1(fixed2 - N.share[1986])
    out["requestion"]["numerator_second_pt"] = r1(N.share[2025] - fixed2)
    out["requestion"]["numerator_avg_pt"] = r1(((fixed - N.share[1986]) + (N.share[2025] - fixed2)) / 2)
    out["requestion"]["denominator_avg_pt"] = r1(((N.share[2025] - fixed) + (fixed2 - N.share[1986])) / 2)
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("share", "structure", "hypotheses", "requestion", "pref_sum_check", "years_below_20")}, ensure_ascii=False, indent=0)); print(tab.round(2)); print(pd.DataFrame(rb).to_string())


if __name__ == "__main__":
    main()
