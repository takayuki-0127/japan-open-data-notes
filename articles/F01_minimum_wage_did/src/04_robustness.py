"""頑健性チェック → results/robustness.csv, results/permutation.csv

基本形：DID（bite上位半分 × 2016年以降、2008〜2019年）
1. 偽の開始年（プラセボ）：2008〜2015年だけを使い、2012年以降を「処置後」とみなす
2. 県別線形トレンドを入れる
3. 期間を2025年まで延ばす／2020〜22年（コロナ期）を除く
4. 被災3県（岩手・宮城・福島）を除く
5. 連続版（bite 1標準偏差あたり）
6. 別の結果指標：有効求人倍率（職業安定業務統計）
7. wild cluster bootstrap（Rademacher, 999回）の p 値
8. 並べ替え検定：bite の「上位半分」をランダムに入れ替えて2,000回推定した分布
"""
import numpy as np, pandas as pd
from common import panel, fe_ols, wild_cluster_p, RES


def did(d, y, start, treat="high_bite", trends=False, wild=False):
    d = d.copy(); d["tp"] = d[treat] * (d.year >= start)
    m, _, _ = fe_ols(d, y, ["tp"], trends=trends)
    ci = m.conf_int().loc["tp"]
    r = {"delta": m.params["tp"], "se": m.bse["tp"], "lo95": ci[0], "hi95": ci[1], "p_cluster": m.pvalues["tp"], "n": int(m.nobs)}
    r["p_wild"] = wild_cluster_p(d, y, "tp", ["tp"], trends=trends) if wild else np.nan
    return r


def main():
    df = panel()
    df["bite_z"] = (df.bite - df.drop_duplicates("pref").bite.mean()) / df.drop_duplicates("pref").bite.std()
    pre = df[df.year <= 2019]
    checks = [("基本（2008–2019）", pre, 2016, "high_bite", False),
              ("プラセボ：2012年開始とみなす（2008–2015）", df[df.year <= 2015], 2012, "high_bite", False),
              ("県別線形トレンド（2008–2019）", pre, 2016, "high_bite", True),
              ("2025年まで延長", df, 2016, "high_bite", False),
              ("2025年まで・2020–22年を除く", df[~df.year.between(2020, 2022)], 2016, "high_bite", False),
              ("被災3県を除く（2008–2019）", pre[~pre.pref.isin(["岩手", "宮城", "福島"])], 2016, "high_bite", False),
              ("連続版：bite 1標準偏差あたり（2008–2019）", pre, 2016, "bite_z", False)]
    rows = []
    for y in ["emp_rate", "unemp_rate", "jor"]:
        for name, d, s, tr, trend in checks:
            wild = name.startswith("基本") or name.startswith("県別")
            r = did(d, y, s, tr, trend, wild=wild)
            rows.append({"outcome": y, "check": name, **r})
            print(y, name, {k: round(v, 3) for k, v in r.items()})
    pd.DataFrame(rows).round(5).to_csv(RES / "robustness.csv", index=False)

    # 並べ替え検定
    rng = np.random.default_rng(2026)
    prefs = pre.drop_duplicates("pref")["pref"].values
    obs = {y: did(pre, y, 2016)["delta"] for y in ["emp_rate", "unemp_rate"]}
    perm = []
    for i in range(2000):
        hi = set(rng.choice(prefs, 23, replace=False))
        d = pre.assign(fake=pre.pref.isin(hi).astype(int))
        perm.append({"rep": i, **{y: did(d, y, 2016, "fake")["delta"] for y in obs}})
    pm = pd.DataFrame(perm); pm.round(5).to_csv(RES / "permutation.csv", index=False)
    summ = [{"outcome": y, "observed": obs[y], "perm_p_two_sided": float((np.abs(pm[y]) >= abs(obs[y])).mean()),
             "perm_sd": pm[y].std()} for y in obs]
    pd.DataFrame(summ).round(4).to_csv(RES / "permutation_summary.csv", index=False)
    print(pd.DataFrame(summ).round(4))


if __name__ == "__main__":
    main()
