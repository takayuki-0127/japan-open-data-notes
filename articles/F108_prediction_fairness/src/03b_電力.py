"""電力：F92 の東京の1日の最大電力の予測（LightGBM の点予測、2020〜2026年度上期、年度ごとの時系列CV）を使い、
日の種類・気温・季節のグループで外れ方を比べ、区間を全体で決めるかグループ別に決めるかを比べる"""
import numpy as np, pandas as pd
from common import DATA, RES, SEED
d = pd.read_csv(DATA / "power_daily.csv", parse_dates=["date"])
d["r"] = np.log(d["point"]) - np.log(d["actual"])
folds = list(d["fold"].unique())
GDEF = {"daytype": ["平日", "土曜", "日曜・祝日", "連休（盆・年末年始・GW）"],
        "tempq": ["気温1（寒い）", "気温2", "気温3", "気温4", "気温5（暑い）"],
        "season": sorted(d["season"].unique())}


def qcal(df, level, g=None, past_only=True):
    """区間の幅：その年度より前の年度の |外れ| の分位点（最初の年度は評価から外す）。g があればグループ別"""
    q = pd.Series(np.nan, index=df.index)
    for i, f in enumerate(folds):
        te = df.fold == f
        tr = df.fold.isin(folds[:i]) if past_only else (df.fold != f)
        if tr.sum() == 0: continue
        a = df.loc[tr, "r"].abs()
        if g is None:
            q[te] = np.quantile(a, level)
        else:
            for gv in df.loc[te, g].unique():
                m = tr & (df[g] == gv)
                q[te & (df[g] == gv)] = np.quantile(df.loc[m, "r"].abs(), level) if m.sum() >= 20 else np.quantile(a, level)
    return q


rows = []
for setting, past in (("過去の年度だけで幅を決める", True), ("ほかの年度すべてで幅を決める", False)):
    for level in (0.8, 0.9, 0.95):
        for gcol, gs in GDEF.items():
            qa = qcal(d, level, None, past); qg = qcal(d, level, gcol, past)
            ok = qa.notna()
            for gv in ["全体"] + gs:
                m = ok & ((d[gcol] == gv) if gv != "全体" else True)
                r = d.loc[m, "r"]
                rows.append(dict(setting=setting, level=level, group_def=gcol, group=gv, n=int(m.sum()),
                                 mape=np.mean(np.abs(np.exp(r) - 1)), bias=np.exp(r.mean()) - 1,
                                 cover=(r.abs() <= qa[m]).mean(), cover_g=(r.abs() <= qg[m]).mean(),
                                 width=np.exp(2 * qa[m].median()) - 1, width_g=np.exp(2 * qg[m].median()) - 1))
pd.DataFrame(rows).to_csv(RES / "power_group_metrics.csv", index=False)
# 年度ごとのグループ別の偏り（時期で変わるか）
yb = d.groupby(["fold", "daytype"])["r"].mean().apply(lambda v: np.exp(v) - 1).unstack()
yb.to_csv(RES / "power_bias_by_year.csv")
print(pd.DataFrame(rows).query("level==0.9 and setting=='過去の年度だけで幅を決める'").round(3).to_string())
print(yb.round(3))
