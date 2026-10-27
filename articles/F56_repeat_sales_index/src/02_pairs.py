"""02：同じ物件とみなせる取引の組（ペア）を作る。
不動産取引価格情報には物件の ID がないので、「同じ建物・同じ間取り・同じ面積」を同じ住戸の代わりにする（近似）。"""
from common import *

KEY_STRICT = ['市区町村コード', '地区名', '最寄駅：名称', '最寄駅：距離（分）', '建築年', '建物の構造', '都市計画',
              '建ぺい率（％）', '容積率（％）', '間取り', '面積（㎡）']
KEY_BUILDING = KEY_STRICT[:-2]          # 同じ建物（間取り・面積は問わない）


def make_pairs(d, key, min_gap=1):
    """同じキーの取引を時期順に並べ、となり合う2件をペアにする（同じ四半期どうしは除く）"""
    x = d.copy()
    x['qi'] = (x.q - x.q.min()).apply(lambda p: p.n).astype(int)
    x['k'] = x[key].astype(str).agg('|'.join, axis=1)
    x = x.sort_values(['k', 'qi'])
    nxt = x.groupby('k').shift(-1)
    p = pd.DataFrame({'k': x.k, 'q1': x.qi, 'q2': nxt.qi, 'lp1': x.lppm2, 'lp2': nxt.lppm2,
                      'ren1': x.renov, 'ren2': nxt.renov, 'age1': x.age, 'age2': nxt.age,
                      'area': x.area, 'larea1': x.larea, 'larea2': nxt.larea, 'muni': x.muni, 'ward23': x.ward23,
                      'walk': x.walk})
    p = p.dropna(subset=['q2'])
    p['q2'] = p.q2.astype(int)
    p = p[p.q2 - p.q1 >= min_gap].reset_index(drop=True)
    p['gap'] = p.q2 - p.q1
    p['dlp'] = p.lp2 - p.lp1
    return p


if __name__ == '__main__':
    d, log = load()
    pd.Series(log).to_csv(RES / 'sample_log.csv', header=['rows'])
    ps = make_pairs(d, KEY_STRICT)
    pb = make_pairs(d, KEY_BUILDING)
    ps.to_csv(ROOT / 'data' / 'pairs_strict.csv.gz', index=False, compression='gzip')
    pb.to_csv(ROOT / 'data' / 'pairs_building.csv.gz', index=False, compression='gzip')
    print('strict pairs', len(ps), 'building pairs', len(pb))
