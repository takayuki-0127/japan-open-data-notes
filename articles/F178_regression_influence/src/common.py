from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import OLSInfluence

ROOT = Path(__file__).resolve().parents[1]
DATA, RES, FIG = ROOT / "data", ROOT / "results", ROOT / "figures"
SEED = 178

# F80 の100指標のうち、取り扱わないと決めている題材（犯罪・福祉・事故・乳幼児の死亡・子どもの体格・離婚）は除く
EXCLUDE_PREFIX = ("K", "J")
EXCLUDE_CODES = {"I07101", "I07104", "I07106", "I07201", "I0210104", "A06604", "F08101"}


def ols(y, X):
    """y: Series, X: DataFrame（定数なし）。statsmodels の OLS 結果を返す"""
    return sm.OLS(y, sm.add_constant(X, has_constant="add")).fit()


def influence_table(y, X, focus):
    """1つの回帰について、各県の影響の大きさを表にする"""
    fit = ols(y, X)
    inf = OLSInfluence(fit)
    n, k = len(y), X.shape[1] + 1
    j = list(fit.params.index).index(focus)
    cook = inf.cooks_distance[0]
    dfb = inf.dfbetas[:, j]
    loo = []
    for i in range(n):
        m = np.ones(n, bool); m[i] = False
        f = ols(y[m], X[m])
        loo.append((f.params[focus], f.pvalues[focus]))
    loo = np.array(loo)
    t = pd.DataFrame({"pref": y.index, "cook": cook, "dfbeta": dfb, "leverage": inf.hat_matrix_diag,
                      "stud_resid": inf.resid_studentized_external,
                      "coef_without": loo[:, 0], "p_without": loo[:, 1]})
    t["coef_change"] = t.coef_without - fit.params[focus]
    return fit, t, n, k
