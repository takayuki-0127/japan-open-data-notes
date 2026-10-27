"""F45 共通の設定と、コーホート要因法のエンジン。"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (DATA, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)

# 5歳階級（0～4歳 … 90～94歳, 95歳～）＝20区分
AGES = [f"{a}～{a+4}歳" for a in range(0, 95, 5)] + ["95歳～"]
NA = len(AGES)  # 20
# 子ども女性比の分母：2023年推計は女性20～44歳（階級4～8）、2018・2013年推計は女性15～49歳（階級3～9）
F2044 = list(range(4, 9))
F1549 = list(range(3, 10))


def project_step(pm, pf, sm, sf, mm, mf, cwr, sr, fidx=F2044):
    """5年先の男女・年齢別人口を1期だけ進める（社人研の地域推計と同じ形）。

    pm, pf : 期首の男女別人口（長さ n。最後は開いた階級）
    sm, sf : 生残率（長さ n-1。最後は「1つ下の階級以上 → 最後の階級」）
    mm, mf : 純移動率（長さ n-1、生残率と同じ並び）
    cwr    : 子ども女性比（期末の0～4歳 ÷ 期末の女性の出産年齢人口）
    sr     : 0～4歳性比（女100に対する男）
    fidx   : 子ども女性比の分母にする女性の年齢階級
    戻り値 : 期末の男女別人口（長さ n）
    """
    out = []
    for p, s, m in ((pm, sm, mm), (pf, sf, mf)):
        n = len(p)
        q = np.zeros(n)
        # 5～9歳 … 最後から2番目の階級：1つ下の階級から
        q[1:n - 1] = p[0:n - 2] * (s[0:n - 2] + m[0:n - 2])
        # 最後の開いた階級（95歳～ または 90歳以上）：1つ下の階級と自分自身から
        q[n - 1] = (p[n - 2] + p[n - 1]) * (s[n - 2] + m[n - 2])
        out.append(q)
    qm, qf = out
    births = cwr * qf[fidx].sum()
    qm[0] = births * sr / (100 + sr)
    qf[0] = births * 100 / (100 + sr)
    return qm, qf


def project(pm, pf, steps, fidx=F2044):
    """steps: [(sm, sf, mm, mf, cwr, sr), ...] を順に当てて、各期の男女別人口を返す。"""
    res = [(np.asarray(pm, float), np.asarray(pf, float))]
    for st in steps:
        res.append(project_step(*res[-1], *st, fidx=fidx))
    return res
