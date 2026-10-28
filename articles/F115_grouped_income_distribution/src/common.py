# F115 共通：階級別の度数（％）から所得の分布を推定し、平均・分位点・五分位の平均・ジニ係数などを計算する
import numpy as np
from scipy import stats, special, optimize
from scipy.interpolate import PchipInterpolator

# 計算用の格子（万円）。0〜3,000万円は0.25万円刻み、その先は対数刻みで10万（=10億円）まで
GRID = np.unique(np.concatenate([np.arange(0, 3000, 0.25), np.geomspace(3000, 1e5, 4000)]))

# 階級の区切り方（上限は開いた階級）。S25 は公表どおり
SCHEMES = {
    'S25': list(range(0, 1001, 50)) + [1100, 1200, 1500, 2000],
    'S14': list(range(0, 1001, 100)) + [1200, 1500, 2000],
    'S8':  [0, 200, 400, 600, 800, 1000, 1500, 2000],
    'S5':  [0, 200, 400, 700, 1000],
    'S3':  [0, 300, 600],
    'S21top1000': list(range(0, 1001, 50)),   # 公表の刻みのまま、1,000万円以上をひとまとめにする
}
SCHEME_LABEL = {'S25': '公表の25階級（50万円刻み）', 'S14': '14階級（100万円刻み）', 'S8': '8階級（200万円刻み）',
                'S5': '5階級', 'S3': '3階級', 'S21top1000': '21階級（1,000万円以上をまとめる）'}


def coarsen(lo, share, cuts):
    """細かい階級の割合を、区切り cuts（下限の並び、最後は開いた階級）に足し上げる"""
    cuts = np.asarray(cuts, float); idx = np.searchsorted(cuts, np.asarray(lo, float), side='right') - 1
    out = np.zeros(len(cuts))
    np.add.at(out, idx, share)
    return out


class Dist:
    """格子の上の累積分布 F（GRID の各点）と、10万万円より先の残り（無視できるか確かめる）を持つ"""
    def __init__(self, F, name):
        F = np.clip(np.maximum.accumulate(np.asarray(F, float)), 0, 1)
        self.F, self.name = F, name
        self.dF = np.diff(F); self.xm = (GRID[1:] + GRID[:-1]) / 2
        self.tail = 1 - F[-1]

    def cdf(self, x):
        return np.interp(x, GRID, self.F)

    def ppf(self, q):
        q = np.atleast_1d(q); F = self.F
        i = np.searchsorted(F, q, side='left').clip(1, len(F) - 1)
        f0, f1 = F[i - 1], F[i]; w = np.where(f1 > f0, (q - f0) / np.where(f1 > f0, f1 - f0, 1), 0)
        return GRID[i - 1] + w * (GRID[i] - GRID[i - 1])

    def summary(self):
        tot = self.F[-1]
        m = np.sum(self.dF * self.xm) / tot
        qs = self.ppf(np.array([.2, .4, .5, .6, .8, .9, .99]) * tot)
        # 五分位の階級の平均：格子のセルを分けながら足す
        cum = np.concatenate([[0], np.cumsum(self.dF)]) / tot
        cm = np.concatenate([[0], np.cumsum(self.dF * self.xm)]) / tot
        def partial(q):  # 下から割合 q までの所得の合計（1世帯あたり）
            i = np.searchsorted(cum, q, side='right').clip(1, len(cum) - 1)
            frac = np.where(cum[i] > cum[i - 1], (q - cum[i - 1]) / np.where(cum[i] > cum[i - 1], cum[i] - cum[i - 1], 1), 0)
            return cm[i - 1] + frac * (cm[i] - cm[i - 1])
        P = partial(np.array([0, .2, .4, .6, .8, 1.0, .9, .99]))
        qmean = [(P[j + 1] - P[j]) / 0.2 for j in range(5)]
        L = cm / cm[-1]; gini = 1 - np.sum(np.diff(cum) * (L[1:] + L[:-1]))
        return dict(mean=m, p20=qs[0], p40=qs[1], median=qs[2], p60=qs[3], p80=qs[4], p90=qs[5], p99=qs[6],
                    **{f'qmean{j+1}': qmean[j] for j in range(5)},
                    **{f'qshare{j+1}': qmean[j] / (5 * m) for j in range(5)},
                    top10=1 - P[6] / P[5], top1=1 - P[7] / P[5], gini=gini, tail_mass=self.tail)


