"""06 仮説の判定と主な数字を results/main.json にまとめる。"""
import os, json, numpy as np, pandas as pd
B = os.path.join(os.path.dirname(__file__), '..'); R = os.path.join(B, 'results')
real = pd.read_csv(os.path.join(R, 'B_real_vs_band.csv')); bd = pd.read_csv(os.path.join(R, 'B_bands.csv'))
FULL = 100 * np.log(110 / 108)
M = ['M1 前後比較', 'M2 前年同月比の差', 'M3 中断時系列', 'M4 軽減税率の品目と差の差', 'M5 非課税の品目と差の差', 'M6 合成対照']
def hw(v, kind, h=3): return bd[(bd.variant == v) & (bd.kind == kind) & (bd.h == h)].set_index('method').half90.loc[M]
out = {}
for v in ['main', 'P12', 'P36', 'エネルギーを除くT', '軽減の対照から生鮮を除く', '単純平均']:
    calm = hw(v, '落ち着いた期間'); turb = hw(v, '荒れた期間')
    rr = real[(real.variant == v) & (real.h == 3)].set_index('method').loc[M]
    own, ctl = calm.iloc[:3].mean(), calm.iloc[3:].mean()
    best = calm.idxmin()
    ratio = (turb / calm)
    out[v] = dict(est=rr.est.round(3).to_dict(), calm_half90=calm.round(3).to_dict(), turb_half90=turb.round(3).to_dict(),
                  H1_ratio_own_over_ctl=round(own / ctl, 3), H1=bool(own / ctl >= 1.5),
                  H2_range=round(rr.est.max() - rr.est.min(), 3), H2=bool(rr.est.max() - rr.est.min() >= .5),
                  H3_best=best, H3_best_est=round(rr.est[best], 3), H3_diff=round(rr.est[best] - FULL, 3), H3=bool(abs(rr.est[best] - FULL) <= .3),
                  H4_ratio=ratio.round(2).to_dict(), H4_count=int((ratio >= 2).sum()), H4=bool((ratio >= 2).sum() >= 4),
                  outside_calm=rr.outside.to_dict())
out['full_pass_through'] = dict(log100=round(FULL, 3), pct=round((110 / 108 - 1) * 100, 3))
json.dump(out, open(os.path.join(R, 'main.json'), 'w'), ensure_ascii=False, indent=1)
for v, d in out.items():
    if v == 'full_pass_through': continue
    print(v, 'H1', d['H1_ratio_own_over_ctl'], d['H1'], '| H2', d['H2_range'], d['H2'], '| H3', d['H3_best'], d['H3_best_est'], d['H3_diff'], d['H3'], '| H4', d['H4_count'], d['H4'])
