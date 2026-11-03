"""F160 共通：パス、年齢区分、コーホート要因法のエンジン（F45 と同じ形）。"""
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
# F45 のフォルダ（社人研2018・2023年推計と2025年国勢調査を整形済み）
F45 = ROOT.parent / "F45_population_projection" / "data"
for p in (DATA, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)

NA = 19                      # 5歳階級 0～4歳 … 85～89歳, 90歳以上
F1549 = list(range(3, 10))   # 子ども女性比の分母：女性15～49歳
F2044 = list(range(4, 9))    # 頑健性：女性20～44歳


def step(pm, pf, sm, sf, mm, mf, cwr, sr, fidx=F1549):
    """5年先へ1期進める。s, m は長さ NA-1（最後は「85歳以上→90歳以上」）。"""
    out = []
    for p, s, m in ((pm, sm, mm), (pf, sf, mf)):
        n = len(p)
        q = np.zeros(n)
        q[1:n - 1] = p[0:n - 2] * (s[0:n - 2] + m[0:n - 2])
        q[n - 1] = (p[n - 2] + p[n - 1]) * (s[n - 2] + m[n - 2])
        out.append(np.clip(q, 0, None))
    qm, qf = out
    b = cwr * qf[fidx].sum()
    qm[0] = b * sr / (100 + sr)
    qf[0] = b * 100 / (100 + sr)
    return qm, qf


def resid_mig(p0m, p0f, p1m, p1f, sm, sf):
    """期首・期末の人口と生残率から、純移動率を残差で出す（長さ NA-1）。"""
    out = []
    for p0, p1, s in ((p0m, p1m, sm), (p0f, p1f, sf)):
        m = np.zeros(NA - 1)
        den = p0[:NA - 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            m[:NA - 2] = np.where(den > 0, p1[1:NA - 1] / den - s[:NA - 2], 0.0)
            d2 = p0[NA - 2] + p0[NA - 1]
            m[NA - 2] = p1[NA - 1] / d2 - s[NA - 2] if d2 > 0 else 0.0
        out.append(m)
    return out


def cwr_of(pm, pf, fidx=F1549):
    f = pf[fidx].sum()
    return ((pm[0] + pf[0]) / f if f > 0 else 0.0), (pm[0] / pf[0] * 100 if pf[0] > 0 else 105.0)