# ---------- パラメトリック：区間の最尤推定 ----------
def gb2_cdf(x, a, b, p, q):
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        z = np.power(np.maximum(x, 0) / b, a)
        u = np.where(np.isinf(z), 1.0, z / (1 + z))
    return special.betainc(p, q, u)

FAMILIES = {
    # name: (パラメータの数, 初期値（対数）, cdf(x, θ))
    'lognorm': (2, [np.log(5.9), np.log(0.8)], lambda x, t: stats.lognorm.cdf(x, np.exp(t[1]), scale=np.exp(t[0]) * 100)),
    'gamma':   (2, [np.log(1.8), np.log(3.0)], lambda x, t: stats.gamma.cdf(x, np.exp(t[0]), scale=np.exp(t[1]) * 100)),
    'singh_maddala': (3, [np.log(2.0), np.log(5.0), np.log(2.0)], lambda x, t: gb2_cdf(x, np.exp(t[0]), np.exp(t[1]) * 100, 1.0, np.exp(t[2]))),
    'dagum':   (3, [np.log(3.0), np.log(5.0), np.log(0.7)], lambda x, t: gb2_cdf(x, np.exp(t[0]), np.exp(t[1]) * 100, np.exp(t[2]), 1.0)),
    'gb2':     (4, [np.log(2.5), np.log(5.0), np.log(1.0), np.log(1.5)], lambda x, t: gb2_cdf(x, np.exp(t[0]), np.exp(t[1]) * 100, np.exp(t[2]), np.exp(t[3]))),
}
FAMILY_LABEL = {'lognorm': '対数正規', 'gamma': 'ガンマ', 'singh_maddala': 'シン・マダラ', 'dagum': 'ダガム', 'gb2': 'GB2',
                'uniform_pareto': '階級内一様＋パレート', 'pchip_pareto': '単調スプライン＋パレート', 'midpoint': '階級の中央の値'}


def fit_param(cuts, shares, fam, init=None):
    k, t0, cdf = FAMILIES[fam]
    s = np.asarray(shares, float); s = s / s.sum()
    b = np.concatenate([np.asarray(cuts, float), [np.inf]])
    def nll(t):
        F = cdf(b, t); F = np.where(np.isinf(b), 1.0, F)
        pr = np.diff(F)
        if not np.all(np.isfinite(pr)): return 1e9
        return -np.sum(s * np.log(np.maximum(pr, 1e-300)))
    best = None
    starts = [np.array(t0)] + [np.array(i) for i in (init or [])]
    for st in starts:
        r = optimize.minimize(nll, st, method='Nelder-Mead', options=dict(maxiter=4000, xatol=1e-7, fatol=1e-10))
        if best is None or r.fun < best.fun: best = r
    F = cdf(GRID, best.x); F[0] = 0
    return Dist(F, fam), best.x, best.fun


def pareto_alpha(cuts, shares):
    """いちばん上の2つの区切り（開いた階級の下限とその1つ下）から、上の裾をパレートと見たときの α"""
    s = np.asarray(shares, float); s = s / s.sum(); c = np.asarray(cuts, float)
    S_top, S_prev = s[-1], s[-1] + s[-2]
    a = np.log(S_prev / S_top) / np.log(c[-1] / c[-2])
    return float(np.clip(a, 1.05, 10))


def _tail(Ftop, xtop, alpha):
    x = GRID[GRID > xtop]
    return 1 - (1 - Ftop) * np.power(xtop / x, alpha)


def fit_uniform_pareto(cuts, shares, alpha=None):
    s = np.asarray(shares, float); s = s / s.sum(); c = np.asarray(cuts, float)
    Fk = np.concatenate([[0], np.cumsum(s[:-1])])
    a = pareto_alpha(cuts, shares) if alpha is None else alpha
    F = np.interp(GRID, c, Fk); m = GRID > c[-1]; F[m] = _tail(Fk[-1], c[-1], a)
    return Dist(F, 'uniform_pareto'), a


def fit_pchip_pareto(cuts, shares, alpha=None):
    s = np.asarray(shares, float); s = s / s.sum(); c = np.asarray(cuts, float)
    Fk = np.concatenate([[0], np.cumsum(s[:-1])])
    a = pareto_alpha(cuts, shares) if alpha is None else alpha
    F = PchipInterpolator(c, Fk)(np.minimum(GRID, c[-1])); m = GRID > c[-1]; F[m] = _tail(Fk[-1], c[-1], a)
    return Dist(F, 'pchip_pareto'), a


def midpoint_summary(cuts, shares, top_mult=1.5):
    """各階級の世帯が全員「階級の中央の値」を持つとみなす素朴な方法（開いた階級は下限の1.5倍）"""
    s = np.asarray(shares, float); s = s / s.sum(); c = np.asarray(cuts, float)
    v = np.concatenate([(c[:-1] + c[1:]) / 2, [c[-1] * top_mult]])
    m = np.sum(s * v)
    cum = np.concatenate([[0], np.cumsum(s)]); cm = np.concatenate([[0], np.cumsum(s * v)])
    P = np.interp([0, .2, .4, .6, .8, 1.0, .9, .99], cum, cm)  # 同じ値の世帯が並ぶので、セルの中は直線でつなぐ
    qmean = [(P[j + 1] - P[j]) / 0.2 for j in range(5)]
    L = cm / cm[-1]; gini = 1 - np.sum(np.diff(cum) * (L[1:] + L[:-1]))
    # 分位点は「その世帯が入る階級の中央の値」
    def q(p): return v[np.searchsorted(cum[1:], p)]
    return dict(mean=m, p20=q(.2), p40=q(.4), median=q(.5), p60=q(.6), p80=q(.8), p90=q(.9), p99=q(.99),
                **{f'qmean{j+1}': qmean[j] for j in range(5)}, **{f'qshare{j+1}': qmean[j] / (5 * m) for j in range(5)},
                top10=1 - P[6] / P[5], top1=1 - P[7] / P[5], gini=gini, tail_mass=0.0)


def estimate_all(cuts, shares, fams=('lognorm', 'gamma', 'singh_maddala', 'dagum', 'gb2'), init=None):
    """すべての方法で推定し、{方法: (要約, 追加情報)} を返す"""
    out, th_of = {}, {}
    for f in fams:
        ini = []
        if f == 'gb2':  # 入れ子になっているシン・マダラ（p=1）とダガム（q=1）の解からも始める（局所解を避ける）
            if 'singh_maddala' in th_of: t = th_of['singh_maddala']; ini.append([t[0], t[1], 0.0, t[2]])
            if 'dagum' in th_of: t = th_of['dagum']; ini.append([t[0], t[1], t[2], 0.0])
        d, th, nll = fit_param(cuts, shares, f, ini)
        th_of[f] = th
        out[f] = (d.summary(), dict(theta=th.tolist(), nll=nll))
    d, a = fit_uniform_pareto(cuts, shares); out['uniform_pareto'] = (d.summary(), dict(alpha=a))
    d, a = fit_pchip_pareto(cuts, shares); out['pchip_pareto'] = (d.summary(), dict(alpha=a))
    out['midpoint'] = (midpoint_summary(cuts, shares), {})
    return out
